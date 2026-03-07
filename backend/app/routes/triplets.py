from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.services.matching_service import MatchingService
from app.schemas.triplet import TripletResponse, TripletListResponse, TripletReview
from app.utils.export_utils import to_csv_bytes, text_to_pdf_bytes

router = APIRouter()
matching_service = MatchingService()

from app.services.websocket_manager import ws_manager

@router.post("/match")
async def run_matching(db: Session = Depends(get_db)):
    """Run matching algorithm on unmatched documents."""
    triplets, events = matching_service.match_documents(db)
    
    # Broadcast all collected events
    for event in events:
        if event['type'] == 'processing_update':
            await ws_manager.send_processing_update(
                event['document_id'],
                event['stage'],
                event['progress'],
                event['message']
            )
        elif event['type'] == 'fraud_alert':
            await ws_manager.send_fraud_alert(
                event['id'], event['risk_score'], event['alert_type']
            )
        elif event['type'] == 'match_found':
            await ws_manager.send_match_found(
                event['id'], event['match_score']
            )
    
    return {
        "message": f"Created {len(triplets)} triplet matches",
        "triplet_ids": [t.id for t in triplets]
    }

@router.get("", response_model=TripletListResponse)
def list_triplets(
    status: Optional[str] = Query(None, description="Filter by triplet status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    vendor_name: Optional[str] = Query(None, description="Filter by vendor/party name (partial match)"),
    amount_min: Optional[float] = Query(None, description="Minimum invoice amount"),
    amount_max: Optional[float] = Query(None, description="Maximum invoice amount"),
    date_from: Optional[str] = Query(None, description="Filter triplets created on or after this date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter triplets created on or before this date (YYYY-MM-DD)"),
    fraud_risk: Optional[str] = Query(None, description="Fraud risk level: LOW | MEDIUM | HIGH"),
    document_type: Optional[str] = Query(None, description="Document type scope for filters: LR | POD | INVOICE"),
    route_origin: Optional[str] = Query(None, description="Filter by origin city (partial match)"),
    route_destination: Optional[str] = Query(None, description="Filter by destination city (partial match)"),
    db: Session = Depends(get_db)
):
    """List triplets. Supports all NL-query filter fields server-side."""
    triplets, stats = matching_service.get_triplets(
        db,
        status=status,
        skip=skip,
        limit=limit,
        vendor_name=vendor_name,
        amount_min=amount_min,
        amount_max=amount_max,
        date_from=date_from,
        date_to=date_to,
        fraud_risk=fraud_risk,
        document_type=document_type,
        route_origin=route_origin,
        route_destination=route_destination,
    )
    
    return TripletListResponse(
        triplets=[TripletResponse.model_validate(t) for t in triplets],
        total=stats['total'],
        pending_review=stats['pending_review'],
        auto_approved=stats['auto_approved'],
        flagged=stats['flagged']
    )


@router.get("/export")
def export_triplets(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db),
):
    triplets, _ = matching_service.get_triplets(db, skip=0, limit=5000)
    rows = []
    for t in triplets:
        rows.append(
            {
                "id": t.id,
                "status": t.status,
                "confidence": round(float(t.confidence or 0), 4),
                "match_score": round(float(t.match_score or 0), 4),
                "lr_id": t.lr_id,
                "pod_id": t.pod_id,
                "invoice_id": t.invoice_id,
                "created_at": t.created_at.isoformat() if t.created_at else "",
            }
        )

    if format == "csv":
        content = to_csv_bytes(
            rows,
            fieldnames=["id", "status", "confidence", "match_score", "lr_id", "pod_id", "invoice_id", "created_at"],
        )
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="triplets_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'},
        )

    lines = [f"{r['id']} | {r['status']} | conf={r['confidence']} | score={r['match_score']}" for r in rows]
    pdf = text_to_pdf_bytes("FreightIQ Triplets Export", lines)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="triplets_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'},
    )


@router.get("/{triplet_id}/audit-export")
def export_triplet_audit(
    triplet_id: str,
    format: str = Query("pdf", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db),
):
    t = matching_service.get_triplet(db, triplet_id)
    if not t:
        raise HTTPException(status_code=404, detail="Triplet not found")

    details = t.validation_details or []
    explanation = t.ai_explanation or "No AI explanation available."

    row = {
        "triplet_id": t.id,
        "status": t.status,
        "confidence": round(float(t.confidence or 0), 4),
        "match_score": round(float(t.match_score or 0), 4),
        "rule_pass_score": round(float(t.rule_pass_score or 0), 4),
        "created_at": t.created_at.isoformat() if t.created_at else "",
        "ai_explanation": explanation,
    }

    if format == "csv":
        content = to_csv_bytes([row], fieldnames=list(row.keys()))
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="triplet_audit_{triplet_id[:8]}.csv"'},
        )

    lines = [
        f"Triplet: {t.id}",
        f"Status: {t.status}",
        f"Confidence: {row['confidence']}",
        f"Match score: {row['match_score']}",
        f"Rule pass score: {row['rule_pass_score']}",
        "Validation details:",
    ]
    for d in details[:20]:
        lines.append(f"- {d.get('rule')}: {'PASS' if d.get('passed') else 'FAIL'} ({d.get('message', '')})")
    lines.append("AI explanation:")
    lines.extend((explanation or "").splitlines()[:20])

    pdf = text_to_pdf_bytes("FreightIQ Triplet Audit Report", lines)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="triplet_audit_{triplet_id[:8]}.pdf"'},
    )


@router.get("/{triplet_id}", response_model=TripletResponse)
def get_triplet(triplet_id: str, db: Session = Depends(get_db)):
    """Get a specific triplet with full details."""
    triplet = matching_service.get_triplet(db, triplet_id)
    if not triplet:
        raise HTTPException(status_code=404, detail="Triplet not found")
    
    return TripletResponse.model_validate(triplet)

@router.post("/{triplet_id}/approve", response_model=TripletResponse)
def approve_triplet(
    triplet_id: str,
    review: TripletReview,
    db: Session = Depends(get_db)
):
    """Approve a triplet match."""
    triplet = matching_service.approve_triplet(
        db, triplet_id, review.reviewed_by, review.notes
    )
    if not triplet:
        raise HTTPException(status_code=404, detail="Triplet not found")
    
    return TripletResponse.model_validate(triplet)

@router.post("/{triplet_id}/reject", response_model=TripletResponse)
def reject_triplet(
    triplet_id: str,
    review: TripletReview,
    db: Session = Depends(get_db)
):
    """Reject a triplet match."""
    triplet = matching_service.reject_triplet(
        db, triplet_id, review.reviewed_by, review.notes
    )
    if not triplet:
        raise HTTPException(status_code=404, detail="Triplet not found")
    
    return TripletResponse.model_validate(triplet)
