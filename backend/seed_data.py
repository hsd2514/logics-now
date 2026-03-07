"""
Seed script – populates the SQLite DB with realistic sample data.
Run from the backend/ directory:
    uv run python seed_data.py
"""

import uuid
from datetime import datetime, timedelta
import random
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.database import Base, engine, SessionLocal
from app.models.document import Document, DocumentType, DocumentStatus
from app.models.triplet import Triplet, TripletStatus
from app.models.fraud_alert import FraudAlert, AlertType, AlertStatus

# ── helpers ──────────────────────────────────────────────────────────────────

def uid():
    return str(uuid.uuid4())

def dt(days_ago: int, hour: int = 10):
    return datetime.now() - timedelta(days=days_ago, hours=hour)


# ── entity sets ──────────────────────────────────────────────────────────────

VENDORS = ["FastFreight Pvt Ltd", "BlueChain Logistics", "SwiftMove Corp",
           "Apex Transport", "SkyHaul Inc"]

CONSIGNEES = ["Reliance Retail", "Tata Enterprises", "Infosys Ltd",
               "HCL Supply Chain", "HDFC Bank"]

SHIPMENT_IDS = [f"SHP{2024000 + i}" for i in range(1, 21)]

def make_entities(shipment_id, vendor, consignee, amount, date, vehicle="MH12AB1234"):
    return {
        "shipment_id": shipment_id,
        "vendor_name": vendor,
        "consignee_name": consignee,
        "amount": str(amount),
        "date": date,
        "vehicle_number": vehicle,
        "origin": random.choice(["Mumbai", "Delhi", "Pune", "Chennai", "Bangalore"]),
        "destination": random.choice(["Hyderabad", "Kolkata", "Ahmedabad", "Surat", "Jaipur"]),
    }

def make_text_blocks():
    return [
        {"text": "LR No:", "x": 50, "y": 80, "w": 80, "h": 20, "conf": 0.95},
        {"text": "Shipment ID:", "x": 50, "y": 110, "w": 100, "h": 20, "conf": 0.92},
        {"text": "Vendor:", "x": 50, "y": 140, "w": 70, "h": 20, "conf": 0.97},
        {"text": "Consignee:", "x": 50, "y": 170, "w": 90, "h": 20, "conf": 0.93},
        {"text": "Amount:", "x": 50, "y": 200, "w": 75, "h": 20, "conf": 0.96},
    ]

def make_field_matches(score_override=None):
    s = score_override if score_override is not None else round(random.uniform(0.75, 1.0), 3)
    return {
        "shipment_id": {"score": s, "values": {"lr": "SHP2024001", "pod": "SHP2024001", "invoice": "SHP2024001"}},
        "vendor_name":  {"score": round(s * 0.98, 3), "values": {"lr": "FastFreight", "pod": "FastFreight", "invoice": "FastFreight Pvt Ltd"}},
        "amount":       {"score": round(s * 0.97, 3), "values": {"lr": "45000", "pod": "45000", "invoice": "45000"}},
        "date":         {"score": round(s * 0.95, 3), "values": {"lr": "2024-01-15", "pod": "2024-01-15", "invoice": "2024-01-15"}},
    }


# ── seed function ─────────────────────────────────────────────────────────────

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Wipe existing data so we can re-seed safely
        existing = db.query(Document).count()
        if existing > 0:
            print(f"Clearing {existing} existing documents (and related records)…")
            from app.models.audit_log import AuditLog
            db.query(AuditLog).delete()
            db.query(FraudAlert).delete()
            db.query(Triplet).delete()
            db.query(Document).delete()
            db.commit()
            print("  Tables cleared.")

        triplet_records = []

        # ── 12 healthy triplets ───────────────────────────────────────────────
        for i in range(12):
            ship_id   = SHIPMENT_IDS[i]
            vendor    = VENDORS[i % len(VENDORS)]
            consignee = CONSIGNEES[i % len(CONSIGNEES)]
            amount    = random.randint(20000, 150000)
            date_str  = (datetime.now() - timedelta(days=random.randint(1, 60))).strftime("%Y-%m-%d")
            vehicle   = f"MH{random.randint(10,99)}AB{random.randint(1000,9999)}"
            days_ago  = random.randint(1, 45)
            conf      = round(random.uniform(0.82, 0.99), 3)

            lr = Document(
                id=uid(), type=DocumentType.LR, file_name=f"LR_{ship_id}.pdf",
                file_path=f"uploads/LR_{ship_id}.pdf",
                uploaded_at=dt(days_ago, 8),
                ocr_text=f"Lorry Receipt\nShipment: {ship_id}\nVendor: {vendor}\nConsignee: {consignee}\nAmount: ₹{amount}\nDate: {date_str}\nVehicle: {vehicle}",
                ocr_confidence=round(random.uniform(0.88, 0.99), 3),
                text_blocks=make_text_blocks(),
                entities=make_entities(ship_id, vendor, consignee, amount, date_str, vehicle),
                status=DocumentStatus.MATCHED,
            )
            pod = Document(
                id=uid(), type=DocumentType.POD, file_name=f"POD_{ship_id}.pdf",
                file_path=f"uploads/POD_{ship_id}.pdf",
                uploaded_at=dt(days_ago, 9),
                ocr_text=f"Proof of Delivery\nShipment: {ship_id}\nVendor: {vendor}\nConsignee: {consignee}\nAmount: ₹{amount}\nDate: {date_str}",
                ocr_confidence=round(random.uniform(0.88, 0.99), 3),
                text_blocks=make_text_blocks(),
                entities=make_entities(ship_id, vendor, consignee, amount, date_str, vehicle),
                status=DocumentStatus.MATCHED,
            )
            inv = Document(
                id=uid(), type=DocumentType.INVOICE, file_name=f"INV_{ship_id}.pdf",
                file_path=f"uploads/INV_{ship_id}.pdf",
                uploaded_at=dt(days_ago, 10),
                ocr_text=f"Tax Invoice\nShipment: {ship_id}\nVendor: {vendor}\nBilled To: {consignee}\nAmount: ₹{amount}\nDate: {date_str}",
                ocr_confidence=round(random.uniform(0.88, 0.99), 3),
                text_blocks=make_text_blocks(),
                entities=make_entities(ship_id, vendor, consignee, amount, date_str, vehicle),
                status=DocumentStatus.MATCHED,
            )

            db.add_all([lr, pod, inv])
            db.flush()

            status = random.choice([
                TripletStatus.AUTO_APPROVED, TripletStatus.AUTO_APPROVED,
                TripletStatus.APPROVED, TripletStatus.REVIEW,
            ])
            triplet = Triplet(
                id=uid(),
                lr_id=lr.id, pod_id=pod.id, invoice_id=inv.id,
                match_score=conf, confidence=conf,
                ocr_accuracy=round(random.uniform(0.88, 0.99), 3),
                ner_confidence=round(random.uniform(0.82, 0.98), 3),
                rule_pass_score=round(random.uniform(0.85, 1.0), 3),
                status=status,
                created_at=dt(days_ago, 11),
                validation_details={
                    "rules_passed": ["SHIPMENT_ID_MATCH", "AMOUNT_TOLERANCE", "DATE_MATCH"],
                    "rules_failed": [],
                    "field_matches": make_field_matches(conf),
                    "validation_results": [
                        {"rule": "SHIPMENT_ID_MATCH", "passed": True,  "message": "Shipment IDs match across all documents"},
                        {"rule": "AMOUNT_TOLERANCE",  "passed": True,  "message": "Amounts within ±5% tolerance"},
                        {"rule": "DATE_MATCH",         "passed": True,  "message": "Dates are consistent"},
                    ],
                },
                ai_explanation=f"All three documents for shipment {ship_id} from {vendor} are consistent. Shipment IDs, amounts (₹{amount:,}), and dates match across LR, POD, and Invoice. Confidence: {conf:.0%}.",
                attention_map={"fields": {"shipment_id": 0.9, "amount": 0.85, "vendor_name": 0.8, "date": 0.75}},
            )
            db.add(triplet)
            triplet_records.append(triplet)

        # ── 4 suspicious / fraud triplets ─────────────────────────────────────
        for i in range(4):
            ship_id   = SHIPMENT_IDS[12 + i]
            vendor    = VENDORS[i % len(VENDORS)]
            consignee = CONSIGNEES[(i + 2) % len(CONSIGNEES)]
            amount_lr = random.randint(50000, 200000)
            amount_inv = int(amount_lr * random.uniform(1.15, 1.4))   # inflated
            date_str  = (datetime.now() - timedelta(days=random.randint(5, 30))).strftime("%Y-%m-%d")
            days_ago  = random.randint(2, 15)
            conf      = round(random.uniform(0.38, 0.62), 3)

            lr = Document(
                id=uid(), type=DocumentType.LR, file_name=f"LR_{ship_id}.pdf",
                file_path=f"uploads/LR_{ship_id}.pdf",
                uploaded_at=dt(days_ago, 8),
                ocr_text=f"Lorry Receipt\nShipment: {ship_id}\nVendor: {vendor}\nAmount: ₹{amount_lr}\nDate: {date_str}",
                ocr_confidence=round(random.uniform(0.70, 0.85), 3),
                text_blocks=make_text_blocks(),
                entities=make_entities(ship_id, vendor, consignee, amount_lr, date_str),
                status=DocumentStatus.MATCHED,
            )
            pod = Document(
                id=uid(), type=DocumentType.POD, file_name=f"POD_{ship_id}.pdf",
                file_path=f"uploads/POD_{ship_id}.pdf",
                uploaded_at=dt(days_ago, 9),
                ocr_text=f"Proof of Delivery\nShipment: {ship_id}\nVendor: {vendor}\nAmount: ₹{amount_lr}\nDate: {date_str}",
                ocr_confidence=round(random.uniform(0.70, 0.85), 3),
                text_blocks=make_text_blocks(),
                entities=make_entities(ship_id, vendor, consignee, amount_lr, date_str),
                status=DocumentStatus.MATCHED,
            )
            inv = Document(
                id=uid(), type=DocumentType.INVOICE, file_name=f"INV_{ship_id}.pdf",
                file_path=f"uploads/INV_{ship_id}.pdf",
                uploaded_at=dt(days_ago, 10),
                ocr_text=f"Tax Invoice\nShipment: {ship_id}\nVendor: {vendor}\nAmount: ₹{amount_inv}\nDate: {date_str}",   # inflated
                ocr_confidence=round(random.uniform(0.70, 0.85), 3),
                text_blocks=make_text_blocks(),
                entities=make_entities(ship_id, vendor, consignee, amount_inv, date_str),
                status=DocumentStatus.MATCHED,
            )

            db.add_all([lr, pod, inv])
            db.flush()

            triplet = Triplet(
                id=uid(),
                lr_id=lr.id, pod_id=pod.id, invoice_id=inv.id,
                match_score=conf, confidence=conf,
                ocr_accuracy=round(random.uniform(0.70, 0.85), 3),
                ner_confidence=round(random.uniform(0.60, 0.78), 3),
                rule_pass_score=round(random.uniform(0.40, 0.65), 3),
                status=TripletStatus.REVIEW,
                created_at=dt(days_ago, 11),
                validation_details={
                    "rules_passed": ["SHIPMENT_ID_MATCH"],
                    "rules_failed": ["AMOUNT_TOLERANCE"],
                    "field_matches": {
                        "shipment_id": {"score": 0.95, "values": {"lr": ship_id, "pod": ship_id, "invoice": ship_id}},
                        "amount":       {"score": 0.42, "values": {"lr": str(amount_lr), "pod": str(amount_lr), "invoice": str(amount_inv)}},
                        "date":         {"score": 0.90, "values": {"lr": date_str, "pod": date_str, "invoice": date_str}},
                    },
                    "validation_results": [
                        {"rule": "SHIPMENT_ID_MATCH", "passed": True,  "message": "Shipment IDs match"},
                        {"rule": "AMOUNT_TOLERANCE",  "passed": False, "message": f"Invoice amount ₹{amount_inv:,} deviates from LR/POD ₹{amount_lr:,} by >{round((amount_inv/amount_lr-1)*100)}%"},
                    ],
                },
                ai_explanation=f"⚠️ Suspicious triplet for {ship_id}. Invoice shows ₹{amount_inv:,} but LR and POD show ₹{amount_lr:,} — a {round((amount_inv/amount_lr-1)*100)}% discrepancy exceeding allowed tolerance. Possible invoice inflation.",
                attention_map={"fields": {"amount": 0.95, "shipment_id": 0.5, "vendor_name": 0.4, "date": 0.3}},
            )
            db.add(triplet)
            triplet_records.append(triplet)

            alert_types = [AlertType.AMOUNT_ANOMALY, AlertType.PREDICTED, AlertType.VENDOR_ANOMALY, AlertType.DUPLICATE]
            fraud = FraudAlert(
                id=uid(),
                triplet_id=triplet.id,
                risk_score=round(random.uniform(0.68, 0.95), 3),
                alert_type=alert_types[i],
                details={
                    "amount_lr": amount_lr,
                    "amount_invoice": amount_inv,
                    "deviation_pct": round((amount_inv / amount_lr - 1) * 100, 1),
                    "rule": "AMOUNT_TOLERANCE",
                    "threshold": 5.0,
                },
                ai_reasoning=f"Invoice amount for {ship_id} is inflated by {round((amount_inv/amount_lr-1)*100)}% compared to LR and POD. Historical average deviation for {vendor} is <3%. This pattern is consistent with invoice manipulation.",
                status=random.choice([AlertStatus.OPEN, AlertStatus.INVESTIGATING]),
                created_at=dt(days_ago, 12),
            )
            db.add(fraud)

        # ── 2 DUPLICATE fraud alerts on healthy triplets ───────────────────────
        dup_trip = triplet_records[0]
        db.add(FraudAlert(
            id=uid(), triplet_id=dup_trip.id,
            risk_score=0.78,
            alert_type=AlertType.DUPLICATE,
            details={"duplicate_of": triplet_records[1].id, "similarity": 0.97},
            ai_reasoning="This shipment ID and amount combination was already processed 3 days ago. Possible duplicate submission.",
            status=AlertStatus.OPEN,
            created_at=dt(3, 10),
        ))

        db.commit()

        # Summary
        docs       = db.query(Document).count()
        triplets   = db.query(Triplet).count()
        alerts     = db.query(FraudAlert).count()
        print(f"\n✅ Seed complete!")
        print(f"   Documents : {docs}  (LR + POD + Invoice sets)")
        print(f"   Triplets  : {triplets}  (12 healthy, 4 suspicious)")
        print(f"   Fraud alerts: {alerts}")
        print(f"\nStart the backend:  uv run uvicorn app.main:app --reload")
        print(f"Open the frontend:  http://localhost:3001\n")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
