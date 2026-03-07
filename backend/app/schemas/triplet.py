from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.schemas.document import DocumentResponse

class ValidationDetail(BaseModel):
    rule: str
    passed: bool
    expected: Optional[str] = None
    actual: Optional[str] = None
    message: str

class AttentionRegion(BaseModel):
    document_type: str  # LR, POD, INVOICE
    field: str
    score: float
    # Raw pixel coords
    x: float
    y: float
    width: float
    height: float
    # Real document canvas dimensions (pixels)
    doc_width: Optional[float] = None
    doc_height: Optional[float] = None
    # Normalised coordinates [0, 1] — use these for rendering
    x_norm: Optional[float] = None
    y_norm: Optional[float] = None
    w_norm: Optional[float] = None
    h_norm: Optional[float] = None

class MatchResult(BaseModel):
    lr_id: str
    pod_id: str
    invoice_id: str
    match_score: float
    confidence: float
    attention_regions: List[AttentionRegion]

class TripletResponse(BaseModel):
    id: str
    lr_id: str
    pod_id: str
    invoice_id: str
    match_score: float
    confidence: float
    ocr_accuracy: Optional[float] = None
    ner_confidence: Optional[float] = None
    rule_pass_score: Optional[float] = None
    validation_details: Optional[List[ValidationDetail]] = None
    ai_explanation: Optional[str] = None
    attention_map: Optional[List[AttentionRegion]] = None
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    
    # Nested document info
    lr: Optional[DocumentResponse] = None
    pod: Optional[DocumentResponse] = None
    invoice: Optional[DocumentResponse] = None
    
    class Config:
        from_attributes = True

class TripletListResponse(BaseModel):
    triplets: List[TripletResponse]
    total: int
    pending_review: int
    auto_approved: int
    flagged: int

class TripletReview(BaseModel):
    action: str  # approve, reject
    notes: Optional[str] = None
    reviewed_by: str

class TripletStats(BaseModel):
    total_triplets: int
    auto_approved: int
    manually_approved: int
    rejected: int
    pending_review: int
    avg_confidence: float
    avg_processing_time: float
