import sys, time
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

# ── Raw Gemini connection ──
print('=== RAW GEMINI CONNECTION TEST ===')
from google import genai
from google.genai import types
import os

client = genai.Client(api_key=os.environ.get('GOOGLE_API_KEY'))
try:
    r = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='Reply with exactly: GEMINI_OK',
        config=types.GenerateContentConfig(max_output_tokens=10)
    )
    print('Raw Gemini:', r.text.strip())
except Exception as e:
    print('Raw Gemini ERROR:', str(e)[:300])

time.sleep(8)

# ── Test 1: AuditGenerator ──
print()
print('=== TEST 1: AuditGenerator ===')
from app.ai.audit_generator import AuditGenerator
gen = AuditGenerator()
r1 = gen.generate_match_explanation(
    {'shipment_id': 'LR001', 'amount': '50000'},
    {'shipment_id': 'LR001'},
    {'shipment_id': 'LR001', 'amount': '51000'},
    0.92,
    [{'rule': 'AMOUNT_TOLERANCE', 'passed': True, 'message': 'Within 2%'}],
    'AUTO_APPROVED'
)
print('Response:', r1)

time.sleep(8)

# ── Test 2: NLQueryParser ──
print()
print('=== TEST 2: NLQueryParser ===')
from app.ai.nl_query import NLQueryParser
parser = NLQueryParser()
r2 = parser.parse('show rejected invoices above 50000 from last week')
print('Filters:', r2)

time.sleep(8)

# ── Test 3: DocumentChat ──
print()
print('=== TEST 3: DocumentChat ===')
from app.ai.doc_chat import DocumentChat
chat = DocumentChat()
r3 = chat.chat_sync(
    'LR No: LR001, Shipper: ABC Transport, Amount: 50000, Origin: Mumbai, Dest: Delhi',
    {'shipment_id': 'LR001', 'amount': '50000', 'party_name': 'ABC Transport'},
    'What is the shipment amount?'
)
print('Chat:', r3)

print()
print('=== ALL DONE ===')
