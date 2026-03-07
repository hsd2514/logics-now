import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ExtractedEntity:
    value: str
    confidence: float
    source_text: str
    position: Optional[Tuple[float, float, float, float]] = None  # x, y, w, h

class EntityExtractor:
    """Stage 3: Extract entities from OCR text - SHIPMENT_ID, AMOUNT, DATE, etc."""
    
    def __init__(self):
        self.patterns = {
            'shipment_id': [
                # Require at least one digit in the captured ID so we don't grab labels like "Number" or "Invoice"
                r'(?:LR|POD|INV|INVOICE|SHIPMENT)[\s#:.-]*([A-Z0-9]*\d[A-Z0-9]{4,14})',
                r'(?:Consignment|CN|Docket)[\s#:.-]*([A-Z0-9]*\d[A-Z0-9]{4,14})',
                r'(?:AWB|Airway\s*Bill)[\s#:.-]*([A-Z0-9]*\d[A-Z0-9]{6,14})',
            ],
            'amount': [
                r'(?:Total|Grand\s*Total|Amount|Net\s*Amount|Freight)[\s:₹Rs.]*([0-9,]+\.?[0-9]*)',
                r'₹\s*([0-9,]+\.?[0-9]*)',
                r'Rs\.?\s*([0-9,]+\.?[0-9]*)',
                r'INR\s*([0-9,]+\.?[0-9]*)',
            ],
            'date': [
                r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',
                r'(?:Date|Dated)[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            ],
            'vehicle_number': [
                r'([A-Z]{2}[\s-]?\d{1,2}[\s-]?[A-Z]{1,3}[\s-]?\d{4})',
                r'(?:Vehicle|Truck|Lorry)[\s#:.-]*([A-Z0-9\s-]{8,12})',
            ],
            'gst_number': [
                r'(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})',
                r'(?:GST|GSTIN)[\s#:.-]*(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})',
            ],
            'party_name': [
                r'(?:Consignor|Shipper|From)[\s:]*([A-Za-z\s&.]+?)(?:\n|,|$)',
                r'(?:Consignee|Receiver|To)[\s:]*([A-Za-z\s&.]+?)(?:\n|,|$)',
                r'(?:Bill\s*To|Billed\s*To)[\s:]*([A-Za-z\s&.]+?)(?:\n|,|$)',
            ],
            'weight': [
                r'(?:Weight|Wt|Gross)[\s:]*([0-9,]+\.?[0-9]*)\s*(?:kg|KG|Kg|MT|mt)',
                r'([0-9,]+\.?[0-9]*)\s*(?:kg|KG|Kg|MT|mt)',
            ],
            'origin': [
                r'(?:From|Origin|Pickup)[\s:]*([A-Za-z\s]+?)(?:\n|,|to|$)',
            ],
            'destination': [
                r'(?:To|Destination|Delivery)[\s:]*([A-Za-z\s]+?)(?:\n|,|$)',
            ],
        }
    
    def extract(self, text: str, text_blocks: List[Dict] = None) -> Tuple[Dict, float]:
        """
        Extract all entities from text.
        Returns: (entities_dict, overall_confidence)
        """
        entities = {}
        confidences = []
        
        # Clean text
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = re.sub(r'\s+', ' ', text)
        
        for entity_type, patterns in self.patterns.items():
            result = self._extract_entity(text, patterns, text_blocks)
            if result:
                entities[entity_type] = result.value
                confidences.append(result.confidence)
        
        # Post-process amounts
        if 'amount' in entities:
            entities['amount'] = self._parse_amount(entities['amount'])
        
        # Post-process dates
        if 'date' in entities:
            entities['date'] = self._parse_date(entities['date'])
        
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return entities, overall_confidence
    
    def _extract_entity(self, text: str, patterns: List[str], text_blocks: List[Dict] = None) -> Optional[ExtractedEntity]:
        """Extract a single entity using multiple patterns."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                
                # Calculate confidence based on pattern specificity
                confidence = 0.85 if len(patterns) > 1 else 0.90
                
                # Find position if text_blocks provided
                position = None
                if text_blocks:
                    position = self._find_position(value, text_blocks)
                
                return ExtractedEntity(
                    value=value,
                    confidence=confidence,
                    source_text=match.group(0),
                    position=position
                )
        
        return None
    
    def _find_position(self, value: str, text_blocks: List[Dict]) -> Optional[Tuple[float, float, float, float]]:
        """Find the position of extracted value in text blocks."""
        value_lower = value.lower()
        for block in text_blocks:
            if value_lower in block['text'].lower():
                return (block['x'], block['y'], block['width'], block['height'])
        return None
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string to float."""
        try:
            cleaned = re.sub(r'[^\d.]', '', amount_str.replace(',', ''))
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0
    
    def _parse_date(self, date_str: str) -> str:
        """Normalize date string to ISO format."""
        date_formats = [
            '%d-%m-%Y', '%d/%m/%Y', '%d-%m-%y', '%d/%m/%y',
            '%d %b %Y', '%d %B %Y', '%d %b %y',
            '%Y-%m-%d', '%m/%d/%Y'
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except:
                continue
        
        return date_str  # Return original if parsing fails
    
    def extract_for_document_type(self, text: str, doc_type: str) -> Tuple[Dict, float]:
        """Extract entities specific to document type."""
        entities, confidence = self.extract(text)
        
        # Add document-type specific extraction
        if doc_type == 'LR':
            # LR specific: look for booking date, expected delivery
            pass
        elif doc_type == 'POD':
            # POD specific: look for delivery date, receiver signature
            pass
        elif doc_type == 'INVOICE':
            # Invoice specific: look for GST, tax breakdown
            pass
        
        return entities, confidence
