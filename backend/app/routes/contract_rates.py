from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.contract_rate import ContractRate

router = APIRouter()


class ContractRateCreate(BaseModel):
    vendor_name: str = Field(min_length=1)
    origin: Optional[str] = None
    destination: Optional[str] = None
    base_rate: float = 0.0
    fuel_surcharge: float = 0.0
    detention_rate: float = 0.0
    distance_rate: float = 0.0
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    is_active: bool = True


class ContractRateUpdate(BaseModel):
    vendor_name: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    base_rate: Optional[float] = None
    fuel_surcharge: Optional[float] = None
    detention_rate: Optional[float] = None
    distance_rate: Optional[float] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    is_active: Optional[bool] = None


class ContractRateResponse(BaseModel):
    id: str
    vendor_name: str
    origin: Optional[str]
    destination: Optional[str]
    base_rate: float
    fuel_surcharge: float
    detention_rate: float
    distance_rate: float
    effective_from: Optional[datetime]
    effective_to: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.post("", response_model=ContractRateResponse)
def create_contract_rate(payload: ContractRateCreate, db: Session = Depends(get_db)):
    rate = ContractRate(**payload.model_dump())
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


@router.get("", response_model=list[ContractRateResponse])
def list_contract_rates(
    vendor_name: Optional[str] = Query(None),
    origin: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    query = db.query(ContractRate)
    if vendor_name:
        query = query.filter(ContractRate.vendor_name == vendor_name)
    if origin:
        query = query.filter(ContractRate.origin == origin)
    if destination:
        query = query.filter(ContractRate.destination == destination)
    if active_only:
        query = query.filter(ContractRate.is_active.is_(True))
    return query.order_by(ContractRate.created_at.desc()).all()


@router.get("/{rate_id}", response_model=ContractRateResponse)
def get_contract_rate(rate_id: str, db: Session = Depends(get_db)):
    rate = db.query(ContractRate).filter(ContractRate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Contract rate not found")
    return rate


@router.put("/{rate_id}", response_model=ContractRateResponse)
def update_contract_rate(rate_id: str, payload: ContractRateUpdate, db: Session = Depends(get_db)):
    rate = db.query(ContractRate).filter(ContractRate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Contract rate not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(rate, key, value)

    db.commit()
    db.refresh(rate)
    return rate


@router.delete("/{rate_id}")
def delete_contract_rate(rate_id: str, db: Session = Depends(get_db)):
    rate = db.query(ContractRate).filter(ContractRate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Contract rate not found")
    db.delete(rate)
    db.commit()
    return {"message": "Contract rate deleted", "id": rate_id}
