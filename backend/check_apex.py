from app.database import SessionLocal
from app.models.document import Document

db = SessionLocal()

vendor_name = "Apex Transport"

invoices = db.query(Document).filter(Document.type == "INVOICE").all()
print(f"Total invoices: {len(invoices)}")

vendor_invoices = [
    inv for inv in invoices 
    if inv.entities and inv.entities.get('vendor_name', '').strip().upper() == vendor_name.strip().upper()
]

print(f"Vendor invoices for '{vendor_name}': {len(vendor_invoices)}")

for inv in vendor_invoices[:5]:
    print(f"  Invoice ID: {inv.id}")
    print(f"    vendor_name: {inv.entities.get('vendor_name')}")
    print(f"    amount: {inv.entities.get('amount')}")
    print(f"   upload_date: {inv.upload_date}")
