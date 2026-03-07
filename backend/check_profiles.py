from app.database import get_db
from app.models.vendor_profile import VendorProfile

db = next(get_db())
profiles = db.query(VendorProfile).all()

print(f'Vendor profiles ({len(profiles)}):')
for p in profiles:
    print(f'  {p.vendor_name}: {p.total_invoices} invoices')
