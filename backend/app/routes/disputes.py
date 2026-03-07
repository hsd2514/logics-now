"""
Dispute Resolution routes.

POST /disputes/{triplet_id}/draft   — generate an AI dispute email draft
POST /disputes/{triplet_id}/send    — record user-approved draft as sent (audit log)
GET  /disputes/{triplet_id}/history — list all dispute audit entries for a triplet
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.triplet import Triplet
from app.models.audit_log import AuditLog
from app.services.dispute_service import DisputeService, DisputeDraft

router = APIRouter()
_dispute_service = DisputeService()


# ---------------------------------------------------------------------------
# Request / Response schemas (inline — no extra schema file needed)
# ---------------------------------------------------------------------------

class DisputeDraftResponse(BaseModel):
    triplet_id:         str
    scenario:           str
    severity:           str
    subject:            str
    body:               str
    discrepancies:      List[dict]
    recommended_action: str
    generated_at:       str

    model_config = {"from_attributes": True}


class SendDisputeRequest(BaseModel):
    subject:  str
    body:     str
    sent_by:  Optional[str] = None


class DisputeHistoryEntry(BaseModel):
    id:           str
    action:       str
    ai_generated: str
    context:      Optional[dict]
    timestamp:    str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/{triplet_id}/draft", response_model=DisputeDraftResponse)
def generate_draft(triplet_id: str, db: Session = Depends(get_db)):
    """
    Ask the Dispute Resolution Agent to analyse the triplet and return
    a ready-to-edit dispute email. Returns 204 if no dispute is needed.
    """
    triplet = db.query(Triplet).filter(Triplet.id == triplet_id).first()
    if not triplet:
        raise HTTPException(status_code=404, detail="Triplet not found")

    draft: Optional[DisputeDraft] = _dispute_service.generate_dispute_draft(db, triplet)
    if draft is None:
        raise HTTPException(
            status_code=204,
            detail="No disputable condition detected for this triplet.",
        )

    return DisputeDraftResponse(
        triplet_id=draft.triplet_id,
        scenario=draft.scenario.value,
        severity=draft.severity,
        subject=draft.subject,
        body=draft.body,
        discrepancies=draft.discrepancies,
        recommended_action=draft.recommended_action,
        generated_at=draft.generated_at,
    )


@router.post("/{triplet_id}/send")
def record_dispute_sent(
    triplet_id: str,
    payload: SendDisputeRequest,
    db: Session = Depends(get_db),
):
    """
    Called after the user reviews, edits if needed, and approves the draft.
    Writes an immutable AuditLog entry. Email delivery is the caller's responsibility.
    """
    triplet = db.query(Triplet).filter(Triplet.id == triplet_id).first()
    if not triplet:
        raise HTTPException(status_code=404, detail="Triplet not found")

    # Re-generate draft to get scenario/severity metadata (fast, no LLM call)
    draft = _dispute_service.generate_dispute_draft(db, triplet)

    # Even if no auto-draft (manual dispute), record the log
    if draft is None:
        from app.services.dispute_service import DisputeScenario
        from dataclasses import dataclass, field as dc_field
        from datetime import datetime as dt

        _tid = triplet.id

        class _FallbackDraft:
            triplet_id = _tid
            scenario = type("S", (), {"value": "MANUAL"})()
            severity = "MEDIUM"
            discrepancies = []
            generated_at = dt.utcnow().isoformat()

        draft = _FallbackDraft()

    log = _dispute_service.record_dispute_sent(
        db=db,
        triplet=triplet,
        draft=draft,
        approved_subject=payload.subject,
        approved_body=payload.body,
        sent_by=payload.sent_by,
    )

    return {
        "message": "Dispute recorded in audit trail.",
        "audit_log_id": log.id,
    }


@router.get("/{triplet_id}/history", response_model=List[DisputeHistoryEntry])
def dispute_history(triplet_id: str, db: Session = Depends(get_db)):
    """Return all DISPUTE_SENT audit entries for a triplet."""
    triplet = db.query(Triplet).filter(Triplet.id == triplet_id).first()
    if not triplet:
        raise HTTPException(status_code=404, detail="Triplet not found")

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.triplet_id == triplet_id, AuditLog.action == "DISPUTE_SENT")
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    return [
        DisputeHistoryEntry(
            id=log.id,
            action=log.action,
            ai_generated=log.ai_generated,
            context=log.context,
            timestamp=log.timestamp.isoformat() if log.timestamp else "",
        )
        for log in logs
    ]
