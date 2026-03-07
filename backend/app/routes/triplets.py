from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.matching_service import MatchingService
from app.schemas.triplet import TripletResponse, TripletListResponse, TripletReview

router = APIRouter()
matching_service = MatchingService()

@router.post("/match")
def run_matching(db: Session = Depends(get_db)):
    """Run matching algorithm on unmatched documents."""
    triplets = matching_service.match_documents(db)
    
    return {
        "message": f"Created {len(triplets)} triplet matches",
        "triplet_ids": [t.id for t in triplets]
    }

@router.get("", response_model=TripletListResponse)
def list_triplets(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all triplets with optional status filter."""
    triplets, stats = matching_service.get_triplets(db, status, skip, limit)
    
    return TripletListResponse(
        triplets=[TripletResponse.model_validate(t) for t in triplets],
        total=stats['total'],
        pending_review=stats['pending_review'],
        auto_approved=stats['auto_approved'],
        flagged=stats['flagged']
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
