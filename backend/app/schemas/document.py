from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TextBlock(BaseModel):
    text: str
    x: float
    y: float
    width: float
    height: float
    confidence: float

class EntityExtraction(BaseModel):
    shipment_id: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[str] = None
    party_name: Optional[str] = None
    consignor: Optional[str] = None
    consignee: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    vehicle_number: Optional[str] = None
    weight: Optional[float] = None
    gst_number: Optional[str] = None

class DocumentCreate(BaseModel):
    type: str
    file_name: str

class DocumentResponse(BaseModel):
    id: str
    type: str
    file_name: str
    file_path: str
    uploaded_at: datetime
    ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    entities: Optional[EntityExtraction] = None
    status: str
    
    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int

class DocumentUploadResponse(BaseModel):
    id: str
    message: str
    status: str

class ProcessingStatus(BaseModel):
    document_id: str
    stage: str
    progress: float
    message: str
