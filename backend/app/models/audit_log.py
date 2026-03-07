from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base

class AuditLog(Base):
    """
    Novel Feature: AI-generated audit trail for compliance.
    Every action is logged with an AI-written explanation.
    triplet_id and document_id are both optional so the same table
    can record document-level events (upload/delete) as well as
    triplet-level events (created/approved/rejected/fraud).
    """
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Entity references — at least one will be set
    triplet_id = Column(String, ForeignKey("triplets.id"), nullable=True)   # nullable for doc events
    document_id = Column(String, ForeignKey("documents.id"), nullable=True) # nullable for triplet events
    
    # Action details
    action = Column(String, nullable=False)  # CREATED, APPROVED, REJECTED, FLAGGED, UPLOADED, DELETED, FRAUD_CONFIRMED, FRAUD_DISMISSED
    
    # Novel: AI-generated explanation
    ai_generated = Column(Text, nullable=False)
    
    # Additional context
    context = Column(JSON, nullable=True)
    
    # User info
    user_id = Column(String, nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=func.now())
    
    # Relationships
    triplet = relationship("Triplet", back_populates="audit_logs", foreign_keys=[triplet_id])
    document = relationship("Document", foreign_keys=[document_id])
