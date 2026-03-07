from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.services.document_service import DocumentService
from app.schemas.document import DocumentResponse, DocumentListResponse, DocumentUploadResponse

router = APIRouter()
document_service = DocumentService()

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Query(..., description="Document type: LR, POD, or INVOICE"),
    db: Session = Depends(get_db)
):
    """Upload and process a single document."""
    if doc_type.upper() not in ["LR", "POD", "INVOICE"]:
        raise HTTPException(status_code=400, detail="Invalid document type. Must be LR, POD, or INVOICE")
    
    document = await document_service.upload_and_process(db, file, doc_type)
    
    return DocumentUploadResponse(
        id=document.id,
        message=f"Document uploaded and processed successfully",
        status=document.status
    )

@router.post("/batch", response_model=List[DocumentUploadResponse])
async def upload_batch(
    files: List[UploadFile] = File(...),
    doc_type: str = Query(..., description="Document type for all files"),
    db: Session = Depends(get_db)
):
    """Upload and process multiple documents."""
    if doc_type.upper() not in ["LR", "POD", "INVOICE"]:
        raise HTTPException(status_code=400, detail="Invalid document type")
    
    results = []
    for file in files:
        document = await document_service.upload_and_process(db, file, doc_type)
        results.append(DocumentUploadResponse(
            id=document.id,
            message="Processed",
            status=document.status
        ))
    
    return results

@router.get("", response_model=DocumentListResponse)
def list_documents(
    doc_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all documents with optional filtering."""
    documents, total = document_service.get_documents(db, doc_type, status, skip, limit)
    
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        total=total
    )

@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    """Get a specific document by ID."""
    document = document_service.get_document(db, doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse.model_validate(document)

@router.delete("/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    """Delete a document."""
    if not document_service.delete_document(db, doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": "Document deleted successfully"}
