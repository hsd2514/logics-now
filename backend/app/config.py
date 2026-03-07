from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    app_name: str = "FreightIQ"
    debug: bool = True
    database_url: str = "sqlite:///./freightiq.db"
    upload_dir: str = "./uploads"
    google_api_key: str = ""
    
    # Matching thresholds (tunable via env)
    amount_tolerance: float = 0.02  # 2% LR vs Invoice variance
    confidence_threshold: float = 0.85  # below this => low confidence
    auto_approve_threshold: float = 0.90  # above this => auto-approve
    min_match_score: float = 0.5  # minimum raw match score to consider a triplet
    
    # Missing settings for TripletMatcher
    date_valid_score: float = 1.0
    date_invalid_score: float = 0.2

    # Confidence aggregation weights
    match_weight: float = 0.35
    ocr_weight: float = 0.20
    ner_weight: float = 0.25
    rule_weight: float = 0.20
    confidence_base: float = 0.5   # base confidence offset
    confidence_range: float = 0.5  # max additional confidence from fields

    # Validator thresholds
    name_similarity_threshold: float = 0.85  # min party-name similarity

    # Fraud detection thresholds
    fraud_duplicate_exact_risk: float = 0.95
    fraud_duplicate_amount_risk: float = 0.75
    fraud_vendor_zscore_threshold: float = 3.0
    fraud_lr_invoice_variance_threshold: float = 0.10  # 10%
    fraud_lr_invoice_base_risk: float = 0.4
    fraud_lr_invoice_max_risk: float = 0.9
    fraud_frequency_multiplier: float = 2.0  # recent_count > expected_weekly * multiplier
    fraud_frequency_risk: float = 0.7
    fraud_high_fraud_rate_threshold: float = 0.05  # 5% for predictive checks
    fraud_predictive_new_route_risk: float = 0.5
    fraud_predictive_round_amount_min: float = 1000.0
    fraud_predictive_round_amount_step: float = 1000.0
    isolation_forest_contamination: float = 0.10
    isolation_forest_min_samples: int = 10
    isolation_forest_random_state: int = 42
    isolation_forest_alert_threshold: float = 0.6  # Risk score threshold for ML alerts
    fraud_high_risk_alert_threshold: float = 0.7  # risk_score above this → force REVIEW + counted as flagged
    contract_rate_tolerance: float = 0.05
    contract_mismatch_fraud_threshold: float = 0.12
    contract_mismatch_fraud_risk_base: float = 0.65
    contract_fuel_surcharge_max_pct: float = 0.20
    contract_max_detention_charge: float = 5000.0
    partial_delivery_min_ratio: float = 0.95
    partial_delivery_full_charge_tolerance: float = 0.05
    partial_overcharge_fraud_risk: float = 0.85

    # AI / LLM
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "models/text-embedding-004"
    chat_context_chars: int = 3000

    # Vendor risk thresholds
    vendor_min_invoices_for_risk: int = 5
    vendor_high_risk_cutoff: float = 0.3
    vendor_high_fraud_rate_for_reason: float = 0.10
    vendor_high_cv_threshold: float = 0.5
    vendor_high_frequency_threshold: float = 20.0  # invoices/month
    
    model_config = {"env_file": ".env", "extra": "ignore"}

@lru_cache
def get_settings():
    return Settings()
