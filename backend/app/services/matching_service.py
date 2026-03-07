from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.session import object_session

from app.ai.audit_generator import AuditGenerator
from app.ai.vendor_patterns import VendorPatternLearner
from app.services.vendor_service import VendorService
from app.config import get_settings
from app.models.audit_log import AuditLog
from app.models.document import Document, DocumentStatus
from app.models.fraud_alert import FraudAlert
from app.models.triplet import Triplet, TripletStatus
from app.models.vendor_profile import VendorProfile
from app.pipeline.active_learner import ActiveLearner
from app.pipeline.contrastive_learner import ContrastiveLearner
from app.pipeline.embedding_service import EmbeddingService
from app.pipeline.fraud_detector import FraudDetector
from app.pipeline.triplet_matcher import TripletMatcher
from app.pipeline.validator import Validator

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
        self.vendor_service = VendorService()
        self.active_learner = ActiveLearner()
        self.contrastive_learner = ContrastiveLearner()
        self.embedding_service = EmbeddingService()
    def match_documents(self, db: Session) -> Tuple[List[Triplet], List[dict]]:
        """Find and create triplet matches from unmatched documents."""
        lrs = db.query(Document).filter(
            Document.type == "LR",
            Document.status == DocumentStatus.PROCESSED,
        ).all()
        pods = db.query(Document).filter(
            Document.type == "POD",
            Document.status == DocumentStatus.PROCESSED,
        ).all()
        invoices = db.query(Document).filter(
            Document.type == "INVOICE",
            Document.status == DocumentStatus.PROCESSED,
        ).all()

        if not (lrs and pods and invoices):
            return [], []

        lr_data = [self._doc_to_dict(d) for d in lrs]
        pod_data = [self._doc_to_dict(d) for d in pods]
        invoice_data = [self._doc_to_dict(d) for d in invoices]

        matches = self.matcher.find_best_matches(lr_data, pod_data, invoice_data)

        created_triplets: List[Triplet] = []
        all_events: List[dict] = []

        for match in matches:
            triplet, events = self.create_triplet(
                db,
                match.lr_id,
                match.pod_id,
                match.invoice_id,
                match.match_score,
                match.confidence,
                match.attention_map,
                match.embedding_similarity,
                match.contrastive_score,
                match.graph_score,
            )
            if triplet:
                created_triplets.append(triplet)
                all_events.extend(events)

        return created_triplets, all_events

    def create_triplet(
        self,
        db: Session,
        lr_id: str,
        pod_id: str,
        invoice_id: str,
        match_score: float,
        initial_confidence: float,
        attention_map: List | None = None,
        embedding_similarity: float = 0.0,
        contrastive_score: float = 0.0,
        graph_score: float = 0.0,
    ) -> Tuple[Optional[Triplet], List[dict]]:
        """Create a triplet with validation, active learning, and fraud detection."""
        lr = db.query(Document).filter(Document.id == lr_id).first()
        pod = db.query(Document).filter(Document.id == pod_id).first()
        invoice = db.query(Document).filter(Document.id == invoice_id).first()
        if not (lr and pod and invoice):
            return None, []

        validation_results, rule_pass_score = self.validator.validate_triplet(
            lr.entities or {},
            pod.entities or {},
            invoice.entities or {},
        )

        base_confidence = (
            settings.match_weight * match_score
            + settings.ocr_weight * (lr.ocr_confidence or 0.8)
            + settings.ner_weight * initial_confidence
            + settings.rule_weight * rule_pass_score
        )

        ml_features = {
            "match_score": match_score,
            "ocr_accuracy": lr.ocr_confidence or 0.0,
            "ner_confidence": initial_confidence,
            "rule_pass_score": rule_pass_score,
            "embedding_similarity": embedding_similarity,
            "contrastive_score": contrastive_score,
            "graph_score": graph_score,
        }
        active_prob = self.active_learner.predict(ml_features)
        confidence = (
            (1.0 - settings.active_learning_weight) * base_confidence
            + settings.active_learning_weight * active_prob
        )

        if confidence >= settings.auto_approve_threshold:
            status = TripletStatus.AUTO_APPROVED
        elif confidence >= settings.confidence_threshold:
            status = TripletStatus.PENDING
        else:
            status = TripletStatus.REVIEW

        validation_payload = self.validator.results_to_dict(validation_results)
        validation_payload.append(
            {
                "rule": "ML_SIGNALS",
                "passed": active_prob >= 0.5,
                "expected": "active_prob >= 0.5",
                "actual": f"active_prob={active_prob:.3f}",
                "message": (
                    f"embedding_similarity={embedding_similarity:.3f}, "
                    f"contrastive_score={contrastive_score:.3f}, "
                    f"graph_score={graph_score:.3f}"
                ),
            }
        )

        triplet = Triplet(
            lr_id=lr_id,
            pod_id=pod_id,
            invoice_id=invoice_id,
            match_score=match_score,
            confidence=confidence,
            ocr_accuracy=lr.ocr_confidence,
            ner_confidence=initial_confidence,
            rule_pass_score=rule_pass_score,
            validation_details=validation_payload,
            attention_map=attention_map,
            status=status,
        )

        triplet.ai_explanation = self.audit_generator.generate_match_explanation(
            lr.entities or {},
            pod.entities or {},
            invoice.entities or {},
            match_score,
            validation_payload,
            status,
        )

        db.add(triplet)
        db.flush()

        pending_events: List[dict] = []
        for doc_id in (lr_id, pod_id, invoice_id):
            pending_events.append(
                {
                    "type": "processing_update",
                    "document_id": doc_id,
                    "stage": "MATCHING",
                    "progress": 80,
                    "message": "Running triplet matching and validation",
                }
            )

        triplet_data = self._triplet_to_dict(db, triplet)
        historical = self._get_recent_triplets(db, limit=100)

        vendor_name = (invoice.entities or {}).get("party_name")
        vendor_profile = (
            db.query(VendorProfile)
            .filter(VendorProfile.vendor_name == vendor_name)
            .first()
            if vendor_name
            else None
        )

        _, fraud_alerts = self.fraud_detector.detect(
            triplet_data,
            vendor_profile.__dict__ if vendor_profile else None,
            [self._triplet_to_dict(db, t) for t in historical],
        )
        for doc_id in (lr_id, pod_id, invoice_id):
            pending_events.append(
                {
                    "type": "processing_update",
                    "document_id": doc_id,
                    "stage": "FRAUD",
                    "progress": 92,
                    "message": "Running fraud detection checks",
                }
            )

        for alert in fraud_alerts:
            fraud_alert = FraudAlert(
                triplet=triplet,
                risk_score=alert.risk_score,
                alert_type=alert.alert_type,
                details=alert.details,
                ai_reasoning=alert.reasoning,
            )
            db.add(fraud_alert)
            db.flush()

            pending_events.append(
                {
                    "type": "fraud_alert",
                    "id": fraud_alert.id,
                    "risk_score": fraud_alert.risk_score,
                    "alert_type": fraud_alert.alert_type,
                }
            )

            if alert.risk_score > settings.fraud_high_risk_alert_threshold:
                triplet.status = TripletStatus.REVIEW

        if vendor_name:
            origin = (invoice.entities or {}).get("origin", "")
            dest = (invoice.entities or {}).get("destination", "")
            route = f"{origin}-{dest}" if origin and dest else ""
            amount = (invoice.entities or {}).get("amount", 0)

            date_str = (invoice.entities or {}).get("date")
            try:
                invoice_date = (
                    datetime.strptime(date_str, "%Y-%m-%d")
                    if date_str
                    else datetime.now()
                )
            except Exception:
                invoice_date = datetime.now()

            self.vendor_service.update_vendor_profile(
                db, vendor_name, float(amount) if amount else 0.0, route, invoice_date
            )

            self.vendor_learner.update_vendor_profile(
                db, vendor_name, invoice.entities or {}, (origin, dest) if origin and dest else None
            )

        lr.status = DocumentStatus.MATCHED
        pod.status = DocumentStatus.MATCHED
        invoice.status = DocumentStatus.MATCHED

        self._write_audit(
            db,
            triplet,
            action="CREATED",
            ai_text=triplet.ai_explanation or f"Triplet created with status {status}.",
            context={
                "match_score": match_score,
                "confidence": confidence,
                "status": str(status),
                "active_prob": active_prob,
                "embedding_similarity": embedding_similarity,
                "contrastive_score": contrastive_score,
                "graph_score": graph_score,
            },
        )

        db.commit()

        pending_events.append(
            {
                "type": "match_found",
                "id": triplet.id,
                "match_score": triplet.match_score,
            }
        )
        for doc_id in (lr_id, pod_id, invoice_id):
            pending_events.append(
                {
                    "type": "processing_update",
                    "document_id": doc_id,
                    "stage": "DONE",
                    "progress": 100,
                    "message": "Triplet matching completed",
                }
            )

        return triplet, pending_events

    def approve_triplet(
        self, db: Session, triplet_id: str, user_id: str, notes: str | None = None
    ) -> Optional[Triplet]:
        triplet = (
            db.query(Triplet)
            .options(
                joinedload(Triplet.lr),
                joinedload(Triplet.pod),
                joinedload(Triplet.invoice),
            )
            .filter(Triplet.id == triplet_id)
            .first()
        )
        if not triplet:
            return None

        triplet.status = TripletStatus.APPROVED
        triplet.reviewed_at = datetime.now()
        triplet.reviewed_by = user_id
        triplet.review_notes = notes

        triplet.ai_explanation = self.audit_generator.generate_match_explanation(
            (triplet.lr.entities if triplet.lr else {}) or {},
            (triplet.pod.entities if triplet.pod else {}) or {},
            (triplet.invoice.entities if triplet.invoice else {}) or {},
            triplet.match_score,
            triplet.validation_details or [],
            "APPROVED",
        )

        self._update_learning_from_feedback(triplet, label=1)

        self._write_audit(
            db,
            triplet,
            action="APPROVED",
            ai_text=triplet.ai_explanation or "Triplet manually approved.",
            context={"reviewed_by": user_id, "notes": notes},
            user_id=user_id,
        )
        db.commit()
        return triplet

    def reject_triplet(
        self, db: Session, triplet_id: str, user_id: str, notes: str | None = None
    ) -> Optional[Triplet]:
        triplet = (
            db.query(Triplet)
            .options(
                joinedload(Triplet.lr),
                joinedload(Triplet.pod),
                joinedload(Triplet.invoice),
            )
            .filter(Triplet.id == triplet_id)
            .first()
        )
        if not triplet:
            return None

        triplet.status = TripletStatus.REJECTED
        triplet.reviewed_at = datetime.now()
        triplet.reviewed_by = user_id
        triplet.review_notes = notes

        self._update_learning_from_feedback(triplet, label=0)

        self._write_audit(
            db,
            triplet,
            action="REJECTED",
            ai_text=f"Triplet rejected by reviewer. Notes: {notes or 'None'}.",
            context={"reviewed_by": user_id, "notes": notes},
            user_id=user_id,
        )
        db.commit()
        return triplet

    def get_triplet(self, db: Session, triplet_id: str) -> Optional[Triplet]:
        return db.query(Triplet).filter(Triplet.id == triplet_id).first()

    def get_triplets(
        self,
        db: Session,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        vendor_name: Optional[str] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        fraud_risk: Optional[str] = None,
        document_type: Optional[str] = None,
        route_origin: Optional[str] = None,
        route_destination: Optional[str] = None,
    ) -> Tuple[List[Triplet], dict]:
        query = db.query(Triplet)

        if status:
            query = query.filter(Triplet.status == status)

        if date_from:
            try:
                query = query.filter(
                    Triplet.created_at >= datetime.strptime(date_from, "%Y-%m-%d")
                )
            except ValueError:
                pass

        if date_to:
            try:
                query = query.filter(
                    Triplet.created_at <= datetime.strptime(date_to, "%Y-%m-%d")
                )
            except ValueError:
                pass

        triplets = (
            query.options(
                joinedload(Triplet.lr),
                joinedload(Triplet.pod),
                joinedload(Triplet.invoice),
                joinedload(Triplet.fraud_alerts),
            )
            .order_by(Triplet.created_at.desc())
            .all()
        )

        def _entities_for_doc_type(t: Triplet, dt: Optional[str]) -> Dict[str, Any]:
            if dt == "LR":
                return (t.lr.entities if t.lr else {}) or {}
            if dt == "POD":
                return (t.pod.entities if t.pod else {}) or {}
            return (t.invoice.entities if t.invoice else {}) or {}

        normalized_doc_type = document_type.upper() if document_type else None

        if (
            vendor_name
            or amount_min is not None
            or amount_max is not None
            or fraud_risk
            or normalized_doc_type
            or route_origin
            or route_destination
        ):
            filtered: List[Triplet] = []
            for t in triplets:
                entities = _entities_for_doc_type(t, normalized_doc_type)

                if vendor_name:
                    party = (entities.get("party_name") or "").lower()
                    if vendor_name.lower() not in party:
                        continue

                inv_amount = entities.get("amount")
                if inv_amount is not None:
                    try:
                        amt = float(inv_amount)
                        if amount_min is not None and amt < amount_min:
                            continue
                        if amount_max is not None and amt > amount_max:
                            continue
                    except (TypeError, ValueError):
                        if amount_min is not None or amount_max is not None:
                            continue

                if route_origin:
                    origin = str(entities.get("origin", "")).lower()
                    if route_origin.lower() not in origin:
                        continue

                if route_destination:
                    dest = str(entities.get("destination", "")).lower()
                    if route_destination.lower() not in dest:
                        continue

                if fraud_risk:
                    risk_map = {
                        "HIGH": (0.7, 1.0),
                        "MEDIUM": (0.4, 0.7),
                        "LOW": (0.0, 0.4),
                    }
                    lo, hi = risk_map.get(fraud_risk.upper(), (0.0, 1.0))
                    alert_risks = [a.risk_score for a in (t.fraud_alerts or [])]
                    max_risk = max(alert_risks) if alert_risks else 0.0
                    if not (lo <= max_risk <= hi):
                        continue

                filtered.append(t)
            triplets = filtered

        total = len(triplets)
        triplets_page = triplets[skip : skip + limit]

        stats = {
            "total": total,
            "pending_review": db.query(Triplet)
            .filter(Triplet.status == TripletStatus.REVIEW)
            .count(),
            "auto_approved": db.query(Triplet)
            .filter(Triplet.status == TripletStatus.AUTO_APPROVED)
            .count(),
            "flagged": db.query(FraudAlert)
            .filter(FraudAlert.risk_score > settings.fraud_high_risk_alert_threshold)
            .count(),
        }

        return triplets_page, stats

    def _write_audit(
        self,
        db: Session,
        triplet: Triplet,
        action: str,
        ai_text: str,
        context: dict | None = None,
        user_id: str | None = None,
    ) -> None:
        log = AuditLog(
            triplet_id=triplet.id,
            action=action,
            ai_generated=ai_text,
            context=context or {},
            user_id=user_id,
        )
        db.add(log)

    def _doc_to_dict(self, doc: Document) -> dict:
        return {
            "id": doc.id,
            "type": doc.type,
            "entities": doc.entities or {},
            "text_blocks": doc.text_blocks or [],
            "ocr_text": doc.ocr_text or "",
            "embedding": doc.embedding or [],
        }

    def _triplet_to_dict(
        self, db_or_triplet: Session | Triplet, triplet: Triplet | None = None
    ) -> dict:
        # Backward compatible signature:
        # - _triplet_to_dict(db, triplet)
        # - _triplet_to_dict(triplet)
        if triplet is None:
            triplet = db_or_triplet  # type: ignore[assignment]
            db = object_session(triplet)  # type: ignore[arg-type]
        else:
            db = db_or_triplet  # type: ignore[assignment]

        lr_entities = (triplet.lr.entities or {}) if triplet.lr else {}
        pod_entities = (triplet.pod.entities or {}) if triplet.pod else {}
        invoice_entities = (triplet.invoice.entities or {}) if triplet.invoice else {}

        freq = 0.0
        amt_dev = 0.0
        route_score = 0.0

        vendor_name = invoice_entities.get("party_name")
        if vendor_name and db is not None:
            profile = (
                db.query(VendorProfile)
                .filter(VendorProfile.vendor_name == vendor_name)
                .first()
            )
            if profile:
                freq = float(profile.total_invoices)
                amount = float(invoice_entities.get("amount", 0) or 0)
                avg = float(profile.avg_amount or 0)
                amt_dev = abs(amount - avg) / (avg if avg > 0 else 1.0)

                origin = str(invoice_entities.get("origin", "")).lower()
                dest = str(invoice_entities.get("destination", "")).lower()
                if origin and dest and profile.route_patterns:
                    route = f"{origin}-{dest}"
                    if route not in [r.lower() for r in profile.route_patterns]:
                        route_score = 1.0

        return {
            "id": triplet.id,
            "lr_entities": lr_entities,
            "pod_entities": pod_entities,
            "invoice_entities": invoice_entities,
            "created_at": triplet.created_at,
            "frequency_score": freq,
            "amount_deviation": amt_dev,
            "route_score": route_score,
        }

    def _get_recent_triplets(self, db: Session, limit: int = 100) -> List[Triplet]:
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

    def _update_learning_from_feedback(self, triplet: Triplet, label: int) -> None:
        lr_embedding = (triplet.lr.embedding if triplet.lr else []) or []
        pod_embedding = (triplet.pod.embedding if triplet.pod else []) or []
        inv_embedding = (triplet.invoice.embedding if triplet.invoice else []) or []

        sims = []
        if lr_embedding and pod_embedding:
            sims.append(self.embedding_service.cosine_similarity(lr_embedding, pod_embedding))
        if lr_embedding and inv_embedding:
            sims.append(self.embedding_service.cosine_similarity(lr_embedding, inv_embedding))
        if pod_embedding and inv_embedding:
            sims.append(self.embedding_service.cosine_similarity(pod_embedding, inv_embedding))

        embedding_similarity = float(sum(sims) / len(sims)) if sims else 0.0
        self.contrastive_learner.update(embedding_similarity, is_positive=label == 1)

        ml_features = {
            "match_score": triplet.match_score or 0.0,
            "ocr_accuracy": triplet.ocr_accuracy or 0.0,
            "ner_confidence": triplet.ner_confidence or 0.0,
            "rule_pass_score": triplet.rule_pass_score or 0.0,
            "embedding_similarity": embedding_similarity,
            "contrastive_score": self.contrastive_learner.score_similarity(embedding_similarity),
            "graph_score": 0.0,
        }
        self.active_learner.add_feedback(ml_features, label)
