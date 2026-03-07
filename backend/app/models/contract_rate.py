from sqlalchemy import Boolean, Column, DateTime, Float, String
from sqlalchemy.sql import func
import uuid

from app.database import Base


class ContractRate(Base):
    __tablename__ = "contract_rates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_name = Column(String, nullable=False, index=True)
    origin = Column(String, nullable=True, index=True)
    destination = Column(String, nullable=True, index=True)
    base_rate = Column(Float, nullable=False, default=0.0)
    fuel_surcharge = Column(Float, nullable=False, default=0.0)
    detention_rate = Column(Float, nullable=False, default=0.0)
    distance_rate = Column(Float, nullable=False, default=0.0)
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
