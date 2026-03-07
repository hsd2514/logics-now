"""Unit tests for FraudDetector."""
import pytest
from app.pipeline.fraud_detector import FraudDetector, FraudAlert


class TestFraudDetector:
    def setup_method(self):
        self.detector = FraudDetector()

    # ── Duplicate detection ───────────────────────────────────────────────────

    def test_exact_duplicate_triggers_alert(self):
        triplet = {
            "invoice_entities": {"shipment_id": "INV001", "amount": 50000},
        }
        historical = [
            {"id": "prev-1", "invoice_entities": {"shipment_id": "INV001", "amount": 50000}},
        ]
        risk, alerts = self.detector.detect(triplet, historical_triplets=historical)
        dup_alerts = [a for a in alerts if a.alert_type == "DUPLICATE"]
        assert len(dup_alerts) >= 1
        assert dup_alerts[0].risk_score >= 0.9

    def test_same_amount_near_duplicate_alert(self):
        triplet = {
            "invoice_entities": {"shipment_id": "INV002", "amount": 50000.0},
        }
        historical = [
            {"id": "prev-2", "invoice_entities": {"shipment_id": "INV999", "amount": 50000.0}},
        ]
        risk, alerts = self.detector.detect(triplet, historical_triplets=historical)
        dup_alerts = [a for a in alerts if a.alert_type == "DUPLICATE"]
        # same amount different id → potential duplicate
        assert len(dup_alerts) >= 1

    def test_no_duplicate_when_no_history(self):
        triplet = {"invoice_entities": {"shipment_id": "INV003", "amount": 50000}}
        risk, alerts = self.detector.detect(triplet, historical_triplets=[])
        dup_alerts = [a for a in alerts if a.alert_type == "DUPLICATE"]
        assert len(dup_alerts) == 0

    def test_no_duplicate_with_unique_id_and_amount(self):
        triplet = {"invoice_entities": {"shipment_id": "INV004", "amount": 99999.0}}
        historical = [{"id": "h1", "invoice_entities": {"shipment_id": "INV005", "amount": 12345.0}}]
        risk, alerts = self.detector.detect(triplet, historical_triplets=historical)
        dup_alerts = [a for a in alerts if a.alert_type == "DUPLICATE"]
        assert len(dup_alerts) == 0

    # ── Amount anomaly ────────────────────────────────────────────────────────

    def test_amount_anomaly_triggered_for_high_z_score(self):
        vendor_profile = {
            "avg_amount": 50000.0,
            "std_deviation": 1000.0,       # tight distribution
            "total_invoices": 20,
        }
        triplet = {
            "invoice_entities": {"shipment_id": "INV010", "amount": 200000.0},  # 150σ deviation
            "lr_entities": {"amount": 200000.0},
        }
        risk, alerts = self.detector.detect(triplet, vendor_profile=vendor_profile)
        amount_alerts = [a for a in alerts if a.alert_type == "AMOUNT_ANOMALY"]
        assert len(amount_alerts) >= 1

    def test_no_amount_anomaly_within_normal_range(self):
        vendor_profile = {
            "avg_amount": 50000.0,
            "std_deviation": 5000.0,
            "total_invoices": 20,
        }
        triplet = {
            "invoice_entities": {"shipment_id": "INV011", "amount": 52000.0},
            "lr_entities": {"amount": 52000.0},
        }
        risk, alerts = self.detector.detect(triplet, vendor_profile=vendor_profile)
        amount_alerts = [a for a in alerts if a.alert_type == "AMOUNT_ANOMALY"]
        assert len(amount_alerts) == 0

    # ── Overall risk score ────────────────────────────────────────────────────

    def test_clean_triplet_has_zero_risk(self):
        triplet = {"invoice_entities": {"shipment_id": "CLEAN01", "amount": 10000.0}}
        risk, alerts = self.detector.detect(triplet)
        assert risk == 0.0
        assert alerts == []

    def test_overall_risk_is_max_of_alert_scores(self):
        triplet = {
            "invoice_entities": {"shipment_id": "DUP01", "amount": 50000.0},
        }
        historical = [
            {"id": "prev-x", "invoice_entities": {"shipment_id": "DUP01", "amount": 50000.0}},
        ]
        vendor_profile = {
            "avg_amount": 50000.0,
            "std_deviation": 1.0,     # extreme deviation
            "total_invoices": 20,
        }
        risk, alerts = self.detector.detect(triplet, vendor_profile=vendor_profile, historical_triplets=historical)
        expected_max = max(a.risk_score for a in alerts)
        assert risk == pytest.approx(expected_max)

    def test_risk_score_between_0_and_1(self):
        triplet = {"invoice_entities": {"shipment_id": "RISK01", "amount": 999999}}
        historical = [{"id": "h1", "invoice_entities": {"shipment_id": "RISK01", "amount": 999999}}]
        risk, _ = self.detector.detect(triplet, historical_triplets=historical)
        assert 0.0 <= risk <= 1.0

    # ── FraudAlert dataclass ──────────────────────────────────────────────────

    def test_fraud_alert_has_required_fields(self):
        triplet = {"invoice_entities": {"shipment_id": "FA01", "amount": 50000}}
        historical = [{"id": "prev-fa", "invoice_entities": {"shipment_id": "FA01", "amount": 50000}}]
        _, alerts = self.detector.detect(triplet, historical_triplets=historical)
        for alert in alerts:
            assert hasattr(alert, 'alert_type')
            assert hasattr(alert, 'risk_score')
            assert hasattr(alert, 'details')
            assert hasattr(alert, 'reasoning')
            assert isinstance(alert.details, dict)
