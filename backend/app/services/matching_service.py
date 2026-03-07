from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from app.models.document import Document, DocumentStatus
from app.models.triplet import Triplet, TripletStatus
from app.models.fraud_alert import FraudAlert
from app.models.audit_log import AuditLog
from app.pipeline.triplet_matcher import TripletMatcher
from app.pipeline.validator import Validator
from app.pipeline.fraud_detector import FraudDetector
from app.ai.audit_generator import AuditGenerator
from app.ai.vendor_patterns import VendorPatternLearner
from app.config import get_settings

settings = get_settings()

class MatchingService:
    def __init__(self):
        self.matcher = TripletMatcher()
        self.validator = Validator(
            amount_tolerance=settings.amount_tolerance,
            name_similarity_threshold=settings.name_similarity_threshold,
        )
        self.fraud_detector = FraudDetector()
        self.audit_generator = AuditGenerator()
        self.vendor_learner = VendorPatternLearner()
    
    def match_documents(self, db: Session) -> List[Triplet]:
        """Find and create triplet matches from unmatched documents."""
        # Get unmatched documents
        lrs = db.query(Document).filter(
            Document.type == "LR",
            Document.status == DocumentStatus.PROCESSED
        ).all()
        
        pods = db.query(Document).filter(
            Document.type == "POD",
            Document.status == DocumentStatus.PROCESSED
        ).all()
        
        invoices = db.query(Document).filter(
            Document.type == "INVOICE",
            Document.status == DocumentStatus.PROCESSED
        ).all()
        
        if not (lrs and pods and invoices):
            return []
        
        # Convert to dicts for matcher
        lr_data = [self._doc_to_dict(d) for d in lrs]
        pod_data = [self._doc_to_dict(d) for d in pods]
        invoice_data = [self._doc_to_dict(d) for d in invoices]
        
        # Find matches
        matches = self.matcher.find_best_matches(lr_data, pod_data, invoice_data)
        
        created_triplets = []
        for match in matches:
            triplet = self.create_triplet(
                db, 
                match.lr_id, 
                match.pod_id, 
                match.invoice_id,
                match.match_score,
                match.confidence,
                match.attention_map
            )
            if triplet:
                created_triplets.append(triplet)
        
        return created_triplets
    
    def create_triplet(
        self,
        db: Session,
        lr_id: str,
        pod_id: str,
        invoice_id: str,
        match_score: float,
        initial_confidence: float,
        attention_map: List = None
    ) -> Optional[Triplet]:
        """Create a triplet with full validation and fraud detection."""
        # Get documents
        lr = db.query(Document).filter(Document.id == lr_id).first()
        pod = db.query(Document).filter(Document.id == pod_id).first()
        invoice = db.query(Document).filter(Document.id == invoice_id).first()
        
        if not (lr and pod and invoice):
            return None
        
        # Stage 5: Validation
        validation_results, rule_pass_score = self.validator.validate_triplet(
            lr.entities or {},
            pod.entities or {},
            invoice.entities or {}
        )
        
        # Calculate final confidence
        confidence = (
            settings.match_weight * match_score +
            settings.ocr_weight * (lr.ocr_confidence or 0.8) +
            settings.ner_weight * initial_confidence +
            settings.rule_weight * rule_pass_score
        )
        
        # Determine status
        if confidence >= settings.auto_approve_threshold:
            status = TripletStatus.AUTO_APPROVED
        elif confidence >= settings.confidence_threshold:
            status = TripletStatus.PENDING
        else:
            status = TripletStatus.REVIEW
        
        # Create triplet
        triplet = Triplet(
            lr_id=lr_id,
            pod_id=pod_id,
            invoice_id=invoice_id,
            match_score=match_score,
            confidence=confidence,
            ocr_accuracy=lr.ocr_confidence,
            ner_confidence=initial_confidence,
            rule_pass_score=rule_pass_score,
            validation_details=self.validator.results_to_dict(validation_results),
            attention_map=attention_map,
            status=status
        )
        
        # Generate AI audit explanation
        triplet.ai_explanation = self.audit_generator.generate_match_explanation(
            lr.entities or {},
            pod.entities or {},
            invoice.entities or {},
            match_score,
            self.validator.results_to_dict(validation_results),
            status
        )
        
        db.add(triplet)
        
        # Stage 6: Fraud Detection
        triplet_data = {
            'lr_entities': lr.entities or {},
            'pod_entities': pod.entities or {},
            'invoice_entities': invoice.entities or {}
        }
        
        # Get historical triplets for comparison
        historical = self._get_recent_triplets(db, limit=100)
        
        # Get vendor profile
        vendor_name = (invoice.entities or {}).get('party_name')
        vendor_profile = None
        if vendor_name:
            from app.models.vendor_profile import VendorProfile
            vendor_profile = db.query(VendorProfile).filter(
                VendorProfile.vendor_name == vendor_name
            ).first()
        
        # Run fraud detection
        risk_score, fraud_alerts = self.fraud_detector.detect(
            triplet_data,
            vendor_profile.__dict__ if vendor_profile else None,
            [self._triplet_to_dict(t) for t in historical]
        )
        
        # Create fraud alerts
        for alert in fraud_alerts:
            fraud_alert = FraudAlert(
                triplet=triplet,
                risk_score=alert.risk_score,
                alert_type=alert.alert_type,
                details=alert.details,
                ai_reasoning=alert.reasoning
            )
            db.add(fraud_alert)
            
            # If high risk, change status to review
            if alert.risk_score > 0.7:
                triplet.status = TripletStatus.REVIEW
        
        # Update vendor profile
        if vendor_name:
            origin = (invoice.entities or {}).get('origin')
            dest = (invoice.entities or {}).get('destination')
            route = (origin, dest) if origin and dest else None
            self.vendor_learner.update_vendor_profile(
                db, vendor_name, invoice.entities or {}, route
            )
        
        # Mark documents as matched
        lr.status = DocumentStatus.MATCHED
        pod.status = DocumentStatus.MATCHED
        invoice.status = DocumentStatus.MATCHED
        
        db.commit()
        
        # Write audit log: triplet creation
        self._write_audit(
            db, triplet, action="CREATED",
            ai_text=triplet.ai_explanation or f"Triplet created with status {status}.",
            context={"match_score": match_score, "confidence": confidence, "status": str(status)}
        )
        db.commit()
        return triplet
    
    def approve_triplet(self, db: Session, triplet_id: str, user_id: str, notes: str = None) -> Optional[Triplet]:
        """Approve a triplet."""
        triplet = db.query(Triplet).filter(Triplet.id == triplet_id).first()
        if not triplet:
            return None
        
        triplet.status = TripletStatus.APPROVED
        triplet.reviewed_at = datetime.now()
        triplet.reviewed_by = user_id
        triplet.review_notes = notes
        
        # Update AI explanation
        lr = db.query(Document).filter(Document.id == triplet.lr_id).first()
        pod = db.query(Document).filter(Document.id == triplet.pod_id).first()
        invoice = db.query(Document).filter(Document.id == triplet.invoice_id).first()
        
        triplet.ai_explanation = self.audit_generator.generate_match_explanation(
            lr.entities or {},
            pod.entities or {},
            invoice.entities or {},
            triplet.match_score,
            triplet.validation_details or [],
            "APPROVED"
        )
        
        db.commit()
        
        # Write audit log: manual approval
        self._write_audit(
            db, triplet, action="APPROVED",
            ai_text=triplet.ai_explanation or "Triplet manually approved.",
            context={"reviewed_by": user_id, "notes": notes},
            user_id=user_id
        )
        db.commit()
        return triplet
    
    def reject_triplet(self, db: Session, triplet_id: str, user_id: str, notes: str = None) -> Optional[Triplet]:
        """Reject a triplet."""
        triplet = db.query(Triplet).filter(Triplet.id == triplet_id).first()
        if not triplet:
            return None
        
        triplet.status = TripletStatus.REJECTED
        triplet.reviewed_at = datetime.now()
        triplet.reviewed_by = user_id
        triplet.review_notes = notes
        
        db.commit()
        
        # Write audit log: rejection
        self._write_audit(
            db, triplet, action="REJECTED",
            ai_text=f"Triplet rejected by reviewer. Notes: {notes or 'None'}.",
            context={"reviewed_by": user_id, "notes": notes},
            user_id=user_id
        )
        db.commit()
        return triplet
    
    def get_triplet(self, db: Session, triplet_id: str) -> Optional[Triplet]:
        """Get a triplet by ID."""
        return db.query(Triplet).filter(Triplet.id == triplet_id).first()
    
    def get_triplets(
        self,
        db: Session,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Triplet], dict]:
        """Get triplets with stats."""
        query = db.query(Triplet)
        
        if status:
            query = query.filter(Triplet.status == status)
        
        total = query.count()
        triplets = query.order_by(Triplet.created_at.desc()).offset(skip).limit(limit).all()
        
        # Get stats
        stats = {
            'total': total,
            'pending_review': db.query(Triplet).filter(Triplet.status == TripletStatus.REVIEW).count(),
            'auto_approved': db.query(Triplet).filter(Triplet.status == TripletStatus.AUTO_APPROVED).count(),
            'flagged': db.query(Triplet).filter(Triplet.status == TripletStatus.REVIEW).count()
        }
        
        return triplets, stats
    
    # ── Private helpers ──────────────────────────────────────────────────────

    def _write_audit(
        self,
        db: Session,
        triplet: Triplet,
        action: str,
        ai_text: str,
        context: dict = None,
        user_id: str = None
    ) -> None:
        """Persist a single AuditLog record for a triplet action."""
        log = AuditLog(
            triplet_id=triplet.id,
            action=action,
            ai_generated=ai_text,
            context=context or {},
            user_id=user_id,
        )
        db.add(log)
    
    def _doc_to_dict(self, doc: Document) -> dict:
        """Convert document to dict for matcher."""
        return {
            'id': doc.id,
            'type': doc.type,
            'entities': doc.entities or {},
            'text_blocks': doc.text_blocks or [],
            'ocr_text': doc.ocr_text or '',
            'embedding': doc.embedding  # Include embedding for contrastive learning
        }
    
    def _triplet_to_dict(self, triplet: Triplet) -> dict:
        """Convert triplet to dict for fraud detection.
        
        Populates entity fields from the linked Document relationships so that
        historical duplicate, vendor-frequency, and amount-comparison checks
        in FraudDetector have real data to work with.
        """
        return {
            'id': triplet.id,
            'lr_entities': (triplet.lr.entities or {}) if triplet.lr else {},
            'pod_entities': (triplet.pod.entities or {}) if triplet.pod else {},
            'invoice_entities': (triplet.invoice.entities or {}) if triplet.invoice else {},
            'created_at': triplet.created_at
        }
    
    def _get_recent_triplets(self, db: Session, limit: int = 100) -> List[Triplet]:
        """Get recent triplets for comparison.
        
        Uses joinedload to fetch all linked Documents in a single query,
        avoiding N+1 lazy-load queries when _triplet_to_dict reads their entities.
        """
        return (
            db.query(Triplet)
            .options(
                joinedload(Triplet.lr),
                joinedload(Triplet.pod),
                joinedload(Triplet.invoice),
            )
            .order_by(Triplet.created_at.desc())
            .limit(limit)
            .all()
        )
