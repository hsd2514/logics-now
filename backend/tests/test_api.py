"""Integration tests for FastAPI routes using an in-memory SQLite database."""
import io
import pytest
from fastapi.testclient import TestClient


# ── Health / root ─────────────────────────────────────────────────────────────

class TestRoot:
    def test_root_returns_app_info(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "FreightIQ"
        assert "version" in data

    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


# ── Stats ─────────────────────────────────────────────────────────────────────

class TestStats:
    def test_stats_returns_structure(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "documents" in data
        assert "triplets"  in data
        assert "fraud"     in data

    def test_stats_empty_db(self, client):
        resp = client.get("/api/stats")
        data = resp.json()
        assert data["documents"]["total"] == 0
        assert data["triplets"]["total"]  == 0


# ── Documents ─────────────────────────────────────────────────────────────────

class TestDocuments:
    def _make_file(self, content: str = "dummy content", filename: str = "test.txt"):
        return ("files", (filename, io.BytesIO(content.encode()), "text/plain"))

    def test_list_documents_empty(self, client):
        resp = client.get("/api/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["documents"] == []

    def test_upload_invalid_doc_type(self, client):
        file_bytes = io.BytesIO(b"fake content")
        resp = client.post(
            "/api/documents/upload?doc_type=INVALID",
            files={"file": ("test.pdf", file_bytes, "application/pdf")},
        )
        assert resp.status_code == 400

    def test_get_nonexistent_document(self, client):
        resp = client.get("/api/documents/nonexistent-id")
        assert resp.status_code == 404

    def test_delete_nonexistent_document(self, client):
        resp = client.delete("/api/documents/nonexistent-id")
        assert resp.status_code == 404

    def test_list_documents_with_filter(self, client):
        resp = client.get("/api/documents?doc_type=LR")
        assert resp.status_code == 200
        data = resp.json()
        # Empty DB → 0 results, but the endpoint should work
        assert "documents" in data


# ── Triplets ──────────────────────────────────────────────────────────────────

class TestTriplets:
    def test_list_triplets_empty(self, client):
        resp = client.get("/api/triplets")
        assert resp.status_code == 200
        data = resp.json()
        assert "triplets" in data
        assert data["total"] == 0

    def test_run_matching_with_no_documents(self, client):
        resp = client.post("/api/triplets/match")
        # Should succeed (0 triplets created), not crash
        assert resp.status_code == 200

    def test_get_nonexistent_triplet(self, client):
        resp = client.get("/api/triplets/nonexistent-id")
        assert resp.status_code == 404

    def test_approve_nonexistent_triplet(self, client):
        resp = client.post(
            "/api/triplets/nonexistent-id/approve",
            json={"action": "approve", "reviewed_by": "tester", "notes": ""},
        )
        assert resp.status_code == 404

    def test_reject_nonexistent_triplet(self, client):
        resp = client.post(
            "/api/triplets/nonexistent-id/reject",
            json={"action": "reject", "reviewed_by": "tester", "notes": ""},
        )
        assert resp.status_code == 404


# ── Fraud ─────────────────────────────────────────────────────────────────────

class TestFraud:
    def test_list_alerts_empty(self, client):
        resp = client.get("/api/fraud/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data

    def test_list_alerts_with_status_filter(self, client):
        resp = client.get("/api/fraud/alerts?status=OPEN")
        assert resp.status_code == 200

    def test_get_predictions(self, client):
        resp = client.get("/api/fraud/predictions")
        assert resp.status_code == 200

    def test_dismiss_nonexistent_alert(self, client):
        resp = client.post(
            "/api/fraud/alerts/nonexistent-id/dismiss",
            json={"user_id": "tester"},
        )
        assert resp.status_code == 404

    def test_confirm_nonexistent_alert(self, client):
        resp = client.post(
            "/api/fraud/alerts/nonexistent-id/confirm",
            json={"user_id": "tester"},
        )
        assert resp.status_code == 404


# ── AI routes ─────────────────────────────────────────────────────────────────

class TestAIRoutes:
    def test_chat_sync_nonexistent_doc(self, client):
        resp = client.post(
            "/api/ai/chat/sync",
            json={"document_id": "nonexistent", "message": "What is the amount?"},
        )
        assert resp.status_code == 404

    def test_query_sync_returns_filters(self, client):
        resp = client.post(
            "/api/ai/query/sync",
            json={"query": "show invoices above 50000"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "filters" in data
        # Fallback parser should pick up amount_min
        assert data["filters"].get("amount_min") == 50000.0

    def test_query_sync_status_keyword(self, client):
        resp = client.post(
            "/api/ai/query/sync",
            json={"query": "show all pending triplets"},
        )
        assert resp.status_code == 200
        filters = resp.json().get("filters", {})
        assert filters.get("status") == "PENDING"

    def test_query_sync_date_keyword(self, client):
        resp = client.post(
            "/api/ai/query/sync",
            json={"query": "documents from last week"},
        )
        assert resp.status_code == 200
        filters = resp.json().get("filters", {})
        assert "date_from" in filters
