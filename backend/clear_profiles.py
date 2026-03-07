from app.database import get_db, SessionLocal
from app.models.vendor_profile import VendorProfile

db = SessionLocal()

# Delete all old profiles
count = db.query(VendorProfile).delete()
db.commit()

print(f"Deleted {count} old vendor profiles")
