from sqlalchemy import Column, String, Float, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import uuid

from app.database import Base

class TripletStatus(str, enum.Enum):
    PENDING = "PENDING"
    AUTO_APPROVED = "AUTO_APPROVED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVIEW = "REVIEW"

class Triplet(Base):
    __tablename__ = "triplets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Document references
    lr_id = Column(String, ForeignKey("documents.id"), nullable=False)
    pod_id = Column(String, ForeignKey("documents.id"), nullable=False)
    invoice_id = Column(String, ForeignKey("documents.id"), nullable=False)
    
    # Matching scores
    match_score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    
    # Individual component scores
    ocr_accuracy = Column(Float, nullable=True)
    ner_confidence = Column(Float, nullable=True)
    rule_pass_score = Column(Float, nullable=True)
    
    # Validation details
    validation_details = Column(JSON, nullable=True)
    partial_delivery = Column(Boolean, nullable=False, default=False)
    
    # Novel: AI-generated audit explanation
    ai_explanation = Column(Text, nullable=True)
    
    # Novel: Attention map for explainability heatmap
    attention_map = Column(JSON, nullable=True)
    
    # Status
    status = Column(String, default=TripletStatus.PENDING)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Relationships
    lr = relationship("Document", foreign_keys=[lr_id], back_populates="lr_triplets")
    pod = relationship("Document", foreign_keys=[pod_id], back_populates="pod_triplets")
    invoice = relationship("Document", foreign_keys=[invoice_id], back_populates="invoice_triplets")
    fraud_alerts = relationship("FraudAlert", back_populates="triplet")
    audit_logs = relationship("AuditLog", back_populates="triplet")
