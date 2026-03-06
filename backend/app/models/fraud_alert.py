from sqlalchemy import Column, String, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import uuid

from app.database import Base

class AlertType(str, enum.Enum):
    DUPLICATE = "DUPLICATE"
    AMOUNT_ANOMALY = "AMOUNT_ANOMALY"
    DATE_MISMATCH = "DATE_MISMATCH"
    VENDOR_ANOMALY = "VENDOR_ANOMALY"
    PREDICTED = "PREDICTED"  # Novel: Predictive alert

class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"

class FraudAlert(Base):
    __tablename__ = "fraud_alerts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    triplet_id = Column(String, ForeignKey("triplets.id"), nullable=False)
    
    # Alert details
    risk_score = Column(Float, nullable=False)
    alert_type = Column(String, nullable=False)
    
    # Detailed breakdown
    details = Column(JSON, nullable=False)
    
    # Novel: AI explanation of why this is suspicious
    ai_reasoning = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(String, default=AlertStatus.OPEN)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Relationships
    triplet = relationship("Triplet", back_populates="fraud_alerts")
