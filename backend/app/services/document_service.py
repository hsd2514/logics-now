import os
import re
import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import UploadFile
from html.parser import HTMLParser

from app.models.document import Document, DocumentStatus
from app.models.audit_log import AuditLog
from app.pipeline.preprocessor import Preprocessor
from app.pipeline.ocr_engine import OCREngine
from app.pipeline.entity_extractor import EntityExtractor
from app.services.embedding_service import EmbeddingService
from app.config import get_settings
from app.services.websocket_manager import ws_manager
import asyncio

settings = get_settings()

class HTMLTextExtractor(HTMLParser):
    """Extract text content from HTML."""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.current_tag = None
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        
    def handle_data(self, data):
        text = data.strip()
        if text:
            self.text_parts.append(text)
    
    def get_text(self):
        return ' '.join(self.text_parts)

class DocumentService:
    def __init__(self):
        self.preprocessor = Preprocessor()
        self.ocr_engine = OCREngine()
        self.entity_extractor = EntityExtractor()
        self.embedding_service = EmbeddingService()
        self.upload_dir = settings.upload_dir
        
        # Ensure upload directory exists
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def upload_and_process(
        self, 
        db: Session, 
        file: UploadFile, 
        doc_type: str
    ) -> Document:
        """Upload a document and process it through the pipeline."""
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1]
        saved_filename = f"{file_id}{file_ext}"
        file_path = os.path.join(self.upload_dir, saved_filename)
        
        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Create document record
        document = Document(
            id=file_id,
            type=doc_type.upper(),
            file_name=file.filename,
            file_path=file_path,
            status=DocumentStatus.PENDING
        )
        db.add(document)
        db.commit()
        
        # Process document
        try:
            document = await self.process_document(db, document)
            # Audit log: successful upload & processing
            self._write_audit(
                db, document, action="UPLOADED",
                ai_text=(
                    f"{doc_type.upper()} document '{file.filename}' uploaded and processed successfully. "
                    f"OCR confidence: {document.ocr_confidence or 0:.1%}. "
                    f"Entities extracted: {len(document.entities or {})} fields."
                ),
                context={"file_name": file.filename, "doc_type": doc_type.upper(), "status": document.status}
            )
            db.commit()
        except Exception as e:
            document.status = DocumentStatus.ERROR
            document.processing_error = str(e)
            # Audit log: upload failed
            self._write_audit(
                db, document, action="UPLOAD_ERROR",
                ai_text=f"{doc_type.upper()} document '{file.filename}' processing failed: {str(e)}",
                context={"file_name": file.filename, "doc_type": doc_type.upper(), "error": str(e)}
            )
            db.commit()
        
        return document
    
    async def process_document(self, db: Session, document: Document) -> Document:
        """Process a document through preprocessing, OCR, and entity extraction."""
        file_ext = os.path.splitext(document.file_path)[1].lower()
        
        # Check if HTML file - process directly without OCR
        if file_ext in ['.html', '.htm']:
            return await self.process_html_document(db, document)
        
        document.status = DocumentStatus.PROCESSING
        db.commit()
        
        await ws_manager.send_processing_update(
            document.id, 'PREPROCESSING', 10, 'Starting preprocessing'
        )
        
        # Stage 1: Preprocessing
        processed_image, quality_score = await asyncio.to_thread(
            self.preprocessor.process, document.file_path
        ) # Kept original return values
        
        await ws_manager.send_processing_update(
            document.id, 'OCR', 30, 'Running OCR extraction'
        )

        # Stage 2: OCR
        ocr_text, text_blocks, ocr_confidence = await asyncio.to_thread(
            self.ocr_engine.extract, processed_image
        ) # Kept original return values
        
        await ws_manager.send_processing_update(
            document.id, 'NER', 70, 'Extracting entities'
        )

        # Stage 3: Entity Extraction
        entities, ner_confidence = await asyncio.to_thread(
            self.entity_extractor.extract_for_document_type,
            ocr_text, document.type
        )
        
        # Update document

        document.ocr_text = ocr_text
        document.ocr_confidence = ocr_confidence
        document.text_blocks = await asyncio.to_thread(
            self.ocr_engine.blocks_to_dict, text_blocks
        )
        document.entities = entities
        document.embedding = await asyncio.to_thread(
            self.embedding_service.embed_document, ocr_text, entities
        )
        document.status = DocumentStatus.PROCESSED
        
        db.commit()

        await ws_manager.send_processing_update(
            document.id, 'DONE', 100, 'Processing complete'
        )
        
        return document
    
    async def process_html_document(self, db: Session, document: Document) -> Document:
        """Process HTML document - extract text directly without OCR."""
        # Read HTML file
        with open(document.file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        await ws_manager.send_processing_update(
            document.id, 'EXTRACTION', 30, 'Parsing HTML'
        )

        # Extract text from HTML
        def extract_html(html):
            parser = HTMLTextExtractor()
            parser.feed(html)
            return parser.get_text()

        extracted_text = await asyncio.to_thread(extract_html, html_content)
        
        await ws_manager.send_processing_update(
            document.id, 'NER', 70, 'Extracting entities'
        )

        # Stage 3: Entity Extraction
        entities, ner_confidence = await asyncio.to_thread(
            self.entity_extractor.extract_for_document_type,
            extracted_text, document.type
        )
        
        # Update document - HTML is perfect quality
        document.ocr_text = extracted_text
        document.ocr_confidence = 1.0  # Perfect extraction from HTML
        document.text_blocks = []  # No spatial data for HTML
        document.entities = entities
        document.embedding = await asyncio.to_thread(
            self.embedding_service.embed_document, extracted_text, entities
        )
        document.status = DocumentStatus.PROCESSED
        
        db.commit()

        await ws_manager.send_processing_update(
            document.id, 'DONE', 100, 'Processing complete'
        )
        
        return document
    
    def get_document(self, db: Session, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return db.query(Document).filter(Document.id == doc_id).first()
    
    def get_documents(
        self, 
        db: Session, 
        doc_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Document], int]:
        """Get documents with optional filtering."""
        query = db.query(Document)
        
        if doc_type:
            query = query.filter(Document.type == doc_type.upper())
        if status:
            query = query.filter(Document.status == status)
        
        total = query.count()
        documents = query.order_by(Document.uploaded_at.desc()).offset(skip).limit(limit).all()
        
        return documents, total
    
    def get_unmatched_documents(self, db: Session, doc_type: str) -> List[Document]:
        """Get processed documents that haven't been matched yet."""
        return db.query(Document).filter(
            Document.type == doc_type.upper(),
            Document.status == DocumentStatus.PROCESSED
        ).all()
    
    def delete_document(self, db: Session, doc_id: str) -> bool:
        """Delete a document and its file."""
        document = self.get_document(db, doc_id)
        if not document:
            return False
        
        # Audit log: record deletion before the record is gone
        self._write_audit(
            db, document, action="DELETED",
            ai_text=(
                f"{document.type} document '{document.file_name}' (id: {document.id}) "
                f"was deleted from the system."
            ),
            context={"file_name": document.file_name, "doc_type": document.type, "status": document.status}
        )
        db.flush()  # Persist audit before cascade-deleting the document
        
        # Delete file
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        db.delete(document)
        db.commit()
        return True

    # ── Private helpers ──────────────────────────────────────────────────────

    def _write_audit(
        self,
        db: Session,
        document: Document,
        action: str,
        ai_text: str,
        context: dict = None,
        user_id: str = None
    ) -> None:
        """Persist a single AuditLog record for a document-level event."""
        log = AuditLog(
            document_id=document.id,
            triplet_id=None,
            action=action,
            ai_generated=ai_text,
            context=context or {},
            user_id=user_id,
        )
        db.add(log)
