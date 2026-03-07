from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.vendor_service import VendorService

router = APIRouter()
vendor_service = VendorService()


@router.get("/analytics")
def get_vendor_analytics(db: Session = Depends(get_db)):
    """Get aggregate vendor analytics."""
    analytics = vendor_service.get_vendor_analytics(db)
    return analytics


@router.get("/profiles")
def list_vendor_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query('risk_score', pattern='^(risk_score|total_invoices|avg_amount|vendor_name)$'),
    db: Session = Depends(get_db)
):
    """List all vendor profiles with pagination and sorting."""
    profiles, total = vendor_service.get_all_profiles(db, skip, limit, sort_by)
    
    return {
        'profiles': [
            {
                'vendor_name': p.vendor_name,
                'risk_score': p.risk_score,
                'total_invoices': p.total_invoices,
                'avg_amount': p.avg_amount,
                'std_deviation': p.std_deviation,
                'min_amount': p.min_amount,
                'max_amount': p.max_amount,
                'avg_frequency': p.avg_frequency,
                'historical_fraud_rate': p.historical_fraud_rate,
                'route_patterns': p.route_patterns,
                'first_seen': p.first_seen.isoformat() if p.first_seen else None,
                'last_invoice_date': p.last_invoice_date.isoformat() if p.last_invoice_date else None
            }
            for p in profiles
        ],
        'total': total,
        'skip': skip,
        'limit': limit
    }


@router.get("/{vendor_name}")
def get_vendor_details(vendor_name: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific vendor."""
    details = vendor_service.get_vendor_details(db, vendor_name)
    
    if not details:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    return details


@router.post("/refresh")
def refresh_all_profiles(db: Session = Depends(get_db)):
    """Refresh all vendor profiles with latest data."""
    from app.models.document import Document
    
    # Get all invoices
    invoices = db.query(Document).filter(Document.type == "INVOICE").all()
    
    updated_count = 0
    for invoice in invoices:
        if invoice.entities and invoice.entities.get('party_name'):
            vendor_name = invoice.entities.get('party_name')
            amount = invoice.entities.get('amount', 0)
            route = f"{invoice.entities.get('origin', '')}-{invoice.entities.get('destination', '')}"
            
            # Parse date
            date_str = invoice.entities.get('date')
            try:
                from datetime import datetime
                invoice_date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else invoice.upload_date
            except:
                invoice_date = invoice.upload_date
            
            vendor_service.update_vendor_profile(
                db, vendor_name, float(amount) if amount else 0.0, route, invoice_date
            )
            updated_count += 1
    
    return {"message": f"Refreshed {updated_count} vendor profiles"}
