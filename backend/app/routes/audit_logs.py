"""
Audit Log routes — Issue #13 fix.

Exposes persisted AuditLog records so the UI and judges can query the full
compliance history of every triplet action.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.audit_log import AuditLog

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: str
    triplet_id: str
    action: str
    ai_generated: str
    context: Optional[dict] = None
    user_id: Optional[str] = None
    timestamp: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    logs: List[AuditLogResponse]
    total: int


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    triplet_id: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List audit logs with optional filters.
    Supports filtering by triplet_id, action type, and user_id.
    """
    query = db.query(AuditLog)

    if triplet_id:
        query = query.filter(AuditLog.triplet_id == triplet_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    total = query.count()
    logs = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
def get_audit_log(log_id: str, db: Session = Depends(get_db)):
    """Get a single audit log entry by ID."""
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return AuditLogResponse.model_validate(log)


@router.get("/triplet/{triplet_id}", response_model=AuditLogListResponse)
def get_triplet_audit_trail(triplet_id: str, db: Session = Depends(get_db)):
    """
    Get the full audit trail for a specific triplet.
    Returns all events in chronological order — creation, approvals, fraud actions.
    """
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.triplet_id == triplet_id)
        .order_by(AuditLog.timestamp.asc())
        .all()
    )
    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=len(logs),
    )
