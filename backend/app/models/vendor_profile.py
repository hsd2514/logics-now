from sqlalchemy import Column, String, Float, DateTime, JSON
from sqlalchemy.sql import func
import uuid

from app.database import Base

class VendorProfile(Base):
    """
    Novel Feature: Vendor pattern learning for predictive alerts.
    Tracks normal behavior patterns per vendor to detect anomalies.
    """
    __tablename__ = "vendor_profiles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_name = Column(String, unique=True, nullable=False)
    
    # Amount statistics
    avg_amount = Column(Float, default=0.0)
    std_deviation = Column(Float, default=0.0)
    min_amount = Column(Float, nullable=True)
    max_amount = Column(Float, nullable=True)
    
    # Frequency patterns
    avg_frequency = Column(Float, default=0.0)  # Invoices per month
    total_invoices = Column(Float, default=0)
    
    # Route patterns
    route_patterns = Column(JSON, default=list)  # Common routes
    
    # Risk assessment
    risk_score = Column(Float, default=0.0)
    historical_fraud_rate = Column(Float, default=0.0)
    
    # Timestamps
    first_seen = Column(DateTime, default=func.now())
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    last_invoice_date = Column(DateTime, nullable=True)
