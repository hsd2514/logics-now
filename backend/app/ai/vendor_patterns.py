from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import numpy as np

from app.config import get_settings

settings = get_settings()

class VendorPatternLearner:
    """Novel Feature: Learn vendor patterns for predictive fraud detection"""
    
    def __init__(self):
        pass
    
    def update_vendor_profile(
        self, 
        db: Session,
        vendor_name: str,
        invoice_data: Dict,
        route: Optional[tuple] = None
    ):
        """Update vendor profile with new invoice data."""
        from app.models.vendor_profile import VendorProfile
        
        # Get or create vendor profile
        profile = db.query(VendorProfile).filter(
            VendorProfile.vendor_name == vendor_name
        ).first()
        
        if not profile:
            profile = VendorProfile(vendor_name=vendor_name)
            db.add(profile)
        
        # Update statistics
        amount = float(invoice_data.get('amount', 0))
        
        if profile.total_invoices == 0:
            profile.avg_amount = amount
            profile.std_deviation = 0
            profile.min_amount = amount
            profile.max_amount = amount
        else:
            # Incremental mean and std calculation
            old_mean = profile.avg_amount
            n = profile.total_invoices
            new_mean = old_mean + (amount - old_mean) / (n + 1)
            
            # Welford's algorithm for variance
            old_var = profile.std_deviation ** 2 if profile.std_deviation else 0
            new_var = old_var + ((amount - old_mean) * (amount - new_mean) - old_var) / (n + 1)
            
            profile.avg_amount = new_mean
            profile.std_deviation = np.sqrt(new_var) if new_var > 0 else 0
            profile.min_amount = min(profile.min_amount or amount, amount)
            profile.max_amount = max(profile.max_amount or amount, amount)
        
        profile.total_invoices += 1
        
        # Update route patterns
        if route:
            route_str = f"{route[0]}-{route[1]}".lower()
            routes = profile.route_patterns or []
            if route_str not in routes:
                routes.append(route_str)
                profile.route_patterns = routes[:20]  # Keep top 20 routes
        
        # Update frequency
        profile.last_invoice_date = datetime.now()
        self._update_frequency(db, profile)
        
        db.commit()
        return profile
    
    def _update_frequency(self, db: Session, profile):
        """Calculate invoice frequency for vendor."""
        from app.models.triplet import Triplet
        from app.models.document import Document
        
        # Count invoices in last 30 days
        cutoff = datetime.now() - timedelta(days=30)
        
        # This is a simplified frequency calculation
        # In production, you'd query actual invoice counts
        if profile.first_seen:
            days_active = (datetime.now() - profile.first_seen).days or 1
            profile.avg_frequency = profile.total_invoices / (days_active / 30)
    
    def calculate_risk_score(self, profile, new_invoice: Dict) -> float:
        """Calculate risk score for a new invoice against vendor profile."""
        if not profile or profile.total_invoices < settings.vendor_min_invoices_for_risk:
            return 0.0  # Not enough data
        
        risk_factors = []
        
        # Amount deviation
        amount = float(new_invoice.get('amount', 0))
        if profile.std_deviation and profile.std_deviation > 0:
            z_score = abs(amount - profile.avg_amount) / profile.std_deviation
            if z_score > 3:
                risk_factors.append(min(z_score * 0.1, 0.5))
        
        # Route anomaly
        origin = new_invoice.get('origin', '').lower()
        dest = new_invoice.get('destination', '').lower()
        if origin and dest:
            route = f"{origin}-{dest}"
            if profile.route_patterns and route not in profile.route_patterns:
                risk_factors.append(0.3)
        
        # Historical fraud rate
        if profile.historical_fraud_rate > 0.05:
            risk_factors.append(profile.historical_fraud_rate)
        
        return max(risk_factors) if risk_factors else 0.0
    
    def get_predictive_alerts(self, db: Session, limit: int = 10) -> List[Dict]:
        """Get vendors with elevated risk scores."""
        from app.models.vendor_profile import VendorProfile
        
        high_risk_vendors = db.query(VendorProfile).filter(
            VendorProfile.risk_score > settings.vendor_high_risk_cutoff
        ).order_by(VendorProfile.risk_score.desc()).limit(limit).all()
        
        alerts = []
        for vendor in high_risk_vendors:
            alerts.append({
                'vendor_name': vendor.vendor_name,
                'risk_score': vendor.risk_score,
                'avg_amount': vendor.avg_amount,
                'total_invoices': vendor.total_invoices,
                'historical_fraud_rate': vendor.historical_fraud_rate,
                'alert_type': 'VENDOR_RISK',
                'reasoning': self._generate_risk_reasoning(vendor)
            })
        
        return alerts
    
    def _generate_risk_reasoning(self, profile) -> str:
        """Generate human-readable risk reasoning."""
        reasons = []
        
        if profile.historical_fraud_rate > settings.vendor_high_fraud_rate_for_reason:
            reasons.append(f"High historical fraud rate ({profile.historical_fraud_rate * 100:.1f}%)")
        
        if profile.std_deviation and profile.avg_amount:
            cv = profile.std_deviation / profile.avg_amount
            if cv > settings.vendor_high_cv_threshold:
                reasons.append(f"High amount variability (CV: {cv:.2f})")
        
        if profile.avg_frequency > settings.vendor_high_frequency_threshold:
            reasons.append(f"High invoice frequency ({profile.avg_frequency:.0f}/month)")
        
        return "; ".join(reasons) if reasons else "Elevated risk based on pattern analysis"
