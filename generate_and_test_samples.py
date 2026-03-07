import os
import requests
import time
from PIL import Image, ImageDraw, ImageFont

def create_image(filename, lines, width=800, height=1000):
    # Create a white image
    img = Image.new('RGB', (width, height), color='white')
    d = ImageDraw.Draw(img)
    
    # Try to load a generic font, otherwise default
    try:
        font = ImageFont.truetype("arial.ttf", 24)
        title_font = ImageFont.truetype("arial.ttf", 36)
    except IOError:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    y_text = 40
    for i, line in enumerate(lines):
        f = title_font if i == 0 else font
        d.text((40, y_text), line, fill=(0, 0, 0), font=f)
        y_text += 40 if i == 0 else 30
        
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    img.save(filename)
    print(f"Generated {filename}")

def generate_samples():
    invoice_lines = [
        "INVOICE",
        "Invoice Number: INV-2026-9912",
        "Date: 2026-03-08",
        "Party Name: Global Freight Ltd",
        "Amount: 5500.00",
        "Origin: Mumbai",
        "Destination: Delhi",
        "Bill To: LogisticsNow India",
        "--------------------------------------------------",
        "Item: Transport Services",
        "Qty: 1",
        "Rate: 5000",
        "--------------------------------------------------"
    ]
    
    lr_lines = [
        "LORRY RECEIPT (LR)",
        "LR Number: LR-9912-MUM-DEL",
        "Date: 2026-03-06",
        "Carrier: Global Freight Ltd",
        "Consignor: Tech Parts Inc (Mumbai)",
        "Consignee: Electronics Hub (Delhi)",
        "--------------------------------------------------",
        "Description of Goods: Computer Hardware",
        "Standard Weight: 1450 kg",
        "Number of Articles: 45 Cartons",
        "Amount: 5500.00",
        "Origin: Mumbai",
        "Destination: Delhi"
    ]
    
    pod_lines = [
        "PROOF OF DELIVERY (POD)",
        "LR Number: LR-9912-MUM-DEL",
        "Delivery Date: 2026-03-08",
        "Receiver Name: Electronics Hub",
        "--------------------------------------------------",
        "Delivery Status: DELIVERED IN GOOD CONDITION",
        "Shortages/Damages: None",
        "Time of Delivery: 14:30 PM"
    ]

    create_image("sample_data/synthetic/invoice_1.png", invoice_lines)
    create_image("sample_data/synthetic/lr_1.png", lr_lines)
    create_image("sample_data/synthetic/pod_1.png", pod_lines)

def upload_and_test():
    url = "http://localhost:8000/api/documents/upload"
    
    docs = [
        ("sample_data/synthetic/invoice_1.png", "INVOICE"),
        ("sample_data/synthetic/lr_1.png", "LR"),
        ("sample_data/synthetic/pod_1.png", "POD")
    ]
    
    doc_ids = []
    
    for filepath, doc_type in docs:
        print(f"\nUploading {doc_type} from {filepath}...")
        with open(filepath, 'rb') as f:
            files = {'file': (os.path.basename(filepath), f, 'image/png')}
            params = {'doc_type': doc_type}
            response = requests.post(url, files=files, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"Success! Document ID: {data['id']}, Status: {data['status']}")
                doc_ids.append(data['id'])
            else:
                print(f"Failed to upload: {response.text}")
                
    # Now let's try to trigger matching
    print("\nTriggering Triplet Matching...")
    match_url = "http://localhost:8000/api/triplets/match"
    res = requests.post(match_url)
    if res.status_code == 200:
        match_data = res.json()
        print(f"Match Response: {match_data}")
    else:
        print(f"Match Failed: {res.text}")

if __name__ == "__main__":
    print("Generating synthetic sample documents...")
    generate_samples()
    print("\nWaiting 2 seconds before uploading to backend...")
    time.sleep(2)
    upload_and_test()
    print("\nTest completed.")
