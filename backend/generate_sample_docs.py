"""
Generate sample LR, POD, and Invoice PNG documents for FreightIQ testing.
All 3 documents share the same shipment (SHIP2024001) so they will MATCH.
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "sample_docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

W, H = 900, 1200
BG     = (255, 255, 255)
BLACK  = (0, 0, 0)
BLUE   = (15, 52, 120)
GRAY   = (120, 120, 120)
LGREEN = (220, 255, 220)
LINE   = (200, 200, 200)

# ── Try to use a readable system font, fall back to default ──
def get_font(size=18, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/verdana.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

def draw_header(draw, title, subtitle, doc_no):
    draw.rectangle([0, 0, W, 90], fill=BLUE)
    draw.text((30, 12), title,   fill=(255,255,255), font=get_font(28, bold=True))
    draw.text((30, 52), subtitle, fill=(200,220,255), font=get_font(15))
    draw.text((W-260, 20), doc_no, fill=(255,255,200), font=get_font(14, bold=True))

def draw_row(draw, y, label, value, bold_val=True):
    draw.text((40,  y), label + ":", fill=GRAY, font=get_font(15))
    draw.text((260, y), value,       fill=BLACK, font=get_font(15, bold=bold_val))
    draw.line([(40, y+24), (860, y+24)], fill=LINE, width=1)

def draw_section(draw, y, title):
    draw.rectangle([30, y, W-30, y+30], fill=(230,237,255))
    draw.text((40, y+5), title, fill=BLUE, font=get_font(14, bold=True))
    return y + 36

# ════════════════════════════════════════════
# 1.  LR – Lorry Receipt
# ════════════════════════════════════════════
def make_lr():
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw_header(draw,
        "LORRY RECEIPT (LR)",
        "ABC Transport & Logistics Pvt. Ltd.",
        "LR No: SHIP2024001")

    y = 110
    y = draw_section(draw, y, "SHIPMENT DETAILS")
    rows = [
        ("LR Number",       "SHIP2024001"),
        ("Date",            "01-03-2024"),
        ("Consignment No",  "SHIP2024001"),
        ("Consignor",       "Global Traders Pvt. Ltd."),
        ("Consignee",       "Metro Distributors Ltd."),
        ("From",            "Mumbai"),
        ("To",              "Delhi"),
        ("Vehicle Number",  "MH 04 AB 1234"),
        ("Weight",          "1500 KG"),
        ("GST Number",      "27ABCDE1234F1Z5"),
    ]
    for label, value in rows:
        draw_row(draw, y, label, value)
        y += 32

    y += 10
    y = draw_section(draw, y, "FREIGHT CHARGES")
    charges = [
        ("Freight Charges",   "Rs. 45,000"),
        ("Loading Charges",   "Rs. 2,500"),
        ("Fuel Surcharge",    "Rs. 500"),
        ("Sub-Total",         "Rs. 48,000"),
        ("GST @ 18%",         "Rs. 8,640"),
        ("Total Amount",      "Rs. 56,640"),
    ]
    for label, value in charges:
        draw_row(draw, y, label, value)
        y += 32

    # Grand total box
    y += 10
    draw.rectangle([30, y, W-30, y+50], fill=LGREEN, outline=BLUE, width=2)
    draw.text((40, y+12),
              "Grand Total (Freight):   Rs. 56,640",
              fill=BLUE, font=get_font(18, bold=True))
    y += 70

    draw.text((40, y+10), "Authorized Signatory: ____________________",
              fill=BLACK, font=get_font(14))
    draw.text((40, y+40), "Stamp & Seal of Carrier",
              fill=GRAY, font=get_font(12))

    path = os.path.join(OUTPUT_DIR, "LR_SHIP2024001.png")
    img.save(path, dpi=(150, 150))
    print(f"  Saved: {path}")

# ════════════════════════════════════════════
# 2.  POD – Proof of Delivery
# ════════════════════════════════════════════
def make_pod():
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw_header(draw,
        "PROOF OF DELIVERY (POD)",
        "ABC Transport & Logistics Pvt. Ltd.",
        "POD Ref: SHIP2024001")

    y = 110
    y = draw_section(draw, y, "DELIVERY DETAILS")
    rows = [
        ("LR / Docket No",  "SHIP2024001"),
        ("Delivery Date",   "05-03-2024"),
        ("Consignment No",  "SHIP2024001"),
        ("Consignor",       "Global Traders Pvt. Ltd."),
        ("Consignee",       "Metro Distributors Ltd."),
        ("From",            "Mumbai"),
        ("To",              "Delhi"),
        ("Vehicle Number",  "MH 04 AB 1234"),
        ("Weight Delivered","1500 KG"),
        ("Condition",       "Good - No Damage"),
    ]
    for label, value in rows:
        draw_row(draw, y, label, value)
        y += 32

    y += 10
    y = draw_section(draw, y, "CONFIRMATION")
    draw.text((40, y+8),
              "Goods received in satisfactory condition.",
              fill=BLACK, font=get_font(15))
    y += 48

    # Receiver box
    draw.rectangle([30, y, W-30, y+80], outline=BLUE, width=2)
    draw.text((40, y+10), "Receiver Name:   Rajesh Kumar",         fill=BLACK, font=get_font(14))
    draw.text((40, y+35), "Receiver Sign:   ____________________",  fill=BLACK, font=get_font(14))
    draw.text((40, y+58), "Date:            05-03-2024",            fill=BLACK, font=get_font(14))
    y += 100

    draw.rectangle([30, y, W-30, y+50], fill=LGREEN, outline=BLUE, width=2)
    draw.text((40, y+12),
              "Amount Acknowledged:   Rs. 56,640",
              fill=BLUE, font=get_font(18, bold=True))

    path = os.path.join(OUTPUT_DIR, "POD_SHIP2024001.png")
    img.save(path, dpi=(150, 150))
    print(f"  Saved: {path}")

# ════════════════════════════════════════════
# 3.  Invoice
# ════════════════════════════════════════════
def make_invoice():
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw_header(draw,
        "TAX INVOICE",
        "Global Traders Pvt. Ltd.",
        "Invoice No: INV-SHIP2024001")

    y = 110
    y = draw_section(draw, y, "INVOICE DETAILS")
    rows = [
        ("Invoice Number",  "INV-SHIP2024001"),
        ("Invoice Date",    "06-03-2024"),
        ("LR Number",       "SHIP2024001"),
        ("Shipment ID",     "SHIP2024001"),
        ("Bill To",         "Metro Distributors Ltd."),
        ("Consignor",       "Global Traders Pvt. Ltd."),
        ("GST Number",      "27ABCDE1234F1Z5"),
        ("From",            "Mumbai"),
        ("Destination",     "Delhi"),
    ]
    for label, value in rows:
        draw_row(draw, y, label, value)
        y += 32

    y += 10
    y = draw_section(draw, y, "BILLING SUMMARY")
    items = [
        ("Basic Freight Charges",   "45,000"),
        ("Loading / Unloading",     " 2,500"),
        ("Fuel Surcharge",          "   500"),
        ("Sub-Total",               "48,000"),
        ("CGST @ 9%",               " 4,320"),
        ("SGST @ 9%",               " 4,320"),
        ("Net Amount",              "56,640"),
    ]
    for label, value in items:
        draw_row(draw, y, f"  {label}", f"Rs. {value}")
        y += 30

    y += 10
    draw.rectangle([30, y, W-30, y+55], fill=LGREEN, outline=BLUE, width=2)
    draw.text((40, y+14),
              "Total Amount (INR):   Rs. 56,640",
              fill=BLUE, font=get_font(20, bold=True))
    y += 75

    draw.text((40, y),    "Amount in Words: Fifty-Six Thousand Six Hundred Forty Only",
              fill=GRAY, font=get_font(13))
    draw.text((40, y+30), "Payment Terms: 30 Days from Invoice Date",
              fill=GRAY, font=get_font(13))
    draw.text((40, y+60), "Authorised Signatory: ____________________",
              fill=BLACK, font=get_font(14))

    path = os.path.join(OUTPUT_DIR, "INVOICE_SHIP2024001.png")
    img.save(path, dpi=(150, 150))
    print(f"  Saved: {path}")

# ════════════════════════════════════════════
if __name__ == "__main__":
    print("Generating sample documents...")
    make_lr()
    make_pod()
    make_invoice()
    print(f"\nAll 3 documents saved to: {OUTPUT_DIR}")
    print("\nUpload order:")
    print("  1. LR_SHIP2024001.png   → select type: LR")
    print("  2. POD_SHIP2024001.png  → select type: POD")
    print("  3. INVOICE_SHIP2024001.png → select type: Invoice")
    print("\nThen click 'Run Matching' to see the triplet get auto-matched!")
