from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import uuid

from app.database import Base

class DocumentType(str, enum.Enum):
    LR = "LR"
    POD = "POD"
    INVOICE = "INVOICE"

class DocumentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    MATCHED = "MATCHED"
    ERROR = "ERROR"

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=func.now())
    
    # OCR results
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    text_blocks = Column(JSON, nullable=True)  # Bounding boxes for heatmap
    
    # Extracted entities
    entities = Column(JSON, nullable=True)
    
    # Embedding for matching
    embedding = Column(JSON, nullable=True)
    
    # Processing status
    status = Column(String, default=DocumentStatus.PENDING)
    processing_error = Column(Text, nullable=True)
    
    # Relationships
    lr_triplets = relationship("Triplet", foreign_keys="Triplet.lr_id", back_populates="lr")
    pod_triplets = relationship("Triplet", foreign_keys="Triplet.pod_id", back_populates="pod")
    invoice_triplets = relationship("Triplet", foreign_keys="Triplet.invoice_id", back_populates="invoice")
    audit_logs = relationship("AuditLog", foreign_keys="AuditLog.document_id", back_populates="document")
