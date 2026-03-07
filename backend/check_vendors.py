from app.database import get_db
from app.models.document import Document

db = next(get_db())
invoices = db.query(Document).filter(Document.type == 'INVOICE').all()

vendor_names = set()
for inv in invoices:
    if inv.entities and 'vendor_name' in inv.entities:
        vendor_names.add(inv.entities['vendor_name'])

print(f'Unique vendor names in invoices:')
for vn in sorted(vendor_names):
    count = sum(1 for inv in invoices if inv.entities and inv.entities.get('vendor_name') == vn)    
    print(f'  {vn}: {count} invoices')
