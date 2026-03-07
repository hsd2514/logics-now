from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.triplet import Triplet, TripletStatus
from app.models.fraud_alert import FraudAlert, AlertStatus

router = APIRouter()


def _extract_total_ms(doc: Document) -> float:
    timing = doc.processing_time_ms or {}
    if not isinstance(timing, dict):
        return 0.0
    value = timing.get("total")
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0

@router.get("")
def get_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics."""
    # Document stats
    total_documents = db.query(Document).count()
    documents_by_type = {
        'LR': db.query(Document).filter(Document.type == 'LR').count(),
        'POD': db.query(Document).filter(Document.type == 'POD').count(),
        'INVOICE': db.query(Document).filter(Document.type == 'INVOICE').count()
    }
    documents_by_status = {
        'PENDING': db.query(Document).filter(Document.status == DocumentStatus.PENDING).count(),
        'PROCESSED': db.query(Document).filter(Document.status == DocumentStatus.PROCESSED).count(),
        'MATCHED': db.query(Document).filter(Document.status == DocumentStatus.MATCHED).count(),
        'ERROR': db.query(Document).filter(Document.status == DocumentStatus.ERROR).count()
    }
    
    # Triplet stats
    total_triplets = db.query(Triplet).count()
    triplets_by_status = {
        'PENDING': db.query(Triplet).filter(Triplet.status == TripletStatus.PENDING).count(),
        'AUTO_APPROVED': db.query(Triplet).filter(Triplet.status == TripletStatus.AUTO_APPROVED).count(),
        'APPROVED': db.query(Triplet).filter(Triplet.status == TripletStatus.APPROVED).count(),
        'REJECTED': db.query(Triplet).filter(Triplet.status == TripletStatus.REJECTED).count(),
        'REVIEW': db.query(Triplet).filter(Triplet.status == TripletStatus.REVIEW).count()
    }
    
    # Average confidence
    avg_confidence = db.query(func.avg(Triplet.confidence)).scalar() or 0
    avg_match_score = db.query(func.avg(Triplet.match_score)).scalar() or 0
    
    # Fraud stats
    total_alerts = db.query(FraudAlert).count()
    open_alerts = db.query(FraudAlert).filter(FraudAlert.status == AlertStatus.OPEN).count()
    high_risk_alerts = db.query(FraudAlert).filter(FraudAlert.risk_score > 0.7).count()
    confirmed_fraud = db.query(FraudAlert).filter(FraudAlert.status == AlertStatus.CONFIRMED).count()
    
    # Calculate efficiency metrics
    auto_approved_count = triplets_by_status['AUTO_APPROVED']
    total_approved = auto_approved_count + triplets_by_status['APPROVED']
    automation_rate = (auto_approved_count / total_approved * 100) if total_approved > 0 else 0

    processed_docs = db.query(Document).filter(Document.status.in_([DocumentStatus.PROCESSED, DocumentStatus.MATCHED])).all()
    total_times = [_extract_total_ms(d) for d in processed_docs if _extract_total_ms(d) > 0]
    avg_processing_time_ms = (sum(total_times) / len(total_times)) if total_times else 0.0

    def _avg_for_type(doc_type: str) -> float:
        docs = [d for d in processed_docs if d.type == doc_type]
        vals = [_extract_total_ms(d) for d in docs if _extract_total_ms(d) > 0]
        return round(sum(vals) / len(vals), 2) if vals else 0.0
    
    return {
        "documents": {
            "total": total_documents,
            "by_type": documents_by_type,
            "by_status": documents_by_status
        },
        "triplets": {
            "total": total_triplets,
            "by_status": triplets_by_status,
            "avg_confidence": round(avg_confidence * 100, 1),
            "avg_match_score": round(avg_match_score * 100, 1),
            "automation_rate": round(automation_rate, 1)
        },
        "fraud": {
            "total_alerts": total_alerts,
            "open_alerts": open_alerts,
            "high_risk": high_risk_alerts,
            "confirmed": confirmed_fraud
        },
        "efficiency": {
            "manual_effort_reduction": round(automation_rate, 1),
            "pending_review": triplets_by_status['REVIEW'],
            "avg_processing_time_ms": round(avg_processing_time_ms, 2),
            "avg_processing_time_by_type_ms": {
                "LR": _avg_for_type("LR"),
                "POD": _avg_for_type("POD"),
                "INVOICE": _avg_for_type("INVOICE"),
            }
        }
    }
