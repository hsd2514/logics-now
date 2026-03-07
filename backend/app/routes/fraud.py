from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from typing import List
from datetime import datetime

from app.database import get_db
from app.models.fraud_alert import FraudAlert, AlertStatus
from app.models.audit_log import AuditLog
from app.schemas.fraud import FraudAlertResponse, FraudAlertListResponse, PredictiveAlertResponse
from app.ai.vendor_patterns import VendorPatternLearner
from app.utils.export_utils import to_csv_bytes, text_to_pdf_bytes

router = APIRouter()
vendor_learner = VendorPatternLearner()


@router.get("/export")
def export_alerts(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db),
):
    alerts = db.query(FraudAlert).order_by(FraudAlert.created_at.desc()).all()
    rows = [
        {
            "id": a.id,
            "triplet_id": a.triplet_id,
            "alert_type": a.alert_type,
            "risk_score": round(float(a.risk_score or 0), 4),
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else "",
        }
        for a in alerts
    ]

    if format == "csv":
        data = to_csv_bytes(rows, fieldnames=["id", "triplet_id", "alert_type", "risk_score", "status", "created_at"])
        return Response(
            content=data,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="fraud_alerts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'},
        )

    lines = [f"{r['id']} | {r['alert_type']} | risk={r['risk_score']} | {r['status']}" for r in rows]
    pdf = text_to_pdf_bytes("FreightIQ Fraud Alerts Export", lines)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="fraud_alerts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'},
    )

@router.get("/alerts", response_model=FraudAlertListResponse)
def list_alerts(
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all fraud alerts."""
    query = db.query(FraudAlert)
    
    if status:
        query = query.filter(FraudAlert.status == status)
    
    total = query.count()
    alerts = query.order_by(FraudAlert.created_at.desc()).offset(skip).limit(limit).all()
    
    open_count = db.query(FraudAlert).filter(FraudAlert.status == AlertStatus.OPEN).count()
    high_risk = db.query(FraudAlert).filter(FraudAlert.risk_score > 0.7).count()
    
    return FraudAlertListResponse(
        alerts=[FraudAlertResponse.model_validate(a) for a in alerts],
        total=total,
        open_count=open_count,
        high_risk_count=high_risk
    )

@router.get("/alerts/{alert_id}", response_model=FraudAlertResponse)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    """Get a specific fraud alert."""
    alert = db.query(FraudAlert).filter(FraudAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return FraudAlertResponse.model_validate(alert)

from fastapi import Request

# Simulated auth dependency
def get_current_user(request: Request):
    # In a real app this would decode a token. Here we simulate an authenticated user.
    return getattr(request.state, "user", "system_user")

class ActionRequest(BaseModel):
    notes: Optional[str] = None

@router.post("/alerts/{alert_id}/dismiss")
def dismiss_alert(
    alert_id: str,
    action: ActionRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Dismiss a fraud alert."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    alert = db.query(FraudAlert).filter(FraudAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = AlertStatus.DISMISSED
    alert.resolved_at = datetime.now()
    alert.resolved_by = current_user
    alert.resolution_notes = action.notes
    
    # Audit log: record the human decision to dismiss
    audit = AuditLog(
        triplet_id=alert.triplet_id,
        action="FRAUD_DISMISSED",
        ai_generated=(
            f"Fraud alert of type '{alert.alert_type}' (risk {alert.risk_score * 100:.0f}%) "
            f"was dismissed by reviewer. Notes: {action.notes or 'None'}."
        ),
        context={"alert_id": alert_id, "alert_type": alert.alert_type, "risk_score": alert.risk_score},
        user_id=current_user,
    )
    db.add(audit)
    db.commit()
    
    return {"message": "Alert dismissed", "alert_id": alert_id}

@router.post("/alerts/{alert_id}/confirm")
def confirm_alert(
    alert_id: str,
    action: ActionRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm a fraud alert as legitimate fraud."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    alert = db.query(FraudAlert).filter(FraudAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = AlertStatus.CONFIRMED
    alert.resolved_at = datetime.now()
    alert.resolved_by = current_user
    alert.resolution_notes = action.notes
    
    # Audit log: record the human decision to confirm fraud
    audit = AuditLog(
        triplet_id=alert.triplet_id,
        action="FRAUD_CONFIRMED",
        ai_generated=(
            f"Fraud alert of type '{alert.alert_type}' (risk {alert.risk_score * 100:.0f}%) "
            f"was confirmed as fraud by reviewer. Notes: {action.notes or 'None'}."
        ),
        context={"alert_id": alert_id, "alert_type": alert.alert_type, "risk_score": alert.risk_score},
        user_id=current_user,
    )
    db.add(audit)
    db.commit()
    
    return {"message": "Alert confirmed as fraud", "alert_id": alert_id}


@router.get("/predictions", response_model=List[PredictiveAlertResponse])
def get_predictive_alerts(db: Session = Depends(get_db)):
    """Get predictive fraud alerts based on vendor patterns (Novel Feature)."""
    alerts = vendor_learner.get_predictive_alerts(db)
    
    return [
        PredictiveAlertResponse(
            vendor_name=a['vendor_name'],
            alert_type=a['alert_type'],
            risk_score=a['risk_score'],
            prediction_confidence=0.8,
            reasoning=a['reasoning'],
            recommended_action="Review recent invoices from this vendor",
            historical_pattern={
                'avg_amount': a['avg_amount'],
                'total_invoices': a['total_invoices']
            },
            current_deviation={
                'fraud_rate': a['historical_fraud_rate']
            }
        )
        for a in alerts
    ]
