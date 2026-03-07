from app.database import get_db
from app.models.document import Document

db = next(get_db())
invoices = db.query(Document).filter(Document.type == 'INVOICE').all()

print(f'Total invoices: {len(invoices)}')
if invoices:
    for i, inv in enumerate(invoices[:5]):
        print(f'\nInvoice {i+1}:')
        print(f'  ID: {inv.id}')
        print(f'  Has entities: {inv.entities is not None}')
        if inv.entities:
            print(f'  Entity keys: {list(inv.entities.keys())}')
            print(f'  party_name: {inv.entities.get("party_name")}')
            print(f'  amount: {inv.entities.get("amount")}')
