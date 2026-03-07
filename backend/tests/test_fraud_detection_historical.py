"""
Tests for GitHub Issue #6 — Populate historical triplet entities before fraud detection.

Verifies that _triplet_to_dict correctly reads real entity data from historical
triplets so that duplicate-invoice and vendor-frequency fraud checks work.

Uses an in-memory SQLite database with real ORM models (no mocking) to prove
the full data chain: DB → Triplet.invoice relationship → FraudDetector inputs.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.document import Document, DocumentStatus
from app.models.triplet import Triplet, TripletStatus
from app.models.fraud_alert import FraudAlert
from app.models.vendor_profile import VendorProfile
from app.pipeline.fraud_detector import FraudDetector
from app.services.matching_service import MatchingService


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db():
    """Fresh in-memory SQLite session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def _make_document(doc_type: str, entities: dict, doc_id: str = None) -> Document:
    """Helper: create a persisted Document with the given entities."""
    import uuid
    return Document(
        id=doc_id or str(uuid.uuid4()),
        type=doc_type,
        file_name=f"{doc_type.lower()}_test.pdf",
        file_path=f"/tmp/{doc_type.lower()}_test.pdf",
        status=DocumentStatus.MATCHED,
        entities=entities,
        ocr_confidence=0.95,
    )


def _make_triplet(lr: Document, pod: Document, invoice: Document) -> Triplet:
    """Helper: create a Triplet linking three documents."""
    import uuid
    return Triplet(
        id=str(uuid.uuid4()),
        lr_id=lr.id,
        pod_id=pod.id,
        invoice_id=invoice.id,
        match_score=0.95,
        confidence=0.90,
        status=TripletStatus.AUTO_APPROVED,
        created_at=datetime.now() - timedelta(days=1),
    )


# ─── Tests for _triplet_to_dict ───────────────────────────────────────────────

class TestTripletToDict:
    """Unit tests for MatchingService._triplet_to_dict (the fixed method)."""

    def test_invoice_entities_are_populated(self, db):
        """
        Regression test for Issue #6.
        Before the fix, invoice_entities was always {}.
        After the fix it must contain real entity data from the linked document.
        """
        inv = _make_document("INVOICE", {"shipment_id": "SHP-001", "amount": "5000", "party_name": "ACME Corp"})
        lr  = _make_document("LR",      {"shipment_id": "SHP-001", "amount": "5000"})
        pod = _make_document("POD",     {"shipment_id": "SHP-001"})
        db.add_all([lr, pod, inv])
        db.flush()

        triplet = _make_triplet(lr, pod, inv)
        db.add(triplet)
        db.commit()

        # Reload via query so SQLAlchemy builds its identity map cleanly
        t = db.query(Triplet).filter_by(id=triplet.id).first()

        service = MatchingService()
        result = service._triplet_to_dict(t)

        assert result["invoice_entities"] != {}, "invoice_entities must not be empty (Issue #6 regression)"
        assert result["invoice_entities"]["shipment_id"] == "SHP-001"
        assert result["invoice_entities"]["party_name"] == "ACME Corp"

    def test_lr_entities_are_populated(self, db):
        """lr_entities must also reflect the linked LR document's entities."""
        inv = _make_document("INVOICE", {"shipment_id": "SHP-002", "amount": "3000"})
        lr  = _make_document("LR",      {"shipment_id": "SHP-002", "amount": "3000", "origin": "Mumbai"})
        pod = _make_document("POD",     {"shipment_id": "SHP-002"})
        db.add_all([lr, pod, inv])
        db.flush()

        triplet = _make_triplet(lr, pod, inv)
        db.add(triplet)
        db.commit()

        t = db.query(Triplet).filter_by(id=triplet.id).first()
        result = MatchingService()._triplet_to_dict(t)

        assert result["lr_entities"]["origin"] == "Mumbai"

    def test_id_and_created_at_are_preserved(self, db):
        """The dict must always carry id and created_at regardless of entities."""
        inv = _make_document("INVOICE", {})
        lr  = _make_document("LR",      {})
        pod = _make_document("POD",     {})
        db.add_all([lr, pod, inv])
        db.flush()

        triplet = _make_triplet(lr, pod, inv)
        db.add(triplet)
        db.commit()

        t = db.query(Triplet).filter_by(id=triplet.id).first()
        result = MatchingService()._triplet_to_dict(t)

        assert result["id"] == triplet.id
        assert result["created_at"] is not None


# ─── Integration tests: fraud checks using historical triplets ─────────────────

class TestDuplicateInvoiceDetection:
    """
    FraudDetector must detect duplicate invoices when historical triplets
    carry real invoice_entities (i.e. after the Issue #6 fix).
    """

    def test_exact_duplicate_shipment_id_is_flagged(self, db):
        """
        If a previous triplet's invoice has the same shipment_id,
        the DUPLICATE alert must fire.
        """
        # Historical triplet with shipment SHP-100
        hist_inv = _make_document("INVOICE", {"shipment_id": "SHP-100", "amount": "7500", "party_name": "FastFreight"})
        hist_lr  = _make_document("LR",      {"shipment_id": "SHP-100", "amount": "7500"})
        hist_pod = _make_document("POD",     {"shipment_id": "SHP-100"})
        db.add_all([hist_lr, hist_pod, hist_inv])
        db.flush()

        hist_triplet = _make_triplet(hist_lr, hist_pod, hist_inv)
        db.add(hist_triplet)
        db.commit()

        # New triplet — same shipment_id (duplicate)
        new_triplet_data = {
            "invoice_entities": {"shipment_id": "SHP-100", "amount": "7500", "party_name": "FastFreight"},
            "lr_entities": {"shipment_id": "SHP-100", "amount": "7500"},
            "pod_entities": {"shipment_id": "SHP-100"},
        }

        # Build historical context the way MatchingService now does
        service = MatchingService()
        historical_triplets = db.query(Triplet).all()
        historical_dicts = [service._triplet_to_dict(t) for t in historical_triplets]

        detector = FraudDetector()
        risk_score, alerts = detector.detect(new_triplet_data, vendor_profile=None, historical_triplets=historical_dicts)

        alert_types = [a.alert_type for a in alerts]
        assert "DUPLICATE" in alert_types, (
            "Exact duplicate shipment_id should trigger DUPLICATE alert. "
            "This would have been missed before Issue #6 was fixed."
        )

    def test_no_false_positive_for_different_shipment_ids(self, db):
        """Two invoices with different shipment IDs must not trigger a duplicate."""
        hist_inv = _make_document("INVOICE", {"shipment_id": "SHP-200", "amount": "5000"})
        hist_lr  = _make_document("LR",      {"shipment_id": "SHP-200", "amount": "5000"})
        hist_pod = _make_document("POD",     {"shipment_id": "SHP-200"})
        db.add_all([hist_lr, hist_pod, hist_inv])
        db.flush()

        hist_triplet = _make_triplet(hist_lr, hist_pod, hist_inv)
        db.add(hist_triplet)
        db.commit()

        new_triplet_data = {
            "invoice_entities": {"shipment_id": "SHP-999", "amount": "6000"},
            "lr_entities": {},
            "pod_entities": {},
        }

        service = MatchingService()
        historical_dicts = [service._triplet_to_dict(t) for t in db.query(Triplet).all()]

        detector = FraudDetector()
        _, alerts = detector.detect(new_triplet_data, vendor_profile=None, historical_triplets=historical_dicts)

        dup_alerts = [a for a in alerts if a.alert_type == "DUPLICATE"]
        assert len(dup_alerts) == 0, "Different shipment IDs should not produce a DUPLICATE alert"


class TestVendorFrequencyAnomaly:
    """
    FraudDetector must count prior invoices per vendor using populated
    invoice_entities (i.e. after the Issue #6 fix). Without the fix,
    vendor name was always '' and the frequency counter stayed at 0.
    """

    def _make_vendor_profile(self, vendor_name: str, avg_frequency: float = 2.0) -> dict:
        return {
            "vendor_name": vendor_name,
            "avg_frequency": avg_frequency,    # Expected monthly invoices
            "avg_amount": 5000.0,
            "std_deviation": 500.0,
            "historical_fraud_rate": 0.0,
            "route_patterns": [],
            "total_invoices": 10,
        }

    def test_frequency_spike_is_flagged(self, db):
        """
        If 8 invoices from the same vendor appear within a week
        (vs expected ~2/month = 0.5/week), a VENDOR_ANOMALY alert must fire.
        """
        vendor = "SpeedyLogistics"

        # Create 8 recent historical triplets for this vendor
        for i in range(8):
            inv = _make_document("INVOICE", {"shipment_id": f"SHP-F{i}", "party_name": vendor, "amount": "5000"})
            lr  = _make_document("LR",      {"shipment_id": f"SHP-F{i}", "amount": "5000"})
            pod = _make_document("POD",     {"shipment_id": f"SHP-F{i}"})
            db.add_all([lr, pod, inv])
            db.flush()

            t = Triplet(
                lr_id=lr.id, pod_id=pod.id, invoice_id=inv.id,
                match_score=0.9, confidence=0.88,
                status=TripletStatus.AUTO_APPROVED,
                # All within last 3 days — very recent
                created_at=datetime.now() - timedelta(days=i % 3),
            )
            db.add(t)

        db.commit()

        new_triplet_data = {
            "invoice_entities": {"shipment_id": "SHP-NEW", "party_name": vendor, "amount": "5000"},
            "lr_entities": {"amount": "5000"},
            "pod_entities": {},
        }

        vendor_profile = self._make_vendor_profile(vendor, avg_frequency=2.0)

        service = MatchingService()
        historical_dicts = [service._triplet_to_dict(t) for t in db.query(Triplet).all()]

        detector = FraudDetector()
        _, alerts = detector.detect(new_triplet_data, vendor_profile=vendor_profile, historical_triplets=historical_dicts)

        alert_types = [a.alert_type for a in alerts]
        assert "VENDOR_ANOMALY" in alert_types, (
            "8 invoices from the same vendor in one week should trigger VENDOR_ANOMALY. "
            "This would have been missed before Issue #6 was fixed because party_name was always ''."
        )

    def test_normal_frequency_does_not_flag(self, db):
        """A vendor submitting 1 invoice this week (normal pace) must not be flagged."""
        vendor = "SlowButSteady"

        inv = _make_document("INVOICE", {"shipment_id": "SHP-S1", "party_name": vendor, "amount": "4000"})
        lr  = _make_document("LR",      {"shipment_id": "SHP-S1", "amount": "4000"})
        pod = _make_document("POD",     {"shipment_id": "SHP-S1"})
        db.add_all([lr, pod, inv])
        db.flush()

        t = _make_triplet(lr, pod, inv)
        db.add(t)
        db.commit()

        new_triplet_data = {
            "invoice_entities": {"shipment_id": "SHP-S2", "party_name": vendor, "amount": "4000"},
            "lr_entities": {"amount": "4000"},
            "pod_entities": {},
        }

        vendor_profile = self._make_vendor_profile(vendor, avg_frequency=8.0)  # 8/month = 2/week

        service = MatchingService()
        historical_dicts = [service._triplet_to_dict(t) for t in db.query(Triplet).all()]

        detector = FraudDetector()
        _, alerts = detector.detect(new_triplet_data, vendor_profile=vendor_profile, historical_triplets=historical_dicts)

        freq_alerts = [a for a in alerts if a.alert_type == "VENDOR_ANOMALY"]
        assert len(freq_alerts) == 0, "Normal vendor frequency should not produce VENDOR_ANOMALY"
