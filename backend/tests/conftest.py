"""Shared pytest fixtures for FreightIQ backend tests."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db


# ── In-memory SQLite for tests ─────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture(scope="function")
def db(engine):
    """Return a clean DB session per test (rolled back after each test)."""
    connection  = engine.connect()
    transaction = connection.begin()
    TestingSession = sessionmaker(bind=connection)
    session = TestingSession()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    """FastAPI test client wired to the test DB session."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Reusable entity dicts ──────────────────────────────────────────────────────
@pytest.fixture
def sample_lr_entities():
    return {
        "shipment_id": "LR20240001",
        "amount": 75000.0,
        "date": "2024-01-15",
        "party_name": "ABC Logistics Ltd",
        "origin": "Mumbai",
        "destination": "Delhi",
        "vehicle_number": "MH12AB1234",
        "weight": 500.0,
    }


@pytest.fixture
def sample_pod_entities():
    return {
        "shipment_id": "LR20240001",
        "amount": 75000.0,
        "date": "2024-01-18",
        "party_name": "ABC Logistics Ltd",
        "origin": "Mumbai",
        "destination": "Delhi",
        "vehicle_number": "MH12AB1234",
    }


@pytest.fixture
def sample_invoice_entities():
    return {
        "shipment_id": "LR20240001",
        "amount": 75500.0,   # slight variance within 2% tolerance
        "date": "2024-01-20",
        "party_name": "ABC Logistics Ltd",
    }
