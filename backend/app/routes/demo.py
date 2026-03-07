"""
Demo route — generates synthetic HTML documents and runs the full pipeline.
No real PDFs needed. Uses the HTML processing path (direct text extraction).

POST /api/demo/generate   → creates 1 LR + 1 POD + 1 INVOICE, matches them, returns triplet
"""

import os
import uuid
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.document import Document, DocumentType, DocumentStatus
from app.services.document_service import DocumentService
from app.services.matching_service import MatchingService
from app.config import get_settings

router = APIRouter()
document_service = DocumentService()
matching_service = MatchingService()
settings = get_settings()

# ── Sample data pools ─────────────────────────────────────────────────────────

VENDORS = [
    ("FastFreight Pvt Ltd",   "27AABCF1234A1Z5"),
    ("BlueChain Logistics",   "29AADBL5678B2Z3"),
    ("SwiftMove Corp",        "19AADSM9012C3Z7"),
    ("Apex Transport Ltd",    "06AADAT3456D4Z1"),
    ("SkyHaul Enterprises",   "33AADSE7890E5Z9"),
]

CONSIGNEES = [
    "Reliance Retail Ltd",
    "Tata Enterprises Pvt Ltd",
    "Infosys Supply Chain",
    "HCL Technologies",
    "HDFC Bank Ltd",
]

ROUTES = [
    ("Mumbai",    "Hyderabad"),
    ("Delhi",     "Bangalore"),
    ("Pune",      "Chennai"),
    ("Chennai",   "Kolkata"),
    ("Ahmedabad", "Jaipur"),
]

GOODS = [
    "Electronic Components",
    "Textile Goods",
    "FMCG Products",
    "Automotive Parts",
    "Pharmaceutical Goods",
]

VEHICLES = [
    "MH12AB1234", "DL10CD5678", "KA03EF9012",
    "TN22GH3456", "GJ15IJ7890",
]


# ── HTML templates ─────────────────────────────────────────────────────────────

def lr_html(d: dict) -> str:
    return f"""<!DOCTYPE html>
<html>
<body>
<h1>LORRY RECEIPT</h1>
<p>Reference: {d['lr_no']}</p>
<p>Date: {d['date']}</p>
<p>Consignment# {d['shipment_id']}</p>
<p>Consignor: {d['vendor']}</p>
<p>GSTIN: {d['gst']}</p>
<p>Consignee: {d['consignee']}</p>
<p>From: {d['origin']}</p>
<p>To: {d['destination']}</p>
<p>Vehicle: {d['vehicle']}</p>
<p>Goods: {d['goods']}</p>
<p>Weight: {d['weight']} KG</p>
<p>Freight Amount: Rs. {d['amount']}</p>
<p>Total: {d['amount']}</p>
</body>
</html>"""


def pod_html(d: dict) -> str:
    return f"""<!DOCTYPE html>
<html>
<body>
<h1>PROOF OF DELIVERY</h1>
<p>Reference: {d['pod_no']}</p>
<p>Date: {d['date']}</p>
<p>Consignment# {d['shipment_id']}</p>
<p>Consignor: {d['vendor']}</p>
<p>Consignee: {d['consignee']}</p>
<p>From: {d['origin']}</p>
<p>To: {d['destination']}</p>
<p>Vehicle: {d['vehicle']}</p>
<p>Goods: {d['goods']}</p>
<p>Weight: {d['weight']} KG</p>
<p>Amount: Rs. {d['amount']}</p>
<p>Delivery Status: Delivered Successfully</p>
<p>Receiver Signature: Acknowledged</p>
</body>
</html>"""


def invoice_html(d: dict, invoice_amount: int) -> str:
    return f"""<!DOCTYPE html>
<html>
<body>
<h1>TAX INVOICE</h1>
<p>Reference: {d['inv_no']}</p>
<p>Date: {d['date']}</p>
<p>Consignment# {d['shipment_id']}</p>
<p>Billed To: {d['consignee']}</p>
<p>From: {d['vendor']}</p>
<p>GSTIN: {d['gst']}</p>
<p>Description: Freight charges for {d['goods']}</p>
<p>From: {d['origin']}</p>
<p>To: {d['destination']}</p>
<p>Amount: ₹{invoice_amount}</p>
<p>Total: {invoice_amount}</p>
</body>
</html>"""


# ── helpers ───────────────────────────────────────────────────────────────────

def _save_html(content: str, doc_type: str) -> tuple[str, str]:
    """Save HTML content to upload dir, return (file_id, file_path)."""
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    filename = f"{file_id}.html"
    file_path = os.path.join(settings.upload_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_id, file_path


async def _create_and_process(db: Session, file_id: str, file_path: str,
                               file_name: str, doc_type: str) -> Document:
    doc = Document(
        id=file_id,
        type=doc_type,
        file_name=file_name,
        file_path=file_path,
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    db.commit()
    doc = await document_service.process_document(db, doc)
    return doc


# ── endpoint ──────────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_demo(
    anomaly: bool = False,
    db: Session = Depends(get_db),
):
    """
    Generate a synthetic LR + POD + Invoice triplet set and run matching.

    - anomaly=false  → amounts match  (healthy, high-confidence triplet)
    - anomaly=true   → invoice inflated by 20-40%  (fraud alert triggered)
    """
    vendor, gst     = random.choice(VENDORS)
    consignee       = random.choice(CONSIGNEES)
    origin, dest    = random.choice(ROUTES)
    goods           = random.choice(GOODS)
    vehicle         = random.choice(VEHICLES)
    amount          = random.randint(25_000, 180_000)
    invoice_amount  = amount if not anomaly else int(amount * random.uniform(1.20, 1.40))
    weight          = random.randint(500, 8_000)
    date_str        = (datetime.now() - timedelta(days=random.randint(1, 10))).strftime("%d/%m/%Y")
    suffix          = str(random.randint(100_000, 999_999))

    d = dict(
        shipment_id = f"SHP{suffix}",
        lr_no       = f"DOC{suffix}L",   # avoids LR/POD/INV prefixes that trigger entity patterns
        pod_no      = f"DOC{suffix}P",
        inv_no      = f"DOC{suffix}I",
        vendor      = vendor,
        gst         = gst,
        consignee   = consignee,
        origin      = origin,
        destination = dest,
        goods       = goods,
        vehicle     = vehicle,
        amount      = amount,
        weight      = weight,
        date        = date_str,
    )

    # Save HTML files
    lr_id,  lr_path  = _save_html(lr_html(d),                         "LR")
    pod_id, pod_path = _save_html(pod_html(d),                        "POD")
    inv_id, inv_path = _save_html(invoice_html(d, invoice_amount),    "INVOICE")

    # Process through pipeline
    lr_doc  = await _create_and_process(db, lr_id,  lr_path,  f"LR_{d['lr_no']}.html",  "LR")
    pod_doc = await _create_and_process(db, pod_id, pod_path, f"POD_{d['pod_no']}.html", "POD")
    inv_doc = await _create_and_process(db, inv_id, inv_path, f"INV_{d['inv_no']}.html", "INVOICE")

    # Run matching
    triplets, events = matching_service.match_documents(db)

    return {
        "message": f"Demo documents created and {'anomalous ' if anomaly else ''}triplet matched.",
        "shipment_id": d["shipment_id"],
        "documents": {
            "lr":      {"id": lr_doc.id,  "entities": lr_doc.entities},
            "pod":     {"id": pod_doc.id, "entities": pod_doc.entities},
            "invoice": {"id": inv_doc.id, "entities": inv_doc.entities},
        },
        "triplets_created": len(triplets),
        "triplet_ids": [t.id for t in triplets],
        "events_emitted": len(events),
    }
