"""
Generate sample LR, POD, and Invoice as HTML files.
HTML files bypass Tesseract OCR — text is extracted directly.
All 3 documents share shipment SHIP2024001 so they will MATCH.
"""
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "sample_docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

STYLE = """
<style>
  body { font-family: Arial, sans-serif; margin: 40px; color: #222; }
  h1   { background: #0f3478; color: white; padding: 18px 24px; margin: 0 0 4px; }
  h2   { background: #e6ecff; color: #0f3478; padding: 6px 24px; margin: 0 0 16px; font-size:14px; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
  td   { padding: 8px 12px; border-bottom: 1px solid #ddd; }
  td:first-child { color: #666; width: 220px; }
  td:last-child  { font-weight: bold; }
  .total { background: #dcfce7; border: 2px solid #0f3478; padding: 14px 20px;
           font-size: 18px; font-weight: bold; color: #0f3478; margin: 10px 0; }
  .section { background: #e6ecff; padding: 6px 12px; font-weight: bold;
             color: #0f3478; margin: 16px 0 6px; font-size: 13px; }
</style>
"""

# ── LR ──────────────────────────────────────────────
LR_HTML = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>LR SHIP2024001</title>{STYLE}</head>
<body>
<h1>LORRY RECEIPT (LR)</h1>
<h2>ABC Transport &amp; Logistics Pvt. Ltd. &nbsp;|&nbsp; LR No: SHIP2024001</h2>

<div class="section">SHIPMENT DETAILS</div>
<table>
  <tr><td>LR Number</td><td>SHIP2024001</td></tr>
  <tr><td>Date</td><td>01-03-2024</td></tr>
  <tr><td>Consignment No</td><td>SHIP2024001</td></tr>
  <tr><td>Consignor</td><td>Global Traders Pvt. Ltd.</td></tr>
  <tr><td>Consignee</td><td>Metro Distributors Ltd.</td></tr>
  <tr><td>From</td><td>Mumbai</td></tr>
  <tr><td>To</td><td>Delhi</td></tr>
  <tr><td>Vehicle Number</td><td>MH 04 AB 1234</td></tr>
  <tr><td>Weight</td><td>1500 KG</td></tr>
  <tr><td>GST Number</td><td>27ABCDE1234F1Z5</td></tr>
</table>

<div class="section">FREIGHT CHARGES</div>
<table>
  <tr><td>Freight Charges</td><td>Rs. 45,000</td></tr>
  <tr><td>Loading Charges</td><td>Rs. 2,500</td></tr>
  <tr><td>Fuel Surcharge</td><td>Rs. 500</td></tr>
  <tr><td>Sub-Total</td><td>Rs. 48,000</td></tr>
  <tr><td>GST @ 18%</td><td>Rs. 8,640</td></tr>
  <tr><td>Total Amount</td><td>Rs. 56,640</td></tr>
</table>

<div class="total">Grand Total (Freight): Rs. 56,640</div>
<p>Authorized Signatory: ____________________</p>
<p style="color:#888">Stamp &amp; Seal of Carrier</p>
</body></html>"""

# ── POD ─────────────────────────────────────────────
POD_HTML = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>POD SHIP2024001</title>{STYLE}</head>
<body>
<h1>PROOF OF DELIVERY (POD)</h1>
<h2>ABC Transport &amp; Logistics Pvt. Ltd. &nbsp;|&nbsp; POD Ref: SHIP2024001</h2>

<div class="section">DELIVERY DETAILS</div>
<table>
  <tr><td>LR / Docket No</td><td>SHIP2024001</td></tr>
  <tr><td>Delivery Date</td><td>05-03-2024</td></tr>
  <tr><td>Consignment No</td><td>SHIP2024001</td></tr>
  <tr><td>Consignor</td><td>Global Traders Pvt. Ltd.</td></tr>
  <tr><td>Consignee</td><td>Metro Distributors Ltd.</td></tr>
  <tr><td>From</td><td>Mumbai</td></tr>
  <tr><td>To</td><td>Delhi</td></tr>
  <tr><td>Vehicle Number</td><td>MH 04 AB 1234</td></tr>
  <tr><td>Weight Delivered</td><td>1500 KG</td></tr>
  <tr><td>Condition</td><td>Good - No Damage</td></tr>
</table>

<div class="section">CONFIRMATION</div>
<p>Goods received in satisfactory condition.</p>
<table>
  <tr><td>Receiver Name</td><td>Rajesh Kumar</td></tr>
  <tr><td>Receiver Sign</td><td>____________________</td></tr>
  <tr><td>Date</td><td>05-03-2024</td></tr>
</table>

<div class="total">Amount Acknowledged: Rs. 56,640</div>
</body></html>"""

# ── Invoice ──────────────────────────────────────────
INVOICE_HTML = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Invoice SHIP2024001</title>{STYLE}</head>
<body>
<h1>TAX INVOICE</h1>
<h2>Global Traders Pvt. Ltd. &nbsp;|&nbsp; Invoice No: INV-SHIP2024001</h2>

<div class="section">INVOICE DETAILS</div>
<table>
  <tr><td>Invoice Number</td><td>INV-SHIP2024001</td></tr>
  <tr><td>Invoice Date</td><td>06-03-2024</td></tr>
  <tr><td>LR Number</td><td>SHIP2024001</td></tr>
  <tr><td>Shipment ID</td><td>SHIP2024001</td></tr>
  <tr><td>Bill To</td><td>Metro Distributors Ltd.</td></tr>
  <tr><td>Consignor</td><td>Global Traders Pvt. Ltd.</td></tr>
  <tr><td>GST Number</td><td>27ABCDE1234F1Z5</td></tr>
  <tr><td>From</td><td>Mumbai</td></tr>
  <tr><td>Destination</td><td>Delhi</td></tr>
</table>

<div class="section">BILLING SUMMARY</div>
<table>
  <tr><td>Basic Freight Charges</td><td>Rs. 45,000</td></tr>
  <tr><td>Loading / Unloading</td><td>Rs. 2,500</td></tr>
  <tr><td>Fuel Surcharge</td><td>Rs. 500</td></tr>
  <tr><td>Sub-Total</td><td>Rs. 48,000</td></tr>
  <tr><td>CGST @ 9%</td><td>Rs. 4,320</td></tr>
  <tr><td>SGST @ 9%</td><td>Rs. 4,320</td></tr>
  <tr><td>Net Amount</td><td>Rs. 56,640</td></tr>
</table>

<div class="total">Total Amount (INR): Rs. 56,640</div>
<p style="color:#666">Amount in Words: Fifty-Six Thousand Six Hundred Forty Only</p>
<p style="color:#666">Payment Terms: 30 Days from Invoice Date</p>
<p>Authorised Signatory: ____________________</p>
</body></html>"""

# ── Write files ──────────────────────────────────────
files = {
    "LR_SHIP2024001.html":      LR_HTML,
    "POD_SHIP2024001.html":     POD_HTML,
    "INVOICE_SHIP2024001.html": INVOICE_HTML,
}

for name, content in files.items():
    path = os.path.join(OUTPUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Saved: {path}")

print(f"\nAll 3 HTML documents saved to: {OUTPUT_DIR}")
print("\nUpload order in the app:")
print("  1. LR_SHIP2024001.html      → type: LR")
print("  2. POD_SHIP2024001.html     → type: POD")
print("  3. INVOICE_SHIP2024001.html → type: Invoice")
print("\nThen click 'Run Matching' — no Tesseract needed!")
