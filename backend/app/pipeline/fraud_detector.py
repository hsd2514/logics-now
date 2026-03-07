from typing import Dict, List, Tuple, Optional
import os
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.config import get_settings

settings = get_settings()

class FraudAlert(BaseModel):
    alert_type: str
    risk_score: float
    details: Dict
    reasoning: str

class FraudDetector:
    """Stage 6: Dual anomaly detection - Isolation Forest + Pattern Analysis"""
    
    MODEL_PATH = "isolation_forest.joblib"
    AUTOENCODER_PATH = "autoencoder.joblib"
    
    def __init__(self):
        self.isolation_forest = None
        self.autoencoder = None
        self.autoencoder_scaler = None
        self.autoencoder_err_mean = 0.0
        self.autoencoder_err_std = 1.0
        self.feature_names = ['amount', 'frequency_deviation', 'amount_deviation', 'route_anomaly']
        
        # Attempt to load saved model to persist training across server restarts
        if os.path.exists(self.MODEL_PATH):
            try:
                self.isolation_forest = joblib.load(self.MODEL_PATH)
            except Exception:
                # Log error if loading fails but continue without a pre-trained model
                pass
        if os.path.exists(self.AUTOENCODER_PATH):
            try:
                payload = joblib.load(self.AUTOENCODER_PATH)
                self.autoencoder = payload.get('model')
                self.autoencoder_scaler = payload.get('scaler')
                self.autoencoder_err_mean = float(payload.get('err_mean', 0.0))
                self.autoencoder_err_std = float(payload.get('err_std', 1.0))
            except Exception:
                pass
    
    def detect(
        self, 
        triplet_data: Dict,
        vendor_profile: Optional[Dict] = None,
        historical_triplets: List[Dict] = None,
        contract_rate: Optional[Dict] = None,
    ) -> Tuple[float, List[FraudAlert]]:
        """
        Run fraud detection on a triplet.
        Returns: (overall_risk_score, list_of_alerts)
        """
        alerts = []
        risk_scores = []
        
        # Check 1: Duplicate invoice detection
        dup_alert = self._check_duplicate(triplet_data, historical_triplets)
        if dup_alert:
            alerts.append(dup_alert)
            risk_scores.append(dup_alert.risk_score)
        
        # Check 2: Amount anomaly
        amount_alert = self._check_amount_anomaly(triplet_data, vendor_profile)
        if amount_alert:
            alerts.append(amount_alert)
            risk_scores.append(amount_alert.risk_score)
        
        # Check 3: Frequency anomaly
        freq_alert = self._check_frequency_anomaly(triplet_data, vendor_profile, historical_triplets)
        if freq_alert:
            alerts.append(freq_alert)
            risk_scores.append(freq_alert.risk_score)

        partial_alert = self._check_partial_delivery_overcharge(triplet_data)
        if partial_alert:
            alerts.append(partial_alert)
            risk_scores.append(partial_alert.risk_score)

        contract_alert = self._check_contract_rate_mismatch(triplet_data, contract_rate)
        if contract_alert:
            alerts.append(contract_alert)
            risk_scores.append(contract_alert.risk_score)
        
        # Check 4: Predictive pattern deviation (Novel feature)
        if vendor_profile:
            pred_alert = self._check_predictive_patterns(triplet_data, vendor_profile)
            if pred_alert:
                alerts.append(pred_alert)
                risk_scores.append(pred_alert.risk_score)

        # Check 5: ML Anomaly Detection (Isolation Forest)
        # Auto-train if not trained but enough history exists
        if self.isolation_forest is None and historical_triplets:
            if len(historical_triplets) >= settings.isolation_forest_min_samples:
                self.train_isolation_forest(historical_triplets)
        
        # Score with Isolation Forest if trained
        if self.isolation_forest:
            ml_risk = self.score_with_isolation_forest(triplet_data)
            if ml_risk > settings.isolation_forest_alert_threshold:
                ml_alert = FraudAlert(
                    alert_type="ML_ANOMALY",
                    risk_score=ml_risk,
                    details={'model': 'IsolationForest', 'risk_score_raw': ml_risk},
                    reasoning=f"Machine learning model detected an anomaly with risk score {ml_risk:.2f}."
                )
                alerts.append(ml_alert)
                risk_scores.append(ml_alert.risk_score)

        # Check 6: Autoencoder reconstruction anomaly
        if self.autoencoder is None and historical_triplets:
            if len(historical_triplets) >= settings.autoencoder_min_samples:
                self.train_autoencoder(historical_triplets)
        if self.autoencoder and self.autoencoder_scaler:
            ae_risk = self.score_with_autoencoder(triplet_data)
            if ae_risk > settings.autoencoder_alert_threshold:
                ae_alert = FraudAlert(
                    alert_type="AUTOENCODER_ANOMALY",
                    risk_score=ae_risk,
                    details={'model': 'MLPAutoencoderProxy', 'risk_score_raw': ae_risk},
                    reasoning=f"Autoencoder reconstruction error indicates anomalous behavior (risk {ae_risk:.2f})."
                )
                alerts.append(ae_alert)
                risk_scores.append(ae_alert.risk_score)
        
        # Calculate overall risk
        overall_risk = max(risk_scores) if risk_scores else 0.0
        
        return overall_risk, alerts
    
    def _check_duplicate(self, triplet: Dict, historical: List[Dict]) -> Optional[FraudAlert]:
        """Check for duplicate invoices."""
        if not historical:
            return None
        
        invoice_id = triplet.get('invoice_entities', {}).get('shipment_id', '')
        invoice_amount = triplet.get('invoice_entities', {}).get('amount', 0)
        
        for hist in historical:
            hist_inv_id = hist.get('invoice_entities', {}).get('shipment_id', '')
            hist_amount = hist.get('invoice_entities', {}).get('amount', 0)
            
            # Exact duplicate
            if invoice_id and invoice_id == hist_inv_id:
                return FraudAlert(
                    alert_type="DUPLICATE",
                    risk_score=settings.fraud_duplicate_exact_risk,
                    details={
                        'duplicate_of': hist.get('id'),
                        'invoice_id': invoice_id,
                        'amount': invoice_amount
                    },
                    reasoning=f"Exact duplicate invoice detected. Invoice ID {invoice_id} was already processed in triplet {hist.get('id')}."
                )
            
            # Same amount within short time (potential duplicate)
            if invoice_amount and hist_amount:
                try:
                    if abs(float(invoice_amount) - float(hist_amount)) < 1.0:
                        return FraudAlert(
                            alert_type="DUPLICATE",
                            risk_score=settings.fraud_duplicate_amount_risk,
                            details={
                                'similar_to': hist.get('id'),
                                'amount': invoice_amount,
                                'similarity': 'exact_amount'
                            },
                            reasoning=f"Potential duplicate: Same amount ({invoice_amount}) found in recent invoice."
                        )
                except:
                    pass
        
        return None

    def _check_partial_delivery_overcharge(self, triplet: Dict) -> Optional[FraudAlert]:
        lr = triplet.get("lr_entities", {}) or {}
        pod = triplet.get("pod_entities", {}) or {}
        inv = triplet.get("invoice_entities", {}) or {}

        try:
            lr_weight = float(lr.get("weight", 0) or 0)
            pod_weight = float(pod.get("weight", 0) or 0)
            lr_amount = float(lr.get("amount", 0) or 0)
            inv_amount = float(inv.get("amount", 0) or 0)
        except (TypeError, ValueError):
            return None

        if lr_weight <= 0 or pod_weight <= 0 or lr_amount <= 0 or inv_amount <= 0:
            return None

        ratio = pod_weight / lr_weight
        if ratio >= settings.partial_delivery_min_ratio:
            return None

        variance = abs(inv_amount - lr_amount) / lr_amount
        if variance > settings.partial_delivery_full_charge_tolerance:
            return None

        risk = min(0.95, settings.partial_overcharge_fraud_risk + (settings.partial_delivery_min_ratio - ratio))
        return FraudAlert(
            alert_type="PARTIAL_DELIVERY_OVERCHARGE",
            risk_score=risk,
            details={
                "lr_weight": lr_weight,
                "pod_weight": pod_weight,
                "delivered_ratio": ratio,
                "lr_amount": lr_amount,
                "invoice_amount": inv_amount,
                "amount_variance_percent": variance * 100,
            },
            reasoning=(
                f"POD indicates partial delivery ({ratio * 100:.1f}% of LR weight), "
                "but invoice still charges full LR amount."
            ),
        )

    def _check_contract_rate_mismatch(self, triplet: Dict, contract_rate: Optional[Dict]) -> Optional[FraudAlert]:
        if not contract_rate:
            return None

        inv = triplet.get("invoice_entities", {}) or {}
        try:
            expected_total = (
                float(contract_rate.get("base_rate", 0) or 0)
                + float(contract_rate.get("fuel_surcharge", 0) or 0)
                + float(contract_rate.get("detention_rate", 0) or 0)
                + float(contract_rate.get("distance_rate", 0) or 0)
            )
            inv_amount = float(inv.get("amount", 0) or 0)
        except (TypeError, ValueError):
            return None

        if expected_total <= 0:
            return None

        variance = abs(inv_amount - expected_total) / expected_total
        if variance <= settings.contract_mismatch_fraud_threshold:
            return None

        return FraudAlert(
            alert_type="CONTRACT_RATE_MISMATCH",
            risk_score=min(0.95, settings.contract_mismatch_fraud_risk_base + variance),
            details={
                "invoice_amount": inv_amount,
                "contract_total": expected_total,
                "variance_percent": variance * 100,
                "vendor_name": contract_rate.get("vendor_name"),
                "origin": contract_rate.get("origin"),
                "destination": contract_rate.get("destination"),
            },
            reasoning=(
                f"Invoice amount ({inv_amount:.2f}) deviates from contract total ({expected_total:.2f}) "
                f"by {variance * 100:.1f}%."
            ),
        )
    
    def _check_amount_anomaly(self, triplet: Dict, vendor_profile: Optional[Dict]) -> Optional[FraudAlert]:
        """Check for unusual invoice amounts."""
        invoice_amount = triplet.get('invoice_entities', {}).get('amount', 0)
        lr_amount = triplet.get('lr_entities', {}).get('amount', 0)
        
        try:
            inv_amt = float(invoice_amount) if invoice_amount else 0
            lr_amt = float(lr_amount) if lr_amount else 0
        except:
            return None
        
        # Check against vendor profile
        if vendor_profile:
            # Handle None values from database
            avg = vendor_profile.get('avg_amount') or 0.0
            std = vendor_profile.get('std_deviation') or 0.0
            
            if avg > 0 and std > 0:
                try:
                    z_score = abs(inv_amt - avg) / std
                    
                    if z_score > settings.fraud_vendor_zscore_threshold:
                        return FraudAlert(
                            alert_type="AMOUNT_ANOMALY",
                            risk_score=min(0.5 + z_score * 0.1, settings.fraud_lr_invoice_max_risk),
                            details={
                                'invoice_amount': inv_amt,
                                'vendor_avg': avg,
                                'vendor_std': std,
                                'z_score': z_score
                            },
                            reasoning=f"Invoice amount ({inv_amt}) is {z_score:.1f} standard deviations from vendor average ({avg:.0f}). This is statistically unusual."
                        )
                except (TypeError, ZeroDivisionError):
                    pass
        
        # Check invoice vs LR variance
        if lr_amt > 0:
            variance = abs(inv_amt - lr_amt) / lr_amt
            if variance > settings.fraud_lr_invoice_variance_threshold:
                return FraudAlert(
                    alert_type="AMOUNT_ANOMALY",
                    risk_score=min(settings.fraud_lr_invoice_base_risk + variance, settings.fraud_lr_invoice_max_risk),
                    details={
                        'invoice_amount': inv_amt,
                        'lr_amount': lr_amt,
                        'variance_percent': variance * 100
                    },
                    reasoning=f"Invoice amount ({inv_amt}) differs from LR amount ({lr_amt}) by {variance * 100:.1f}%, exceeding normal tolerance."
                )
        
        return None
    
    def _check_frequency_anomaly(
        self, triplet: Dict, vendor_profile: Optional[Dict], historical: List[Dict]
    ) -> Optional[FraudAlert]:
        """Check for unusual invoice frequency."""
        if not vendor_profile or not historical:
            return None
        
        vendor_name = triplet.get('invoice_entities', {}).get('party_name', '')
        # Handle None values from database
        avg_freq = vendor_profile.get('avg_frequency') or 0.0
        
        if not vendor_name or avg_freq == 0:
            return None
        
        # Count recent invoices from same vendor
        recent_count = 0
        cutoff = datetime.now() - timedelta(days=7)
        
        for hist in historical:
            hist_vendor = hist.get('invoice_entities', {}).get('party_name', '')
            hist_date = hist.get('created_at')
            
            if hist_vendor and hist_vendor.lower() == vendor_name.lower():
                if hist_date and hist_date > cutoff:
                    recent_count += 1
        
        # Expected weekly frequency
        expected_weekly = avg_freq / 4  # Monthly to weekly
        
        if expected_weekly > 0 and recent_count > expected_weekly * settings.fraud_frequency_multiplier:
            return FraudAlert(
                alert_type="VENDOR_ANOMALY",
                risk_score=settings.fraud_frequency_risk,
                details={
                    'vendor': vendor_name,
                    'recent_invoices': recent_count,
                    'expected_weekly': expected_weekly
                },
                reasoning=f"Unusual invoice frequency from {vendor_name}. {recent_count} invoices this week vs expected {expected_weekly:.0f}."
            )
        
        return None
    
    def _check_predictive_patterns(self, triplet: Dict, vendor_profile: Dict) -> Optional[FraudAlert]:
        """Novel: Predictive fraud detection based on learned vendor patterns."""
        alerts_reasons = []
        risk_factors = []
        
        invoice_entities = triplet.get('invoice_entities', {})
        
        # Check route pattern - Only alert if we have a baseline (min 3 invoices)
        origin = invoice_entities.get('origin', '').lower()
        dest = invoice_entities.get('destination', '').lower()
        known_routes = vendor_profile.get('route_patterns', [])
        total_invoices = vendor_profile.get('total_invoices', 0)
        
        if origin and dest and known_routes and total_invoices >= 3:
            route = f"{origin}-{dest}"
            if route not in [r.lower() for r in known_routes]:
                alerts_reasons.append(f"New route {origin}->{dest} not in vendor's usual patterns")
                risk_factors.append(0.5)
        
        # Check for unusually round amounts
        amount = invoice_entities.get('amount', 0)
        try:
            amt = float(amount)
            if amt > settings.fraud_predictive_round_amount_min and amt % settings.fraud_predictive_round_amount_step == 0:
                alerts_reasons.append(f"Suspiciously round amount ({amt})")
                risk_factors.append(0.3)
        except:
            pass
        
        # Check historical fraud rate
        # Handle None values from database
        fraud_rate = vendor_profile.get('historical_fraud_rate') or 0.0
        if fraud_rate > settings.fraud_high_fraud_rate_threshold:
            alerts_reasons.append(f"Vendor has elevated fraud history ({fraud_rate * 100:.1f}%)")
            risk_factors.append(fraud_rate)
        
        if alerts_reasons:
            return FraudAlert(
                alert_type="PREDICTED",
                risk_score=max(risk_factors),
                details={
                    'risk_factors': alerts_reasons,
                    'vendor_fraud_rate': fraud_rate
                },
                reasoning=f"Predictive alert: {'; '.join(alerts_reasons)}"
            )
        
        return None
    
    def train_isolation_forest(self, historical_data: List[Dict]):
        """Train Isolation Forest on historical triplet data."""
        if len(historical_data) < settings.isolation_forest_min_samples:
            return False # Indicate that training did not occur
        
        features = []
        for triplet in historical_data:
            inv = triplet.get('invoice_entities', {})
            feature_vector = [
                float(inv.get('amount', 0)),
                triplet.get('frequency_score', 0),
                triplet.get('amount_deviation', 0),
                triplet.get('route_score', 0)
            ]
            features.append(feature_vector)
        
        X = np.array(features)
        self.isolation_forest = IsolationForest(
            contamination=settings.isolation_forest_contamination,
            random_state=settings.isolation_forest_random_state
        )
        self.isolation_forest.fit(X)
        
        # Persist trained model
        try:
            joblib.dump(self.isolation_forest, self.MODEL_PATH)
        except Exception:
            # Log error if saving fails
            pass
        
        return True

    def train_autoencoder(self, historical_data: List[Dict]) -> bool:
        """Train a compact autoencoder proxy using MLP reconstruction."""
        if len(historical_data) < settings.autoencoder_min_samples:
            return False

        features = []
        for triplet in historical_data:
            inv = triplet.get('invoice_entities', {})
            features.append([
                float(inv.get('amount', 0) or 0),
                float(triplet.get('frequency_score', 0) or 0),
                float(triplet.get('amount_deviation', 0) or 0),
                float(triplet.get('route_score', 0) or 0),
            ])
        X = np.array(features, dtype=np.float32)

        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
        model = MLPRegressor(
            hidden_layer_sizes=(3,),
            activation='tanh',
            random_state=settings.isolation_forest_random_state,
            max_iter=settings.autoencoder_max_iter,
        )
        model.fit(Xs, Xs)

        reconstructed = model.predict(Xs)
        errors = np.mean((Xs - reconstructed) ** 2, axis=1)

        self.autoencoder = model
        self.autoencoder_scaler = scaler
        self.autoencoder_err_mean = float(np.mean(errors))
        self.autoencoder_err_std = float(np.std(errors) + 1e-6)

        try:
            joblib.dump(
                {
                    'model': self.autoencoder,
                    'scaler': self.autoencoder_scaler,
                    'err_mean': self.autoencoder_err_mean,
                    'err_std': self.autoencoder_err_std,
                },
                self.AUTOENCODER_PATH,
            )
        except Exception:
            pass
        return True
    
    def score_with_isolation_forest(self, triplet: Dict) -> float:
        """Score a triplet using trained Isolation Forest."""
        if self.isolation_forest is None:
            return 0.0
        
        inv = triplet.get('invoice_entities', {})
        feature_vector = np.array([[
            float(inv.get('amount', 0)),
            triplet.get('frequency_score', 0),
            triplet.get('amount_deviation', 0),
            triplet.get('route_score', 0)
        ]])
        
        # Isolation Forest returns -1 for anomalies, 1 for normal
        score = self.isolation_forest.decision_function(feature_vector)[0]
        # Convert to 0-1 risk score (lower decision function = higher risk)
        risk = max(0, min(1, 0.5 - score * 0.5))
        return risk

    def score_with_autoencoder(self, triplet: Dict) -> float:
        """Score anomaly risk based on reconstruction error z-score."""
        if self.autoencoder is None or self.autoencoder_scaler is None:
            return 0.0
        inv = triplet.get('invoice_entities', {})
        x = np.array([[
            float(inv.get('amount', 0) or 0),
            float(triplet.get('frequency_score', 0) or 0),
            float(triplet.get('amount_deviation', 0) or 0),
            float(triplet.get('route_score', 0) or 0),
        ]], dtype=np.float32)
        xs = self.autoencoder_scaler.transform(x)
        reconstructed = self.autoencoder.predict(xs)
        err = float(np.mean((xs - reconstructed) ** 2))
        z = (err - self.autoencoder_err_mean) / self.autoencoder_err_std
        # Smooth z-score into [0, 1]
        risk = 1.0 / (1.0 + np.exp(-z))
        return float(max(0.0, min(1.0, risk)))
    
    def alerts_to_dict(self, alerts: List[FraudAlert]) -> List[Dict]:
        """Convert alerts to dictionary for JSON storage."""
        return [
            {
                'alert_type': a.alert_type,
                'risk_score': a.risk_score,
                'details': a.details,
                'reasoning': a.reasoning
            }
            for a in alerts
        ]
