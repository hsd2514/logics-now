from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class FraudAlertDetail(BaseModel):
    field: str
    expected_range: Optional[str] = None
    actual_value: str
    deviation: Optional[float] = None
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL

class FraudAlertResponse(BaseModel):
    id: str
    triplet_id: str
    risk_score: float
    alert_type: str
    # Stored as a JSON dict by the detector; allow any shape here
    details: Dict[str, Any]
    ai_reasoning: Optional[str] = None
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class FraudAlertListResponse(BaseModel):
    alerts: List[FraudAlertResponse]
    total: int
    open_count: int
    high_risk_count: int

class PredictiveAlertResponse(BaseModel):
    """Novel: Predictive fraud alert based on vendor patterns"""
    vendor_name: str
    alert_type: str
    risk_score: float
    prediction_confidence: float
    reasoning: str
    recommended_action: str
    historical_pattern: Dict[str, Any]
    current_deviation: Dict[str, Any]

class VendorRiskProfile(BaseModel):
    vendor_name: str
    risk_score: float
    avg_amount: float
    std_deviation: float
    total_invoices: int
    fraud_rate: float
    last_invoice_date: Optional[datetime] = None
    risk_factors: List[str]
