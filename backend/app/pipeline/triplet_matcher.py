from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from difflib import SequenceMatcher

from app.config import get_settings

settings = get_settings()

@dataclass
class MatchResult:
    lr_id: str
    pod_id: str
    invoice_id: str
    match_score: float
    confidence: float
    field_matches: Dict[str, Dict]
    attention_map: List[Dict]

class TripletMatcher:
    """Stage 4: Match LR-POD-Invoice triplets with confidence scoring"""
    
    def __init__(self):
        # Relative importance of each field in overall match_score.
        self.field_weights = {
            'shipment_id': 0.35,
            'amount': 0.25,
            'date': 0.15,
            'party_name': 0.10,
            'origin': 0.05,
            'destination': 0.05,
            'vehicle_number': 0.05,
        }
    
    def match_triplet(
        self, 
        lr_entities: Dict, 
        pod_entities: Dict, 
        invoice_entities: Dict,
        lr_blocks: List[Dict] = None,
        pod_blocks: List[Dict] = None,
        invoice_blocks: List[Dict] = None
    ) -> Tuple[float, float, Dict, List[Dict]]:
        """
        Match three documents and return scores.
        Returns: (match_score, confidence, field_matches, attention_map)
        """
        field_matches = {}
        attention_map = []
        total_weight = 0
        weighted_score = 0
        
        for field, weight in self.field_weights.items():
            lr_val = lr_entities.get(field)
            pod_val = pod_entities.get(field)
            inv_val = invoice_entities.get(field)
            
            if lr_val or pod_val or inv_val:
                match_info = self._compare_field(field, lr_val, pod_val, inv_val)
                field_matches[field] = match_info
                
                weighted_score += match_info['score'] * weight
                total_weight += weight
                
                # Build attention map for heatmap visualization
                if match_info['score'] > 0.5:
                    attention_map.extend(
                        self._build_attention_regions(field, match_info, lr_blocks, pod_blocks, invoice_blocks)
                    )
        
        match_score = weighted_score / total_weight if total_weight > 0 else 0
        
        # Confidence based on how many fields were matched
        fields_matched = sum(1 for f in field_matches.values() if f['score'] > 0.7)
        confidence = min(
            settings.confidence_base +
            (fields_matched / len(self.field_weights)) * settings.confidence_range,
            1.0
        )
        
        return match_score, confidence, field_matches, attention_map
    
    def _compare_field(self, field: str, lr_val, pod_val, inv_val) -> Dict:
        """Compare a field across all three documents."""
        values = [v for v in [lr_val, pod_val, inv_val] if v is not None]
        
        if len(values) < 2:
            return {'score': 0.5, 'matched': False, 'values': {'lr': lr_val, 'pod': pod_val, 'invoice': inv_val}}
        
        if field == 'shipment_id':
            score = self._exact_match_score(values)
        elif field == 'amount':
            score = self._numeric_match_score(values, tolerance=settings.amount_tolerance)
        elif field == 'date':
            score = self._date_match_score(lr_val, pod_val, inv_val)
        else:
            score = self._fuzzy_match_score(values)
        
        return {
            'score': score,
            'matched': score > 0.7,
            'values': {'lr': lr_val, 'pod': pod_val, 'invoice': inv_val}
        }
    
    def _exact_match_score(self, values: List) -> float:
        """Score for exact string match."""
        if len(values) < 2:
            return 0.5
        
        normalized = [str(v).strip().upper() for v in values]
        if all(v == normalized[0] for v in normalized):
            return 1.0
        
        # Partial match
        max_similarity = 0
        for i in range(len(normalized)):
            for j in range(i + 1, len(normalized)):
                sim = SequenceMatcher(None, normalized[i], normalized[j]).ratio()
                max_similarity = max(max_similarity, sim)
        
        return max_similarity
    
    def _numeric_match_score(self, values: List, tolerance: float) -> float:
        """Score for numeric match with tolerance."""
        try:
            nums = [float(v) for v in values if v]
            if len(nums) < 2:
                return 0.5
            
            max_val = max(nums)
            min_val = min(nums)
            
            if max_val == 0:
                return 1.0 if min_val == 0 else 0.0
            
            variance = (max_val - min_val) / max_val
            
            if variance <= tolerance:
                return 1.0
            elif variance <= tolerance * 2:
                return 0.8
            elif variance <= tolerance * 5:
                return 0.5
            else:
                return 0.2
        except:
            return 0.0
    
    def _date_match_score(self, lr_date, pod_date, inv_date) -> float:
        """Score for date sequence validation: LR <= POD <= Invoice."""
        dates = []
        for d in [lr_date, pod_date, inv_date]:
            if d:
                dates.append(d)
        
        if len(dates) < 2:
            return 0.5
        
        # Check if dates are in valid sequence
        try:
            from datetime import datetime
            parsed = []
            for d in [lr_date, pod_date, inv_date]:
                if d:
                    parsed.append(datetime.strptime(d, '%Y-%m-%d'))
                else:
                    parsed.append(None)
            
            # LR should be <= POD <= Invoice
            valid = True
            if parsed[0] and parsed[1] and parsed[0] > parsed[1]:
                valid = False
            if parsed[1] and parsed[2] and parsed[1] > parsed[2]:
                valid = False
            if parsed[0] and parsed[2] and parsed[0] > parsed[2]:
                valid = False
            
            return settings.date_valid_score if valid else settings.date_invalid_score
        except:
            return 0.5
    
    def _fuzzy_match_score(self, values: List) -> float:
        """Score for fuzzy string matching."""
        if len(values) < 2:
            return 0.5
        
        normalized = [str(v).strip().lower() for v in values]
        
        total_sim = 0
        pairs = 0
        for i in range(len(normalized)):
            for j in range(i + 1, len(normalized)):
                sim = SequenceMatcher(None, normalized[i], normalized[j]).ratio()
                total_sim += sim
                pairs += 1
        
        return total_sim / pairs if pairs > 0 else 0.5
    
    def _build_attention_regions(
        self, field: str, match_info: Dict,
        lr_blocks: List[Dict], pod_blocks: List[Dict], invoice_blocks: List[Dict]
    ) -> List[Dict]:
        """Build attention regions with normalised coordinates for heatmap."""
        regions = []
        score = match_info['score']

        for doc_type, blocks, value in [
            ('LR', lr_blocks, match_info['values'].get('lr')),
            ('POD', pod_blocks, match_info['values'].get('pod')),
            ('INVOICE', invoice_blocks, match_info['values'].get('invoice'))
        ]:
            if not (blocks and value):
                continue

            position = self._find_value_position(str(value), blocks)
            if not position:
                continue

            px, py, pw, ph = position

            # Compute real document bounding box from all text blocks
            doc_w, doc_h = self._compute_doc_dimensions(blocks)

            # Normalise to [0, 1] — safe even if doc_w/h are 0
            x_norm = (px / doc_w) if doc_w > 0 else 0.0
            y_norm = (py / doc_h) if doc_h > 0 else 0.0
            w_norm = (pw / doc_w) if doc_w > 0 else 0.0
            h_norm = (ph / doc_h) if doc_h > 0 else 0.0

            regions.append({
                'document_type': doc_type,
                'field': field,
                # Raw pixel coords (kept for debugging)
                'x': px,
                'y': py,
                'width': pw,
                'height': ph,
                # Real document dimensions
                'doc_width': doc_w,
                'doc_height': doc_h,
                # Normalised coords — use these in the frontend
                'x_norm': round(x_norm, 4),
                'y_norm': round(y_norm, 4),
                'w_norm': round(max(w_norm, 0.02), 4),  # min 2% so tiny words visible
                'h_norm': round(max(h_norm, 0.02), 4),
                'score': score,
            })

        return regions

    
    def _find_value_position(self, value: str, blocks: List[Dict]) -> Optional[Tuple]:
        """Find position of value in text blocks."""
        value_lower = value.lower()
        for block in blocks:
            if value_lower in block.get('text', '').lower():
                return (block['x'], block['y'], block['width'], block['height'])
        return None

    def _compute_doc_dimensions(self, blocks: List[Dict]) -> Tuple[float, float]:
        """Compute document canvas size from the bounding box of all OCR text blocks."""
        if not blocks:
            return 0.0, 0.0
        max_x = max((b['x'] + b.get('width', 0)) for b in blocks)
        max_y = max((b['y'] + b.get('height', 0)) for b in blocks)
        return float(max_x), float(max_y)

    def find_best_matches(
        self, 
        lr_docs: List[Dict], 
        pod_docs: List[Dict], 
        invoice_docs: List[Dict]
    ) -> List[MatchResult]:
        """Find best triplet matches from document pools."""
        matches = []
        
        for lr in lr_docs:
            for pod in pod_docs:
                for inv in invoice_docs:
                    score, conf, fields, attention = self.match_triplet(
                        lr.get('entities', {}),
                        pod.get('entities', {}),
                        inv.get('entities', {}),
                        lr.get('text_blocks'),
                        pod.get('text_blocks'),
                        inv.get('text_blocks')
                    )
                    
                    if score > settings.min_match_score:  # configurable minimum threshold
                        matches.append(MatchResult(
                            lr_id=lr['id'],
                            pod_id=pod['id'],
                            invoice_id=inv['id'],
                            match_score=score,
                            confidence=conf,
                            field_matches=fields,
                            attention_map=attention
                        ))
        
        # Sort by score and return best non-overlapping matches
        matches.sort(key=lambda x: x.match_score, reverse=True)
        return self._select_best_non_overlapping(matches)
    
    def _select_best_non_overlapping(self, matches: List[MatchResult]) -> List[MatchResult]:
        """Select best matches ensuring each document is used only once."""
        selected = []
        used_docs = set()
        
        for match in matches:
            doc_ids = {match.lr_id, match.pod_id, match.invoice_id}
            if not doc_ids & used_docs:
                selected.append(match)
                used_docs.update(doc_ids)
        
        return selected
