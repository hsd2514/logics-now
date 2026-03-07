from app.database import SessionLocal
from app.models.document import Document
from app.services.vendor_service import VendorService
from datetime import datetime

db = SessionLocal()
vendor_service = VendorService()

# Get all invoices
invoices = db.query(Document).filter(Document.type == "INVOICE").all()

print(f"Found {len(invoices)} invoices")

updated_count = 0
for invoice in invoices:
    if invoice.entities and invoice.entities.get('vendor_name'):
        vendor_name = invoice.entities.get('vendor_name')
        amount = invoice.entities.get('amount', 0)
        route = f"{invoice.entities.get('origin', '')}-{invoice.entities.get('destination', '')}"
        
        # Parse date
        date_str = invoice.entities.get('date')
        try:
            invoice_date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else invoice.upload_date
        except:
            invoice_date = invoice.upload_date
        
        print(f"Processing vendor: {vendor_name}, amount: {amount}, route: {route}")
        vendor_service.update_vendor_profile(
            db, vendor_name, float(amount) if amount else 0.0, route, invoice_date
        )
        updated_count += 1

print(f"Updated {updated_count} vendor profiles")

# Check what profiles we have now
from app.models.vendor_profile import VendorProfile
profiles = db.query(VendorProfile).all()
print(f"\nVendor profiles  in DB: {len(profiles)}")
for p in profiles:
    print(f"  {p.vendor_name}: {p.total_invoices} invoices")
