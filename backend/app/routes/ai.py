from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db
from app.models.document import Document
from app.models.triplet import Triplet
from app.ai.doc_chat import DocumentChat
from app.ai.nl_query import NLQueryParser
from app.ai.audit_generator import AuditGenerator

router = APIRouter()
doc_chat = DocumentChat()
nl_parser = NLQueryParser()
audit_gen = AuditGenerator()

class ChatRequest(BaseModel):
    document_id: str
    message: str
    history: Optional[List[dict]] = None

class QueryRequest(BaseModel):
    query: str

@router.post("/chat")
async def chat_with_document(request: ChatRequest, db: Session = Depends(get_db)):
    """Chat with a document using AI (Novel Feature - streaming)."""
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    async def generate():
        async for chunk in doc_chat.chat_stream(
            document.ocr_text or "",
            document.entities or {},
            request.message,
            request.history
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

@router.post("/chat/sync")
def chat_sync(request: ChatRequest, db: Session = Depends(get_db)):
    """Non-streaming chat endpoint."""
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    response = doc_chat.chat_sync(
        document.ocr_text or "",
        document.entities or {},
        request.message
    )
    
    return {"response": response}

@router.post("/query")
async def natural_language_query(request: QueryRequest):
    """Convert natural language to filters (Novel Feature - streaming)."""
    async def generate():
        async for chunk in nl_parser.parse_stream(request.query):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

@router.post("/query/sync")
def query_sync(request: QueryRequest):
    """Non-streaming query parsing."""
    filters = nl_parser.parse(request.query)
    return {"filters": filters}

@router.get("/audit/{triplet_id}")
def get_audit_trail(triplet_id: str, db: Session = Depends(get_db)):
    """Get or generate AI audit trail for a triplet (Novel Feature)."""
    triplet = db.query(Triplet).filter(Triplet.id == triplet_id).first()
    if not triplet:
        raise HTTPException(status_code=404, detail="Triplet not found")
    
    # Return existing explanation or generate new one
    if triplet.ai_explanation:
        return {
            "triplet_id": triplet_id,
            "explanation": triplet.ai_explanation,
            "generated": False
        }
    
    # Generate new explanation
    lr = db.query(Document).filter(Document.id == triplet.lr_id).first()
    pod = db.query(Document).filter(Document.id == triplet.pod_id).first()
    invoice = db.query(Document).filter(Document.id == triplet.invoice_id).first()
    
    explanation = audit_gen.generate_match_explanation(
        lr.entities or {} if lr else {},
        pod.entities or {} if pod else {},
        invoice.entities or {} if invoice else {},
        triplet.match_score,
        triplet.validation_details or [],
        triplet.status
    )
    
    # Save it
    triplet.ai_explanation = explanation
    db.commit()
    
    return {
        "triplet_id": triplet_id,
        "explanation": explanation,
        "generated": True
    }
