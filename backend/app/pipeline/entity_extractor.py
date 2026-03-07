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
                # Allow intermediate words like 'Number', 'No', 'Ref', 'ID' between label and value
                r'\b(?:LR|POD|INV|INVOICE|SHIPMENT)\b(?:\s+(?:No|Number|Ref|ID|#))?[\s:.-]*([A-Z0-9]*\d[A-Z0-9]{4,14})',
                r'\b(?:Consignment|CN|Docket)\b(?:\s+(?:No|Number|Ref|ID|#))?[\s:.-]*([A-Z0-9]*\d[A-Z0-9]{4,14})',
                r'\b(?:AWB|Airway\s*Bill)\b(?:\s+(?:No|Number|Ref|ID|#))?[\s:.-]*([A-Z0-9]*\d[A-Z0-9]{6,14})',
            ],
            'amount': [
                # Word boundaries and prioritized labels
                r'\b(?:Total\s*Amount|Net\s*Amount|Met\s*Amount|Grand\s*Total|Amount\s*Acknowledged|Amount|Basic\s*Freight|Freight)\b[\s:₹Rs,.]*([0-9,]+\.[0-9]+|[0-9,]+)',
                r'₹\s*([0-9,]+\.[0-9]+|[0-9,]+)',
                r'Rs\.?\s*([0-9,]+\.[0-9]+|[0-9,]+)',
                r'INR\s*([0-9,]+\.[0-9]+|[0-9,]+)',
            ],
            'date': [
                r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',
                r'\b(?:Date|Dated)\b[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            ],
            'vehicle_number': [
                r'\b([A-Z]{2}[\s-]?\d{1,2}[\s-]?[A-Z]{1,3}[\s-]?\d{4})\b',
                r'\b(?:Vehicle|Truck|Lorry)\b[\s#:.-]*([A-Z0-9\s-]{8,12})',
            ],
            'gst_number': [
                r'\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})\b',
                r'\b(?:GST|GSTIN)\b[\s#:.-]*(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})',
            ],
            'party_name': [
                r'\b(?:Consignor|Shipper|From)\b[\s:]*([A-Za-z\s&.]+?)(?=\s*(?:Consignee|Receiver|To|Date|Amount|LR|INV|Shipment)|[.,\n]|$)',
                r'\b(?:Consignee|Receiver|To)\b[\s:]*([A-Za-z\s&.]+?)(?=\s*(?:Consignor|Shipper|From|Date|Amount|LR|INV|Shipment)|[.,\n]|$)',
                r'\b(?:Bill\s*To|Billed\s*To)\b[\s:]*([A-Za-z\s&.]+?)(?=\s*(?:Consignor|Date|Amount|GST)|[.,\n]|$)',
            ],
            'weight': [
                r'\b(?:Weight|Wt|Gross)\b[\s:]*([0-9,]+\.?[0-9]*)\s*(?:kg|KG|Kg|MT|mt)',
                r'([0-9,]+\.?[0-9]*)\s*(?:kg|KG|Kg|MT|mt)',
            ],
            'origin': [
                # Exclude "days from" or similar prepositions; handle "From." with dot
                r'(?<!days\s)(?<!Validity\s)\b(?:From|Origin|Pickup)\b[\s:.]*([A-Za-z\s]{3,30}?)(?=\s*(?:To|Destination|Delivery|Date|Amount|LR|INV)|[.,\n]|$)',
            ],
            'destination': [
                # Exclude "Bill To", "Ship To", "Sold To" labels
                r'(?<!Bill\s)(?<!Billed\s)(?<!Ship\s)(?<!Sold\s)\b(?:To|Destination|Delivery)\b[\s:.]*([A-Za-z][A-Za-z\s]{2,30}?)(?=\s*(?:From|Origin|Pickup|Date|Amount|LR|INV)|[.,\n]|\s+[A-Z]{3,}|$)',
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
