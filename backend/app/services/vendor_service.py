from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import statistics

from app.models.vendor_profile import VendorProfile
from app.models.document import Document
from app.models.fraud_alert import FraudAlert
from app.models.triplet import Triplet


class VendorService:
    """Service for managing vendor profiles and analytics."""
    
    def get_or_create_profile(self, db: Session, vendor_name: str) -> VendorProfile:
        """Get existing vendor profile or create new one."""
        profile = db.query(VendorProfile).filter(
            VendorProfile.vendor_name == vendor_name
        ).first()
        
        if not profile:
            profile = VendorProfile(vendor_name=vendor_name)
            db.add(profile)
            db.flush()
        
        return profile
    
    def update_vendor_profile(
        self, 
        db: Session, 
        vendor_name: str,
        amount: float,
        route: str,
        invoice_date: datetime
    ):
        """Update vendor profile with new transaction data."""
        profile = self.get_or_create_profile(db, vendor_name)
        
        # Get all invoices for this vendor
        invoices = db.query(Document).filter(
            Document.type == "INVOICE"
        ).all()
        
        vendor_invoices = [
            inv for inv in invoices 
            if inv.entities and inv.entities.get('party_name', '').strip().upper() == vendor_name.strip().upper()
        ]
        
        if not vendor_invoices:
            return profile
        
        # Update amount statistics
        amounts = []
        for inv in vendor_invoices:
            inv_amount = inv.entities.get('amount')
            if inv_amount:
                try:
                    amounts.append(float(inv_amount))
                except:
                    pass
        
        if amounts:
            profile.avg_amount = statistics.mean(amounts)
            profile.std_deviation = statistics.stdev(amounts) if len(amounts) > 1 else 0.0
            profile.min_amount = min(amounts)
            profile.max_amount = max(amounts)
            profile.total_invoices = len(amounts)
        
        # Update frequency (invoices per month)
        if profile.first_seen:
            days_active = (datetime.now() - profile.first_seen).days
            if days_active > 0:
                profile.avg_frequency = (profile.total_invoices / days_active) * 30
        
        # Update route patterns
        routes = {}
        for inv in vendor_invoices:
            origin = inv.entities.get('origin', '')
            destination = inv.entities.get('destination', '')
            if origin and destination:
                route_key = f"{origin}-{destination}"
                routes[route_key] = routes.get(route_key, 0) + 1
        
        # Store top 5 routes
        sorted_routes = sorted(routes.items(), key=lambda x: x[1], reverse=True)[:5]
        profile.route_patterns = [
            {"route": route, "count": count} 
            for route, count in sorted_routes
        ]
        
        # Calculate fraud rate
        fraud_count = db.query(FraudAlert).join(
            Triplet, FraudAlert.triplet_id == Triplet.id
        ).join(
            Document, Triplet.invoice_id == Document.id
        ).filter(
            func.upper(func.json_extract(Document.entities, '$.party_name')) == vendor_name.strip().upper()
        ).count()
        
        if profile.total_invoices > 0:
            profile.historical_fraud_rate = fraud_count / profile.total_invoices
        
        # Calculate risk score (0-100)
        risk_score = 0.0
        
        # High fraud rate increases risk
        risk_score += profile.historical_fraud_rate * 50
        
        # High amount variance increases risk
        if profile.avg_amount > 0 and profile.std_deviation > 0:
            cv = profile.std_deviation / profile.avg_amount  # Coefficient of variation
            risk_score += min(cv * 20, 30)  # Cap at 30
        
        # Low frequency (inactive vendors) slightly increases risk
        if profile.avg_frequency < 1:  # Less than 1 invoice per month
            risk_score += 10
        
        # New vendors have moderate risk
        if profile.total_invoices < 5:
            risk_score += 10
        
        profile.risk_score = min(risk_score, 100)
        profile.last_invoice_date = invoice_date
        profile.last_updated = datetime.now()
        
        db.commit()
        return profile
    
    def get_all_profiles(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        sort_by: str = 'risk_score'
    ) -> tuple[List[VendorProfile], int]:
        """Get all vendor profiles with pagination."""
        query = db.query(VendorProfile)
        
        # Apply sorting
        if sort_by == 'risk_score':
            query = query.order_by(desc(VendorProfile.risk_score))
        elif sort_by == 'total_invoices':
            query = query.order_by(desc(VendorProfile.total_invoices))
        elif sort_by == 'avg_amount':
            query = query.order_by(desc(VendorProfile.avg_amount))
        else:
            query = query.order_by(VendorProfile.vendor_name)
        
        total = query.count()
        profiles = query.offset(skip).limit(limit).all()
        
        return profiles, total
    
    def get_vendor_analytics(self, db: Session) -> Dict:
        """Get aggregate vendor analytics."""
        profiles = db.query(VendorProfile).all()
        
        if not profiles:
            return {
                'total_vendors': 0,
                'high_risk_count': 0,
                'avg_risk_score': 0.0,
                'total_transactions': 0,
                'avg_transaction_value': 0.0,
                'risk_distribution': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
            }
        
        total_vendors = len(profiles)
        high_risk_count = sum(1 for p in profiles if p.risk_score > 70)
        avg_risk = statistics.mean([p.risk_score for p in profiles])
        total_transactions = sum(p.total_invoices for p in profiles)
        
        all_amounts = [p.avg_amount for p in profiles if p.avg_amount > 0]
        avg_transaction_value = statistics.mean(all_amounts) if all_amounts else 0.0
        
        # Risk distribution
        risk_buckets = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        for p in profiles:
            if p.risk_score < 25:
                risk_buckets['low'] += 1
            elif p.risk_score < 50:
                risk_buckets['medium'] += 1
            elif p.risk_score < 75:
                risk_buckets['high'] += 1
            else:
                risk_buckets['critical'] += 1
        
        return {
            'total_vendors': total_vendors,
            'high_risk_count': high_risk_count,
            'avg_risk_score': round(avg_risk, 2),
            'total_transactions': total_transactions,
            'avg_transaction_value': round(avg_transaction_value, 2),
            'risk_distribution': risk_buckets
        }
    
    def get_vendor_details(self, db: Session, vendor_name: str) -> Optional[Dict]:
        """Get detailed information about a specific vendor."""
        profile = db.query(VendorProfile).filter(
            VendorProfile.vendor_name == vendor_name
        ).first()
        
        if not profile:
            return None
        
        # Get recent transactions
        invoices = db.query(Document).filter(
            Document.type == "INVOICE"
        ).all()
        
        vendor_invoices = [
            inv for inv in invoices 
            if inv.entities and inv.entities.get('party_name', '').strip().upper() == vendor_name.strip().upper()
        ]
        
        recent_transactions = []
        for inv in sorted(vendor_invoices, key=lambda x: x.upload_date or datetime.now(), reverse=True)[:10]:
            recent_transactions.append({
                'id': inv.id,
                'amount': inv.entities.get('amount'),
                'date': inv.entities.get('date'),
                'shipment_id': inv.entities.get('shipment_id'),
                'upload_date': inv.upload_date.isoformat() if inv.upload_date else None
            })
        
        # Get fraud alerts - simplified for now
        vendor_fraud_alerts = []
        
        return {
            'profile': {
                'vendor_name': profile.vendor_name,
                'risk_score': profile.risk_score,
                'total_invoices': profile.total_invoices,
                'avg_amount': profile.avg_amount,
                'std_deviation': profile.std_deviation,
                'min_amount': profile.min_amount,
                'max_amount': profile.max_amount,
                'avg_frequency': profile.avg_frequency,
                'historical_fraud_rate': profile.historical_fraud_rate,
                'route_patterns': profile.route_patterns,
                'first_seen': profile.first_seen.isoformat() if profile.first_seen else None,
                'last_invoice_date': profile.last_invoice_date.isoformat() if profile.last_invoice_date else None
            },
            'recent_transactions': recent_transactions,
            'fraud_alerts': [
                {
                    'id': alert.id,
                    'alert_type': alert.alert_type,
                    'risk_score': alert.risk_score,
                    'detected_at': alert.detected_at.isoformat() if alert.detected_at else None
                }
                for alert in vendor_fraud_alerts
            ]
        }
