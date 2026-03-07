from typing import List, Optional, Dict, Any
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

    def _normalize_route_patterns(self, raw_patterns: Any) -> List[Dict[str, Any]]:
        """Normalize stored route patterns into [{route, count}] shape."""
        if not raw_patterns:
            return []

        normalized: List[Dict[str, Any]] = []
        if isinstance(raw_patterns, list):
            for item in raw_patterns:
                if isinstance(item, dict):
                    route = str(item.get("route", "")).strip().lower()
                    if not route:
                        continue
                    try:
                        count = int(item.get("count", 1))
                    except (TypeError, ValueError):
                        count = 1
                    normalized.append({"route": route, "count": max(1, count)})
                elif isinstance(item, str):
                    route = item.strip().lower()
                    if route:
                        normalized.append({"route": route, "count": 1})
        elif isinstance(raw_patterns, dict):
            for route, count in raw_patterns.items():
                route_key = str(route).strip().lower()
                if not route_key:
                    continue
                try:
                    parsed_count = int(count)
                except (TypeError, ValueError):
                    parsed_count = 1
                normalized.append({"route": route_key, "count": max(1, parsed_count)})

        merged: Dict[str, int] = {}
        for item in normalized:
            merged[item["route"]] = merged.get(item["route"], 0) + int(item["count"])

        return [
            {"route": route, "count": count}
            for route, count in sorted(merged.items(), key=lambda x: x[1], reverse=True)
        ][:20]

    def _compute_display_risk(self, profile: VendorProfile) -> float:
        """
        Compute a robust 0-100 risk score for UI sorting/display.
        Uses persisted risk if present; otherwise derives from profile signals.
        """
        persisted = float(profile.risk_score or 0.0)
        if persisted > 0:
            return round(min(persisted, 100.0), 2)

        total_invoices = float(profile.total_invoices or 0.0)
        avg_amount = float(profile.avg_amount or 0.0)
        std_dev = float(profile.std_deviation or 0.0)
        avg_freq = float(profile.avg_frequency or 0.0)
        fraud_rate = float(profile.historical_fraud_rate or 0.0)
        routes = self._normalize_route_patterns(profile.route_patterns)

        risk = 0.0

        # Fraud history is the strongest feature.
        risk += min(fraud_rate * 100.0 * 0.6, 60.0)

        # New vendors are less predictable.
        if total_invoices <= 2:
            risk += 30.0
        elif total_invoices < 5:
            risk += 18.0

        # Low frequency tends to be noisier in this dataset.
        if total_invoices > 0 and avg_freq < 1.0:
            risk += 12.0

        # Amount volatility
        if avg_amount > 0 and std_dev > 0:
            cv = std_dev / avg_amount
            risk += min(cv * 35.0, 28.0)

        # Single-route concentration is a mild risk factor.
        if len(routes) <= 1 and total_invoices > 0:
            risk += 6.0

        # Ensure non-flat baseline for active vendors.
        if total_invoices > 0 and risk < 5.0:
            risk = 5.0

        return round(min(risk, 100.0), 2)

    def _serialize_profile(self, profile: VendorProfile) -> Dict[str, Any]:
        normalized_routes = self._normalize_route_patterns(profile.route_patterns)
        return {
            'vendor_name': profile.vendor_name,
            'risk_score': self._compute_display_risk(profile),
            'total_invoices': profile.total_invoices,
            'avg_amount': profile.avg_amount,
            'std_deviation': profile.std_deviation,
            'min_amount': profile.min_amount,
            'max_amount': profile.max_amount,
            'avg_frequency': profile.avg_frequency,
            'historical_fraud_rate': profile.historical_fraud_rate,
            'route_patterns': normalized_routes,
            'first_seen': profile.first_seen.isoformat() if profile.first_seen else None,
            'last_invoice_date': profile.last_invoice_date.isoformat() if profile.last_invoice_date else None
        }
    
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
            if inv.entities and inv.entities.get('vendor_name', '').strip().upper() == vendor_name.strip().upper()
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
            func.upper(func.json_extract(Document.entities, '$.vendor_name')) == vendor_name.strip().upper()
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
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get all vendor profiles with pagination."""
        profiles = db.query(VendorProfile).all()
        serialized = [self._serialize_profile(p) for p in profiles]

        if sort_by == 'risk_score':
            serialized.sort(key=lambda p: float(p.get('risk_score', 0.0)), reverse=True)
        elif sort_by == 'total_invoices':
            serialized.sort(key=lambda p: float(p.get('total_invoices', 0.0)), reverse=True)
        elif sort_by == 'avg_amount':
            serialized.sort(key=lambda p: float(p.get('avg_amount', 0.0)), reverse=True)
        else:
            serialized.sort(key=lambda p: (p.get('vendor_name') or '').lower())

        total = len(serialized)
        page = serialized[skip: skip + limit]
        return page, total
    
    def get_vendor_analytics(self, db: Session) -> Dict:
        """Get aggregate vendor analytics."""
        profiles = [self._serialize_profile(p) for p in db.query(VendorProfile).all()]
        
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
        high_risk_count = sum(1 for p in profiles if float(p.get('risk_score', 0.0)) > 70)
        avg_risk = statistics.mean([float(p.get('risk_score', 0.0)) for p in profiles])
        total_transactions = sum(float(p.get('total_invoices', 0.0)) for p in profiles)
        
        all_amounts = [float(p.get('avg_amount', 0.0)) for p in profiles if float(p.get('avg_amount', 0.0)) > 0]
        avg_transaction_value = statistics.mean(all_amounts) if all_amounts else 0.0
        
        # Risk distribution
        risk_buckets = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        for p in profiles:
            risk = float(p.get('risk_score', 0.0))
            if risk < 25:
                risk_buckets['low'] += 1
            elif risk < 50:
                risk_buckets['medium'] += 1
            elif risk < 75:
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
            if inv.entities and inv.entities.get('vendor_name', '').strip().upper() == vendor_name.strip().upper()
        ]
        
        recent_transactions = []
        try:
            # Sort by uploaded_at, handling None values
            sorted_invoices = sorted(
                vendor_invoices, 
                key=lambda x: x.uploaded_at if x.uploaded_at else datetime.min,
                reverse=True
            )[:10]
            
            for inv in sorted_invoices:
                recent_transactions.append({
                    'id': inv.id,
                    'amount': inv.entities.get('amount') if inv.entities else None,
                    'date': inv.entities.get('date') if inv.entities else None,
                    'shipment_id': inv.entities.get('shipment_id') if inv.entities else None,
                    'uploaded_at': inv.uploaded_at.isoformat() if inv.uploaded_at else None
                })
        except Exception as e:
            print(f"Error processing transactions: {e}")
            recent_transactions = []
        
        # Get fraud alerts - simplified for now
        vendor_fraud_alerts = []
        
        return {
            'profile': self._serialize_profile(profile),
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
