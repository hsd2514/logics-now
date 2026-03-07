from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.ai.audit_generator import AuditGenerator
from app.ai.vendor_patterns import VendorPatternLearner
from app.config import get_settings
from app.models.audit_log import AuditLog
from app.models.contract_rate import ContractRate
from app.models.document import Document, DocumentStatus
from app.models.fraud_alert import FraudAlert
from app.models.triplet import Triplet, TripletStatus
from app.models.vendor_profile import VendorProfile
from app.pipeline.fraud_detector import FraudDetector
from app.pipeline.triplet_matcher import TripletMatcher
from app.pipeline.validator import Validator
from app.services.vendor_service import VendorService

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

    def match_documents(self, db: Session) -> Tuple[List[Triplet], List[dict]]:
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

        matches = self.matcher.find_best_matches(
            [self._doc_to_dict(d) for d in lrs],
            [self._doc_to_dict(d) for d in pods],
            [self._doc_to_dict(d) for d in invoices],
        )

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
    ) -> Tuple[Optional[Triplet], List[dict]]:
        lr = db.query(Document).filter(Document.id == lr_id).first()
        pod = db.query(Document).filter(Document.id == pod_id).first()
        invoice = db.query(Document).filter(Document.id == invoice_id).first()
        if not (lr and pod and invoice):
            return None, []

        lr_entities = lr.entities or {}
        pod_entities = pod.entities or {}
        invoice_entities = invoice.entities or {}

        contract_rate = self._get_contract_rate(db, invoice_entities)
        contract_rate_payload = self._contract_rate_to_dict(contract_rate)

        validation_results, rule_pass_score = self.validator.validate_triplet(
            lr_entities,
            pod_entities,
            invoice_entities,
            contract_rate_payload,
        )
        validation_payload = self.validator.results_to_dict(validation_results)

        confidence = (
            settings.match_weight * match_score
            + settings.ocr_weight * (lr.ocr_confidence or 0.8)
            + settings.ner_weight * initial_confidence
            + settings.rule_weight * rule_pass_score
        )

        if confidence >= settings.auto_approve_threshold:
            status = TripletStatus.AUTO_APPROVED
        elif confidence >= settings.confidence_threshold:
            status = TripletStatus.PENDING
        else:
            status = TripletStatus.REVIEW

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
            partial_delivery=self._is_partial_delivery(lr_entities, pod_entities),
            attention_map=attention_map,
            status=status,
        )

        triplet.ai_explanation = self.audit_generator.generate_match_explanation(
            lr_entities,
            pod_entities,
            invoice_entities,
            match_score,
            validation_payload,
            status,
        )

        db.add(triplet)
        db.flush()

        pending_events: List[dict] = []
        triplet_data = self._triplet_to_dict(db, triplet)
        historical = self._get_recent_triplets(db, limit=100)

        vendor_name = invoice_entities.get("party_name")
        vendor_profile = (
            db.query(VendorProfile).filter(VendorProfile.vendor_name == vendor_name).first()
            if vendor_name
            else None
        )

        _, fraud_alerts = self.fraud_detector.detect(
            triplet_data,
            vendor_profile.__dict__ if vendor_profile else None,
            [self._triplet_to_dict(db, t) for t in historical],
            contract_rate_payload,
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
            origin = invoice_entities.get("origin", "")
            dest = invoice_entities.get("destination", "")
            route = f"{origin}-{dest}" if origin and dest else ""
            amount = invoice_entities.get("amount", 0)

            date_str = invoice_entities.get("date")
            invoice_date = self._parse_doc_date(date_str) or datetime.now()

            self.vendor_service.update_vendor_profile(
                db,
                vendor_name,
                float(amount) if amount else 0.0,
                route,
                invoice_date,
            )
            self.vendor_learner.update_vendor_profile(
                db,
                vendor_name,
                invoice_entities,
                (origin, dest) if origin and dest else None,
            )

        lr.status = DocumentStatus.MATCHED
        pod.status = DocumentStatus.MATCHED
        invoice.status = DocumentStatus.MATCHED

        self._write_audit(
            db,
            triplet,
            action="CREATED",
            ai_text=triplet.ai_explanation or f"Triplet created with status {status}.",
            context={"match_score": match_score, "confidence": confidence, "status": str(status)},
        )

        db.commit()

        pending_events.append(
            {"type": "match_found", "id": triplet.id, "match_score": triplet.match_score}
        )
        return triplet, pending_events

    def approve_triplet(
        self, db: Session, triplet_id: str, user_id: str, notes: str = None
    ) -> Optional[Triplet]:
        triplet = db.query(Triplet).filter(Triplet.id == triplet_id).first()
        if not triplet:
            return None

        triplet.status = TripletStatus.APPROVED
        triplet.reviewed_at = datetime.now()
        triplet.reviewed_by = user_id
        triplet.review_notes = notes

        lr = db.query(Document).filter(Document.id == triplet.lr_id).first()
        pod = db.query(Document).filter(Document.id == triplet.pod_id).first()
        invoice = db.query(Document).filter(Document.id == triplet.invoice_id).first()

        triplet.ai_explanation = self.audit_generator.generate_match_explanation(
            (lr.entities if lr else {}) or {},
            (pod.entities if pod else {}) or {},
            (invoice.entities if invoice else {}) or {},
            triplet.match_score,
            triplet.validation_details or [],
            "APPROVED",
        )

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
        self, db: Session, triplet_id: str, user_id: str, notes: str = None
    ) -> Optional[Triplet]:
        triplet = db.query(Triplet).filter(Triplet.id == triplet_id).first()
        if not triplet:
            return None

        triplet.status = TripletStatus.REJECTED
        triplet.reviewed_at = datetime.now()
        triplet.reviewed_by = user_id
        triplet.review_notes = notes

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
    ) -> Tuple[List[Triplet], dict]:
        query = db.query(Triplet).options(
            joinedload(Triplet.invoice),
            joinedload(Triplet.fraud_alerts),
        )

        if status:
            query = query.filter(Triplet.status == status)

        if date_from:
            try:
                query = query.filter(Triplet.created_at >= datetime.strptime(date_from, "%Y-%m-%d"))
            except ValueError:
                pass

        if date_to:
            try:
                query = query.filter(Triplet.created_at <= datetime.strptime(date_to, "%Y-%m-%d"))
            except ValueError:
                pass

        triplets = query.order_by(Triplet.created_at.desc()).all()

        if vendor_name or amount_min is not None or amount_max is not None or fraud_risk:
            filtered: List[Triplet] = []
            for t in triplets:
                inv_entities = (t.invoice.entities if t.invoice else {}) or {}

                if vendor_name:
                    party = str(inv_entities.get("party_name", "")).lower()
                    if vendor_name.lower() not in party:
                        continue

                inv_amount = inv_entities.get("amount")
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

                if fraud_risk:
                    risk_map = {"HIGH": (0.7, 1.0), "MEDIUM": (0.4, 0.7), "LOW": (0.0, 0.4)}
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
            "pending_review": db.query(Triplet).filter(Triplet.status == TripletStatus.REVIEW).count(),
            "auto_approved": db.query(Triplet).filter(Triplet.status == TripletStatus.AUTO_APPROVED).count(),
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
            "embedding": getattr(doc, "embedding", []) or [],
        }

    def _triplet_to_dict(self, db: Session, triplet: Triplet) -> dict:
        lr_entities = (triplet.lr.entities or {}) if triplet.lr else {}
        pod_entities = (triplet.pod.entities or {}) if triplet.pod else {}
        invoice_entities = (triplet.invoice.entities or {}) if triplet.invoice else {}

        freq = 0.0
        amt_dev = 0.0
        route_score = 0.0

        vendor_name = invoice_entities.get("party_name")
        if vendor_name:
            profile = db.query(VendorProfile).filter(VendorProfile.vendor_name == vendor_name).first()
            if profile:
                freq = float(profile.total_invoices or 0)
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
            "partial_delivery": bool(getattr(triplet, "partial_delivery", False)),
            "frequency_score": freq,
            "amount_deviation": amt_dev,
            "route_score": route_score,
        }

    def _contract_rate_to_dict(self, rate: ContractRate | None) -> Dict[str, Any] | None:
        if not rate:
            return None
        return {
            "id": rate.id,
            "vendor_name": rate.vendor_name,
            "origin": rate.origin,
            "destination": rate.destination,
            "base_rate": rate.base_rate,
            "fuel_surcharge": rate.fuel_surcharge,
            "detention_rate": rate.detention_rate,
            "distance_rate": rate.distance_rate,
            "effective_from": rate.effective_from,
            "effective_to": rate.effective_to,
            "is_active": rate.is_active,
        }

    def _parse_doc_date(self, date_str: Any) -> datetime | None:
        if not date_str:
            return None
        if isinstance(date_str, datetime):
            return date_str
        raw = str(date_str).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None

    def _get_contract_rate(self, db: Session, invoice_entities: Dict[str, Any]) -> ContractRate | None:
        vendor_name = (
            invoice_entities.get("party_name")
            or invoice_entities.get("vendor_name")
            or ""
        ).strip()
        if not vendor_name:
            return None

        origin = str(invoice_entities.get("origin") or "").strip().lower()
        destination = str(invoice_entities.get("destination") or "").strip().lower()
        invoice_date = self._parse_doc_date(invoice_entities.get("date")) or datetime.now()

        rates = (
            db.query(ContractRate)
            .filter(ContractRate.vendor_name == vendor_name, ContractRate.is_active.is_(True))
            .all()
        )
        if not rates:
            return None

        def is_effective(r: ContractRate) -> bool:
            after_start = r.effective_from is None or invoice_date >= r.effective_from
            before_end = r.effective_to is None or invoice_date <= r.effective_to
            return after_start and before_end

        effective_rates = [r for r in rates if is_effective(r)]
        if not effective_rates:
            return None

        route_matches = []
        for rate in effective_rates:
            r_origin = str(rate.origin or "").strip().lower()
            r_destination = str(rate.destination or "").strip().lower()
            if origin and destination and r_origin == origin and r_destination == destination:
                route_matches.append(rate)

        candidates = route_matches or effective_rates
        candidates.sort(key=lambda r: r.effective_from or datetime.min, reverse=True)
        return candidates[0]

    def _is_partial_delivery(self, lr_entities: Dict[str, Any], pod_entities: Dict[str, Any]) -> bool:
        try:
            lr_weight = float(lr_entities.get("weight", 0) or 0)
            pod_weight = float(pod_entities.get("weight", 0) or 0)
        except (TypeError, ValueError):
            return False
        if lr_weight <= 0 or pod_weight <= 0:
            return False
        return (pod_weight / lr_weight) < settings.partial_delivery_min_ratio

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
