from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

# SQLite for development - change to postgresql:// for production
SQLALCHEMY_DATABASE_URL = settings.database_url

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from app.models import document, triplet, fraud_alert, vendor_profile, audit_log, contract_rate
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_schema()


def _migrate_sqlite_schema() -> None:
    if "sqlite" not in SQLALCHEMY_DATABASE_URL:
        return

    required_audit_columns = {
        "triplet_id": "TEXT",
        "document_id": "TEXT",
        "action": "TEXT",
        "ai_generated": "TEXT",
        "context": "JSON",
        "user_id": "TEXT",
        "timestamp": "DATETIME",
    }

    with engine.begin() as conn:
        table_exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
        ).first()
        if table_exists:
            rows = conn.execute(text("PRAGMA table_info(audit_logs)")).fetchall()
            existing = {row[1] for row in rows}
            for column, col_type in required_audit_columns.items():
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE audit_logs ADD COLUMN {column} {col_type}"))

        triplets_exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='triplets'")
        ).first()
        if triplets_exists:
            triplet_rows = conn.execute(text("PRAGMA table_info(triplets)")).fetchall()
            triplet_existing = {row[1] for row in triplet_rows}
            if "partial_delivery" not in triplet_existing:
                conn.execute(text("ALTER TABLE triplets ADD COLUMN partial_delivery BOOLEAN DEFAULT 0"))
