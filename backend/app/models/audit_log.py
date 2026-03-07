from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base

class AuditLog(Base):
    """
    Novel Feature: AI-generated audit trail for compliance.
    Every action is logged with an AI-written explanation.
    """
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    triplet_id = Column(String, ForeignKey("triplets.id"), nullable=False)
    
    # Action details
    action = Column(String, nullable=False)  # CREATED, APPROVED, REJECTED, FLAGGED
    
    # Novel: AI-generated explanation
    ai_generated = Column(Text, nullable=False)
    
    # Additional context
    context = Column(JSON, nullable=True)
    
    # User info
    user_id = Column(String, nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=func.now())
    
    # Relationships
    triplet = relationship("Triplet", back_populates="audit_logs")
