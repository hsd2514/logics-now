from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.fraud_alert import FraudAlert, AlertStatus
from app.schemas.fraud import FraudAlertResponse, FraudAlertListResponse, PredictiveAlertResponse
from app.ai.vendor_patterns import VendorPatternLearner

router = APIRouter()
vendor_learner = VendorPatternLearner()

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

class ActionRequest(BaseModel):
    user_id: Optional[str] = None
    notes: Optional[str] = None

@router.post("/alerts/{alert_id}/dismiss")
def dismiss_alert(
    alert_id: str,
    action: ActionRequest,
    db: Session = Depends(get_db)
):
    """Dismiss a fraud alert."""
    alert = db.query(FraudAlert).filter(FraudAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    from datetime import datetime
    alert.status = AlertStatus.DISMISSED
    alert.resolved_at = datetime.now()
    alert.resolved_by = action.user_id
    alert.resolution_notes = action.notes
    
    db.commit()
    
    return {"message": "Alert dismissed", "alert_id": alert_id}

@router.post("/alerts/{alert_id}/confirm")
def confirm_alert(
    alert_id: str,
    action: ActionRequest,
    db: Session = Depends(get_db)
):
    """Confirm a fraud alert as legitimate fraud."""
    alert = db.query(FraudAlert).filter(FraudAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    from datetime import datetime
    alert.status = AlertStatus.CONFIRMED
    alert.resolved_at = datetime.now()
    alert.resolved_by = action.user_id
    alert.resolution_notes = action.notes
    
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
