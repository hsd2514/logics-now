"""
Synthetic Document Generator for FreightIQ
Generates LR, POD, and Invoice documents as HTML files for testing
"""

import os
import random
import string
from datetime import datetime, timedelta
from jinja2 import Template

# Sample data pools
VENDORS = [
    "ABC Transport Pvt Ltd",
    "XYZ Logistics",
    "Fast Track Movers",
    "Express Freight Co",
    "National Carriers",
    "Interstate Logistics",
    "Prime Movers Ltd",
    "Swift Transport",
]

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
]

VEHICLES = [
    "MH01AB1234", "DL02CD5678", "KA03EF9012", "TN04GH3456",
    "AP05IJ7890", "WB06KL1234", "GJ07MN5678", "RJ08OP9012",
]

def generate_shipment_id():
    """Generate unique shipment ID."""
    prefix = random.choice(["LR", "SH", "CN", "AWB"])
    numbers = ''.join(random.choices(string.digits, k=8))
    return f"{prefix}{numbers}"

def generate_gst():
    """Generate fake GST number."""
    state = str(random.randint(1, 37)).zfill(2)
    pan = ''.join(random.choices(string.ascii_uppercase, k=5))
    digits = ''.join(random.choices(string.digits, k=4))
    entity = random.choice(string.ascii_uppercase)
    return f"{state}{pan}{digits}{entity}1Z{random.choice(string.ascii_uppercase)}"

def generate_triplet(idx, include_fraud=False):
    """Generate a matching LR-POD-Invoice triplet."""
    shipment_id = generate_shipment_id()
    
    # Base amount with some variation
    base_amount = random.randint(10000, 100000)
    
    # Dates
    lr_date = datetime.now() - timedelta(days=random.randint(5, 30))
    pod_date = lr_date + timedelta(days=random.randint(1, 5))
    invoice_date = pod_date + timedelta(days=random.randint(0, 3))
    
    # Common data
    vendor = random.choice(VENDORS)
    origin = random.choice(CITIES)
    destination = random.choice([c for c in CITIES if c != origin])
    vehicle = random.choice(VEHICLES)
    weight = random.randint(100, 5000)
    gst = generate_gst()
    
    # Fraud variations
    if include_fraud:
        fraud_type = random.choice(["duplicate", "amount", "date"])
        if fraud_type == "amount":
            invoice_amount = base_amount * random.uniform(1.1, 1.5)  # Inflated
        elif fraud_type == "date":
            invoice_date = lr_date - timedelta(days=5)  # Invalid sequence
            invoice_amount = base_amount
        else:
            invoice_amount = base_amount
    else:
        # Normal variance within tolerance
        invoice_amount = base_amount * random.uniform(0.98, 1.02)
    
    return {
        "idx": idx,
        "shipment_id": shipment_id,
        "vendor": vendor,
        "origin": origin,
        "destination": destination,
        "vehicle": vehicle,
        "weight": weight,
        "gst": gst,
        "lr_date": lr_date.strftime("%d-%m-%Y"),
        "pod_date": pod_date.strftime("%d-%m-%Y"),
        "invoice_date": invoice_date.strftime("%d-%m-%Y"),
        "lr_amount": base_amount,
        "invoice_amount": round(invoice_amount, 2),
        "is_fraud": include_fraud,
    }

LR_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; background: white; }
        .header { text-align: center; border-bottom: 3px solid #000; padding-bottom: 15px; margin-bottom: 20px; }
        .title { font-size: 28px; font-weight: bold; }
        .subtitle { font-size: 16px; color: #333; margin-top: 5px; }
        .section { margin: 25px 0; }
        .row { display: flex; margin: 12px 0; font-size: 16px; }
        .label { font-weight: bold; width: 180px; }
        .value { flex: 1; }
        .box { border: 2px solid #333; padding: 15px; margin: 15px 0; background: #fafafa; }
        .amount { font-size: 24px; font-weight: bold; text-align: right; margin-top: 30px; padding: 15px; background: #e8f5e9; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="title">LORRY RECEIPT</div>
        <div class="subtitle">{{ vendor }}</div>
    </div>
    
    <div class="section">
        <div class="row">
            <div class="label">LR Number:</div>
            <div class="value">{{ shipment_id }}</div>
        </div>
        <div class="row">
            <div class="label">Date:</div>
            <div class="value">{{ lr_date }}</div>
        </div>
        <div class="row">
            <div class="label">Vehicle No:</div>
            <div class="value">{{ vehicle }}</div>
        </div>
    </div>
    
    <div class="box">
        <div class="row">
            <div class="label">From:</div>
            <div class="value">{{ origin }}</div>
        </div>
        <div class="row">
            <div class="label">To:</div>
            <div class="value">{{ destination }}</div>
        </div>
    </div>
    
    <div class="section">
        <div class="row">
            <div class="label">Weight (Kg):</div>
            <div class="value">{{ weight }}</div>
        </div>
        <div class="row">
            <div class="label">GST No:</div>
            <div class="value">{{ gst }}</div>
        </div>
    </div>
    
    <div class="amount">
        Total: Rs. {{ lr_amount }}
    </div>
</body>
</html>
"""

POD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; background: white; }
        .header { text-align: center; border-bottom: 3px solid #000; padding-bottom: 15px; margin-bottom: 20px; }
        .title { font-size: 28px; font-weight: bold; }
        .section { margin: 25px 0; }
        .row { display: flex; margin: 12px 0; font-size: 16px; }
        .label { font-weight: bold; width: 180px; }
        .value { flex: 1; }
        .signature { border-top: 2px solid #000; width: 250px; margin-top: 60px; text-align: center; padding-top: 10px; font-size: 14px; }
        .stamp { border: 3px solid green; padding: 15px 30px; text-align: center; color: green; font-weight: bold; font-size: 20px; margin-top: 30px; display: inline-block; border-radius: 5px; }
        .stamp-container { text-align: center; }
    </style>
</head>
<body>
    <div class="header">
        <div class="title">PROOF OF DELIVERY</div>
    </div>
    
    <div class="section">
        <div class="row">
            <div class="label">Consignment No:</div>
            <div class="value">{{ shipment_id }}</div>
        </div>
        <div class="row">
            <div class="label">Delivery Date:</div>
            <div class="value">{{ pod_date }}</div>
        </div>
    </div>
    
    <div class="section">
        <div class="row">
            <div class="label">Origin:</div>
            <div class="value">{{ origin }}</div>
        </div>
        <div class="row">
            <div class="label">Destination:</div>
            <div class="value">{{ destination }}</div>
        </div>
        <div class="row">
            <div class="label">Consignee:</div>
            <div class="value">{{ vendor }}</div>
        </div>
    </div>
    
    <div class="section">
        <div class="row">
            <div class="label">Condition:</div>
            <div class="value">Good / Received in proper condition</div>
        </div>
    </div>
    
    <div class="stamp-container">
        <div class="stamp">DELIVERED</div>
    </div>
    
    <div class="signature">
        Receiver's Signature
    </div>
</body>
</html>
"""

INVOICE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; background: white; }
        .header { text-align: center; border-bottom: 3px solid #000; padding-bottom: 15px; margin-bottom: 20px; }
        .title { font-size: 28px; font-weight: bold; }
        .invoice-no { font-size: 20px; margin-top: 10px; color: #333; }
        .section { margin: 25px 0; }
        .row { display: flex; margin: 12px 0; font-size: 16px; }
        .label { font-weight: bold; width: 180px; }
        .value { flex: 1; }
        table { width: 100%; border-collapse: collapse; margin: 25px 0; }
        th, td { border: 2px solid #333; padding: 12px; text-align: left; font-size: 15px; }
        th { background: #e0e0e0; font-weight: bold; }
        .total { font-size: 24px; font-weight: bold; text-align: right; margin-top: 20px; padding: 15px; background: #fff3e0; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="title">TAX INVOICE</div>
        <div class="invoice-no">Invoice No: INV{{ shipment_id[2:] }}</div>
    </div>
    
    <div class="section">
        <div class="row">
            <div class="label">Date:</div>
            <div class="value">{{ invoice_date }}</div>
        </div>
        <div class="row">
            <div class="label">Shipment Ref:</div>
            <div class="value">{{ shipment_id }}</div>
        </div>
        <div class="row">
            <div class="label">GSTIN:</div>
            <div class="value">{{ gst }}</div>
        </div>
    </div>
    
    <div class="section">
        <div class="row">
            <div class="label">Bill To:</div>
            <div class="value">{{ vendor }}</div>
        </div>
        <div class="row">
            <div class="label">Route:</div>
            <div class="value">{{ origin }} to {{ destination }}</div>
        </div>
    </div>
    
    <table>
        <tr>
            <th>Description</th>
            <th>Weight</th>
            <th>Rate</th>
            <th>Amount</th>
        </tr>
        <tr>
            <td>Freight Charges</td>
            <td>{{ weight }} Kg</td>
            <td>Per consignment</td>
            <td>Rs. {{ invoice_amount }}</td>
        </tr>
    </table>
    
    <div class="total">
        Grand Total: Rs. {{ invoice_amount }}
    </div>
</body>
</html>
"""

def generate_documents(output_dir, count=50, fraud_count=5):
    """Generate document triplets as HTML files."""
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "lr"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "pod"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "invoice"), exist_ok=True)
    
    lr_template = Template(LR_TEMPLATE)
    pod_template = Template(POD_TEMPLATE)
    invoice_template = Template(INVOICE_TEMPLATE)
    
    triplets = []
    
    # Generate normal triplets
    for i in range(count - fraud_count):
        triplet = generate_triplet(i)
        triplets.append(triplet)
    
    # Generate fraud triplets
    for i in range(fraud_count):
        triplet = generate_triplet(count - fraud_count + i, include_fraud=True)
        triplets.append(triplet)
    
    print(f"Generating {len(triplets)} document triplets...")
    
    for triplet in triplets:
        idx = triplet["idx"]
        
        # LR
        lr_html = lr_template.render(**triplet)
        with open(os.path.join(output_dir, "lr", f"lr_{idx:03d}.html"), "w") as f:
            f.write(lr_html)
        
        # POD
        pod_html = pod_template.render(**triplet)
        with open(os.path.join(output_dir, "pod", f"pod_{idx:03d}.html"), "w") as f:
            f.write(pod_html)
        
        # Invoice
        invoice_html = invoice_template.render(**triplet)
        with open(os.path.join(output_dir, "invoice", f"invoice_{idx:03d}.html"), "w") as f:
            f.write(invoice_html)
    
    print(f"\nGenerated {len(triplets)} document triplets")
    print(f"  - Normal: {count - fraud_count}")
    print(f"  - Fraud cases: {fraud_count}")
    print(f"Output directory: {output_dir}")
    
    return triplets

if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(__file__), "generated")
    generate_documents(output_dir, count=50, fraud_count=5)
