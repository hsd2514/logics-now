"""
Automated Dispute Resolution Agent Service.

Analyses a matched Triplet, identifies the root-cause failure scenario,
and generates a professional dispute email draft — ready for human review
and one-click dispatch. No email is sent without explicit user approval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.triplet import Triplet


# ---------------------------------------------------------------------------
# Dispute scenario classification
# ---------------------------------------------------------------------------

class DisputeScenario(str, Enum):
    AMOUNT_OVERBILLING     = "AMOUNT_OVERBILLING"
    AMOUNT_UNDERBILLING    = "AMOUNT_UNDERBILLING"
    MISSING_POD            = "MISSING_POD"
    SEQUENCE_ERROR         = "SEQUENCE_ERROR"       # invoice_date < pod_date
    SHIPMENT_ID_MISMATCH   = "SHIPMENT_ID_MISMATCH"
    PARTY_NAME_MISMATCH    = "PARTY_NAME_MISMATCH"
    GENERAL_DISCREPANCY    = "GENERAL_DISCREPANCY"


@dataclass
class DisputeDraft:
    """Full output produced by the Dispute Resolution Agent."""

    triplet_id:   str
    scenario:     DisputeScenario
    severity:     str                      # HIGH | MEDIUM | LOW
    subject:      str
    body:         str
    discrepancies: List[Dict]              # list of {field, lr_val, pod_val, inv_val, delta}
    recommended_action: str
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ---------------------------------------------------------------------------
# Template library
# ---------------------------------------------------------------------------

_TEMPLATES: Dict[DisputeScenario, Dict] = {

    DisputeScenario.AMOUNT_OVERBILLING: {
        "subject": "Dispute: Invoice {invoice_id} – Over-billing of {currency}{delta}",
        "body": (
            "Dear {vendor_name} Finance Team,\n\n"
            "Our AI-powered document intelligence system (FreightIQ) has automatically "
            "detected a billing discrepancy while reconciling the following logistics documents:\n\n"
            "  • Lorry Receipt : {lr_id}\n"
            "  • Proof of Delivery: {pod_id}\n"
            "  • Invoice        : {invoice_id}\n\n"
            "Issue Identified — Amount Over-billing:\n"
            "  Invoiced amount  : {currency}{invoice_amount}\n"
            "  Agreed/LR amount : {currency}{lr_amount}\n"
            "  Variance         : {currency}{delta} ({variance_pct}% above agreed rate)\n\n"
            "The POD on file confirms delivery was completed on {pod_date}, with the "
            "consignment details matching Shipment ID: {shipment_id}.\n\n"
            "Action Required:\n"
            "Please issue a corrected invoice for {currency}{lr_amount} or provide written "
            "justification for the additional {currency}{delta} charge within 5 business days "
            "so we can release payment without further delay.\n\n"
            "This dispute has been automatically logged in our compliance audit trail "
            "(Ref: DISPUTE-{triplet_short_id}).\n\n"
            "Regards,\n"
            "FreightIQ — Automated Finance Reconciliation\n"
        ),
    },

    DisputeScenario.AMOUNT_UNDERBILLING: {
        "subject": "Query: Invoice {invoice_id} – Possible Under-billing of {currency}{delta}",
        "body": (
            "Dear {vendor_name} Finance Team,\n\n"
            "Our reconciliation system (FreightIQ) has flagged a potential under-billing "
            "in the following document set:\n\n"
            "  • Lorry Receipt : {lr_id}\n"
            "  • Proof of Delivery: {pod_id}\n"
            "  • Invoice        : {invoice_id}\n\n"
            "Issue Identified — Invoiced Amount Below LR Rate:\n"
            "  Invoiced amount  : {currency}{invoice_amount}\n"
            "  LR agreed amount : {currency}{lr_amount}\n"
            "  Difference       : {currency}{delta}\n\n"
            "Please confirm whether this is intentional (e.g., a credit note or discount) "
            "or if a revised invoice is required.\n\n"
            "Dispute Reference: DISPUTE-{triplet_short_id}\n\n"
            "Regards,\n"
            "FreightIQ — Automated Finance Reconciliation\n"
        ),
    },

    DisputeScenario.MISSING_POD: {
        "subject": "Dispute: Invoice {invoice_id} – No Proof of Delivery on Record",
        "body": (
            "Dear {vendor_name} Finance Team,\n\n"
            "Payment for Invoice {invoice_id} (Amount: {currency}{invoice_amount}) cannot "
            "be processed because our system has not received a valid Proof of Delivery (POD) "
            "for the associated Lorry Receipt {lr_id}.\n\n"
            "Shipment ID: {shipment_id}\n"
            "Invoice Date: {invoice_date}\n\n"
            "Action Required:\n"
            "Please share the signed POD document at your earliest convenience. "
            "Payment will be initiated within 2 business days of receipt.\n\n"
            "Dispute Reference: DISPUTE-{triplet_short_id}\n\n"
            "Regards,\n"
            "FreightIQ — Automated Finance Reconciliation\n"
        ),
    },

    DisputeScenario.SEQUENCE_ERROR: {
        "subject": "Dispute: Invoice {invoice_id} – Invalid Document Date Sequence",
        "body": (
            "Dear {vendor_name} Finance Team,\n\n"
            "Our reconciliation engine has detected a logical date-sequence error in the "
            "following document set, which prevents invoice approval:\n\n"
            "  • Lorry Receipt    : {lr_id} (Date: {lr_date})\n"
            "  • Proof of Delivery: {pod_id} (Date: {pod_date})\n"
            "  • Invoice          : {invoice_id} (Date: {invoice_date})\n\n"
            "Issue:\n"
            "The Invoice Date ({invoice_date}) appears earlier than or equal to the "
            "Proof of Delivery Date ({pod_date}). An invoice should only be raised "
            "after delivery is confirmed.\n\n"
            "Action Required:\n"
            "Please provide clarification or re-issue the invoice with a correct date. "
            "No payment will be processed until the date sequence is validated.\n\n"
            "Dispute Reference: DISPUTE-{triplet_short_id}\n\n"
            "Regards,\n"
            "FreightIQ — Automated Finance Reconciliation\n"
        ),
    },

    DisputeScenario.SHIPMENT_ID_MISMATCH: {
        "subject": "Dispute: Invoice {invoice_id} – Shipment ID Mismatch Across Documents",
        "body": (
            "Dear {vendor_name} Finance Team,\n\n"
            "Our AI reconciliation system has detected a Shipment ID mismatch across "
            "the following documents:\n\n"
            "  • LR Shipment ID     : {lr_shipment_id}\n"
            "  • POD Shipment ID    : {pod_shipment_id}\n"
            "  • Invoice Shipment ID: {inv_shipment_id}\n\n"
            "These references must match for automated payment processing. "
            "Please verify and resubmit the corrected documents.\n\n"
            "Dispute Reference: DISPUTE-{triplet_short_id}\n\n"
            "Regards,\n"
            "FreightIQ — Automated Finance Reconciliation\n"
        ),
    },

    DisputeScenario.PARTY_NAME_MISMATCH: {
        "subject": "Dispute: Invoice {invoice_id} – Consignee/Party Name Inconsistency",
        "body": (
            "Dear {vendor_name} Finance Team,\n\n"
            "A party-name inconsistency has been detected across the following documents:\n\n"
            "  • LR Party Name     : {lr_party}\n"
            "  • POD Party Name    : {pod_party}\n"
            "  • Invoice Party Name: {inv_party}\n\n"
            "All three documents must reference the same consignee/shipper to "
            "satisfy compliance requirements. Please resubmit with consistent party names.\n\n"
            "Dispute Reference: DISPUTE-{triplet_short_id}\n\n"
            "Regards,\n"
            "FreightIQ — Automated Finance Reconciliation\n"
        ),
    },

    DisputeScenario.GENERAL_DISCREPANCY: {
        "subject": "Dispute: Invoice {invoice_id} – Multiple Field Discrepancies Detected",
        "body": (
            "Dear {vendor_name} Finance Team,\n\n"
            "Our automated reconciliation system (FreightIQ) has flagged multiple "
            "discrepancies in the following document set (Match Score: {match_score}%):\n\n"
            "  • Lorry Receipt    : {lr_id}\n"
            "  • Proof of Delivery: {pod_id}\n"
            "  • Invoice          : {invoice_id}\n\n"
            "Discrepancies Detected:\n"
            "{discrepancy_table}\n"
            "Please review and resubmit corrected documentation. "
            "Payment is on hold pending resolution.\n\n"
            "Dispute Reference: DISPUTE-{triplet_short_id}\n\n"
            "Regards,\n"
            "FreightIQ — Automated Finance Reconciliation\n"
        ),
    },
}


# ---------------------------------------------------------------------------
# Core service
# ---------------------------------------------------------------------------

class DisputeService:
    """
    Automated Dispute Resolution Agent.

    Usage:
        service = DisputeService()
        draft = service.generate_dispute_draft(db, triplet)
        # present `draft` to the user; call `record_dispute_sent` after approval
    """

    AMOUNT_VARIANCE_THRESHOLD = 0.03   # 3% triggers dispute
    LOW_MATCH_SCORE_THRESHOLD = 0.65   # below this → GENERAL_DISCREPANCY
    CURRENCY_SYMBOL = "₹"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_dispute_draft(
        self,
        db: Session,
        triplet: Triplet,
    ) -> Optional[DisputeDraft]:
        """
        Analyse *triplet* and return a ready-to-edit dispute email draft,
        or None if no disputable condition is detected.
        """
        lr_doc, pod_doc, inv_doc = self._load_docs(db, triplet)

        lr_ent  = (lr_doc.entities  or {}) if lr_doc  else {}
        pod_ent = (pod_doc.entities or {}) if pod_doc else {}
        inv_ent = (inv_doc.entities or {}) if inv_doc else {}

        field_matches = triplet.field_matches or {} if hasattr(triplet, "field_matches") else {}

        # Classify the primary dispute scenario
        scenario, discrepancies = self._classify_scenario(
            lr_ent, pod_ent, inv_ent, field_matches, triplet
        )

        if scenario is None:
            return None  # no dispute needed

        severity = self._compute_severity(triplet.match_score, discrepancies)

        # Build template variables
        ctx = self._build_context(triplet, lr_doc, pod_doc, inv_doc, lr_ent, pod_ent, inv_ent, discrepancies)
        ctx["match_score"] = str(round((triplet.match_score or 0) * 100))

        # Select and render template
        tmpl = _TEMPLATES[scenario]
        subject = self._render(tmpl["subject"], ctx)
        body    = self._render(tmpl["body"],    ctx)

        return DisputeDraft(
            triplet_id=triplet.id,
            scenario=scenario,
            severity=severity,
            subject=subject,
            body=body,
            discrepancies=discrepancies,
            recommended_action=self._recommended_action(scenario),
        )

    def record_dispute_sent(
        self,
        db: Session,
        triplet: Triplet,
        draft: DisputeDraft,
        approved_subject: str,
        approved_body: str,
        sent_by: Optional[str] = None,
    ) -> AuditLog:
        """
        Called after the user reviews and approves the draft.
        Writes an immutable AuditLog entry; does NOT send email
        (email delivery is handled by the caller / email gateway).
        """
        log = AuditLog(
            triplet_id=triplet.id,
            action="DISPUTE_SENT",
            ai_generated=(
                f"Dispute email drafted by AI agent (scenario: {draft.scenario.value}, "
                f"severity: {draft.severity}) and approved for dispatch by user '{sent_by or 'unknown'}'.\n"
                f"Subject: {approved_subject}"
            ),
            context={
                "scenario":        draft.scenario.value,
                "severity":        draft.severity,
                "subject":         approved_subject,
                "body":            approved_body,
                "discrepancies":   draft.discrepancies,
                "generated_at":    draft.generated_at,
                "sent_by":         sent_by,
            },
            user_id=sent_by,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    # ------------------------------------------------------------------
    # Classification logic
    # ------------------------------------------------------------------

    def _classify_scenario(
        self,
        lr_ent: Dict,
        pod_ent: Dict,
        inv_ent: Dict,
        field_matches: Dict,
        triplet: Triplet,
    ) -> Tuple[Optional[DisputeScenario], List[Dict]]:
        """
        Walk through prioritised failure checks and return the first
        matching scenario along with structured discrepancy details.
        """
        discrepancies: List[Dict] = []

        # ── Scenario B: Missing POD ───────────────────────────────────
        if not pod_ent:
            return DisputeScenario.MISSING_POD, []

        # ── Scenario A: Amount variance ───────────────────────────────
        lr_amt  = self._to_float(lr_ent.get("amount"))
        inv_amt = self._to_float(inv_ent.get("amount"))
        pod_amt = self._to_float(pod_ent.get("amount"))

        if lr_amt and inv_amt:
            variance = (inv_amt - lr_amt) / lr_amt
            if abs(variance) > self.AMOUNT_VARIANCE_THRESHOLD:
                discrepancies.append({
                    "field": "amount",
                    "lr_val": lr_amt,
                    "pod_val": pod_amt,
                    "inv_val": inv_amt,
                    "delta": round(abs(inv_amt - lr_amt), 2),
                    "variance_pct": round(abs(variance) * 100, 2),
                })
                return (
                    DisputeScenario.AMOUNT_OVERBILLING if inv_amt > lr_amt
                    else DisputeScenario.AMOUNT_UNDERBILLING,
                    discrepancies,
                )

        # ── Scenario C: Date sequence error ───────────────────────────
        inv_date = self._parse_date(inv_ent.get("date") or inv_ent.get("invoice_date"))
        pod_date = self._parse_date(pod_ent.get("date") or pod_ent.get("delivery_date"))
        lr_date  = self._parse_date(lr_ent.get("date")  or lr_ent.get("booking_date"))

        if inv_date and pod_date and inv_date <= pod_date:
            discrepancies.append({
                "field": "date_sequence",
                "lr_val":  str(lr_date.date()) if lr_date else "–",
                "pod_val": str(pod_date.date()),
                "inv_val": str(inv_date.date()),
                "delta": None,
                "variance_pct": None,
            })
            return DisputeScenario.SEQUENCE_ERROR, discrepancies

        # ── Shipment ID mismatch ──────────────────────────────────────
        fm_ship = field_matches.get("shipment_id", {})
        if fm_ship.get("score", 1.0) < 0.7:
            discrepancies.append({
                "field": "shipment_id",
                "lr_val":  lr_ent.get("shipment_id", "–"),
                "pod_val": pod_ent.get("shipment_id", "–"),
                "inv_val": inv_ent.get("shipment_id", "–"),
                "delta": None,
                "variance_pct": None,
            })
            return DisputeScenario.SHIPMENT_ID_MISMATCH, discrepancies

        # ── Party name mismatch ───────────────────────────────────────
        fm_party = field_matches.get("party_name", {})
        if fm_party.get("score", 1.0) < 0.7:
            discrepancies.append({
                "field": "party_name",
                "lr_val":  lr_ent.get("party_name", "–"),
                "pod_val": pod_ent.get("party_name", "–"),
                "inv_val": inv_ent.get("party_name", "–"),
                "delta": None,
                "variance_pct": None,
            })
            return DisputeScenario.PARTY_NAME_MISMATCH, discrepancies

        # ── General low match score ───────────────────────────────────
        if (triplet.match_score or 1.0) < self.LOW_MATCH_SCORE_THRESHOLD:
            for field_name, fm in field_matches.items():
                if isinstance(fm, dict) and fm.get("score", 1.0) < 0.6:
                    vals = fm.get("values", {})
                    discrepancies.append({
                        "field": field_name,
                        "lr_val":  vals.get("lr",      "–"),
                        "pod_val": vals.get("pod",     "–"),
                        "inv_val": vals.get("invoice", "–"),
                        "delta": None,
                        "variance_pct": None,
                    })
            if discrepancies:
                return DisputeScenario.GENERAL_DISCREPANCY, discrepancies

        return None, []

    # ------------------------------------------------------------------
    # Context + rendering helpers
    # ------------------------------------------------------------------

    def _build_context(
        self,
        triplet: Triplet,
        lr_doc, pod_doc, inv_doc,
        lr_ent: Dict, pod_ent: Dict, inv_ent: Dict,
        discrepancies: List[Dict],
    ) -> Dict[str, str]:
        """Build the template substitution dictionary."""
        short_id = triplet.id[:8].upper()

        vendor_name = (
            inv_ent.get("party_name")
            or lr_ent.get("party_name")
            or pod_ent.get("party_name")
            or "Logistics Partner"
        )

        shipment_id = (
            lr_ent.get("shipment_id")
            or pod_ent.get("shipment_id")
            or inv_ent.get("shipment_id")
            or "N/A"
        )

        lr_amt  = self._to_float(lr_ent.get("amount"))
        inv_amt = self._to_float(inv_ent.get("amount"))

        delta = round(abs((inv_amt or 0) - (lr_amt or 0)), 2) if (lr_amt and inv_amt) else 0.0
        variance_pct = (
            round(abs(((inv_amt or 0) - (lr_amt or 0)) / lr_amt) * 100, 2)
            if lr_amt else 0.0
        )

        # Discrepancy table for GENERAL template
        discrepancy_lines = []
        for d in discrepancies:
            discrepancy_lines.append(
                f"  Field '{d['field']}': LR={d['lr_val']} | POD={d['pod_val']} | "
                f"Invoice={d['inv_val']}"
            )
        discrepancy_table = "\n".join(discrepancy_lines) if discrepancy_lines else "  (See audit log)"

        return {
            "triplet_short_id": short_id,
            "lr_id":            lr_doc.file_name if lr_doc else triplet.lr_id[:8],
            "pod_id":           pod_doc.file_name if pod_doc else triplet.pod_id[:8],
            "invoice_id":       inv_doc.file_name if inv_doc else triplet.invoice_id[:8],
            "vendor_name":      vendor_name,
            "currency":         self.CURRENCY_SYMBOL,
            "lr_amount":        f"{lr_amt:,.2f}" if lr_amt else "N/A",
            "invoice_amount":   f"{inv_amt:,.2f}" if inv_amt else "N/A",
            "delta":            f"{delta:,.2f}",
            "variance_pct":     str(variance_pct),
            "shipment_id":      shipment_id,
            "lr_shipment_id":   lr_ent.get("shipment_id", "–"),
            "pod_shipment_id":  pod_ent.get("shipment_id", "–"),
            "inv_shipment_id":  inv_ent.get("shipment_id", "–"),
            "lr_party":         lr_ent.get("party_name", "–"),
            "pod_party":        pod_ent.get("party_name", "–"),
            "inv_party":        inv_ent.get("party_name", "–"),
            "lr_date":          lr_ent.get("date") or lr_ent.get("booking_date") or "–",
            "pod_date":         pod_ent.get("date") or pod_ent.get("delivery_date") or "–",
            "invoice_date":     inv_ent.get("date") or "–",
            "discrepancy_table": discrepancy_table,
            "match_score":      "0",  # overwritten by caller
        }

    @staticmethod
    def _render(template: str, ctx: Dict[str, str]) -> str:
        """Simple {key} substitution; missing keys are replaced with '–'."""
        def replace(match):
            key = match.group(1)
            return str(ctx.get(key, "–"))
        return re.sub(r"\{(\w+)\}", replace, template)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _load_docs(
        self, db: Session, triplet: Triplet
    ) -> Tuple[Optional[Document], Optional[Document], Optional[Document]]:
        lr_doc  = db.query(Document).filter(Document.id == triplet.lr_id).first()
        pod_doc = db.query(Document).filter(Document.id == triplet.pod_id).first()
        inv_doc = db.query(Document).filter(Document.id == triplet.invoice_id).first()
        return lr_doc, pod_doc, inv_doc

    @staticmethod
    def _to_float(val) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(str(val).replace(",", ""))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_date(val: Optional[str]) -> Optional[datetime]:
        if not val:
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y"):
            try:
                return datetime.strptime(str(val).strip(), fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _compute_severity(match_score: Optional[float], discrepancies: List[Dict]) -> str:
        score = match_score or 0.5
        if score < 0.5 or any(d.get("variance_pct", 0) and d["variance_pct"] > 10 for d in discrepancies):
            return "HIGH"
        if score < 0.75:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _recommended_action(scenario: DisputeScenario) -> str:
        return {
            DisputeScenario.AMOUNT_OVERBILLING:   "Request corrected invoice from vendor.",
            DisputeScenario.AMOUNT_UNDERBILLING:  "Seek vendor confirmation or credit note.",
            DisputeScenario.MISSING_POD:          "Request signed POD before releasing payment.",
            DisputeScenario.SEQUENCE_ERROR:       "Request re-issued invoice with correct date.",
            DisputeScenario.SHIPMENT_ID_MISMATCH: "Resubmit documents with consistent Shipment IDs.",
            DisputeScenario.PARTY_NAME_MISMATCH:  "Resubmit documents with consistent party names.",
            DisputeScenario.GENERAL_DISCREPANCY:  "Review all flagged fields and resubmit.",
        }.get(scenario, "Contact vendor for clarification.")
