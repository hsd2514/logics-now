from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from difflib import SequenceMatcher

from app.config import get_settings
from app.services.embedding_service import EmbeddingService
from app.pipeline.contrastive_learner import ContrastiveLearner
from app.pipeline.graph_attention import GraphAttentionScorer

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
    embedding_similarity: float = 0.0
    contrastive_score: float = 0.0
    graph_score: float = 0.0

class TripletMatcher:
    """Stage 4: Match LR-POD-Invoice triplets with confidence scoring"""
    
    def __init__(self):
        # Relative importance of each field in overall match_score.
        self.field_weights = {
            'shipment_id': 0.30,
            'amount': 0.20,
            'date': 0.13,
            'party_name': 0.09,
            'origin': 0.04,
            'destination': 0.04,
            'vehicle_number': 0.05,
        }
        self.embedding_service = EmbeddingService()
        self.contrastive_learner = ContrastiveLearner()
        # Backward-compatible attribute expected by issue-14 tests.
        self.embedding_weight = 0.15
    
    def match_triplet(
        self, 
        lr_entities: Dict, 
        pod_entities: Dict, 
        invoice_entities: Dict,
        lr_embedding: Optional[List[float]] = None,
        pod_embedding: Optional[List[float]] = None,
        invoice_embedding: Optional[List[float]] = None,
        graph_score: float = 0.0,
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

        embedding_similarity = self._embedding_triplet_similarity(
            lr_embedding, pod_embedding, invoice_embedding
        )
        contrastive_score = self.contrastive_learner.score_similarity(embedding_similarity)
        field_matches['embedding_similarity'] = {
            'score': embedding_similarity,
            'matched': embedding_similarity > 0.6,
            'values': {'lr': embedding_similarity, 'pod': embedding_similarity, 'invoice': embedding_similarity}
        }
        # Backward-compatible key expected by older tests.
        field_matches['_embedding_similarity'] = field_matches['embedding_similarity']
        if lr_embedding or pod_embedding or invoice_embedding:
            weighted_score += self.embedding_weight * contrastive_score
            total_weight += self.embedding_weight
        
        match_score = weighted_score / total_weight if total_weight > 0 else 0
        # Blend GAT-style graph score with field/contrastive score
        if graph_score > 0:
            match_score = (
                (1.0 - settings.graph_attention_weight) * match_score
                + settings.graph_attention_weight * graph_score
            )
        field_matches['graph_attention'] = {
            'score': graph_score,
            'matched': graph_score > 0.55,
            'values': {'lr': graph_score, 'pod': graph_score, 'invoice': graph_score}
        }
        
        # Confidence based on how many fields were matched
        fields_matched = sum(1 for f in field_matches.values() if f['score'] > 0.7)
        confidence = min(
            settings.confidence_base +
            (fields_matched / (len(self.field_weights) + 1)) * settings.confidence_range,
            1.0
        )
        
        return match_score, confidence, field_matches, attention_map

    def _embedding_triplet_similarity(
        self,
        lr_embedding: Optional[List[float]],
        pod_embedding: Optional[List[float]],
        invoice_embedding: Optional[List[float]],
    ) -> float:
        pairs = []
        if lr_embedding and pod_embedding:
            pairs.append(self.embedding_service.cosine_similarity(lr_embedding, pod_embedding))
        if lr_embedding and invoice_embedding:
            pairs.append(self.embedding_service.cosine_similarity(lr_embedding, invoice_embedding))
        if pod_embedding and invoice_embedding:
            pairs.append(self.embedding_service.cosine_similarity(pod_embedding, invoice_embedding))
        if not pairs:
            return 0.0
        return float(sum(pairs) / len(pairs))
    
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
        
        # Partial match across all available document pairs.
        total_similarity = 0.0
        pair_count = 0
        for i in range(len(normalized)):
            for j in range(i + 1, len(normalized)):
                sim = SequenceMatcher(None, normalized[i], normalized[j]).ratio()
                total_similarity += sim
                pair_count += 1

        if pair_count == 0:
            return 0.0
        return total_similarity / pair_count
    
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
        """Find best triplet matches from document pools using blocking for O(n) optimization."""
        graph_scorer = GraphAttentionScorer(lr_docs + pod_docs + invoice_docs)

        # Build indexes by shipment_id for O(1) lookup
        lr_index = self._build_index(lr_docs, 'shipment_id')
        pod_index = self._build_index(pod_docs, 'shipment_id')
        invoice_index = self._build_index(invoice_docs, 'shipment_id')
        
        matches = []
        processed_combinations = set()
        
        # Strategy 1: Exact shipment_id matches (O(n))
        all_shipment_ids = set(lr_index.keys()) | set(pod_index.keys()) | set(invoice_index.keys())
        
        for shipment_id in all_shipment_ids:
            lrs = lr_index.get(shipment_id, [])
            pods = pod_index.get(shipment_id, [])
            invs = invoice_index.get(shipment_id, [])
            
            # Match all combinations within this block (small groups)
            for lr in lrs:
                for pod in pods:
                    for inv in invs:
                        combo = (lr['id'], pod['id'], inv['id'])
                        if combo in processed_combinations:
                            continue
                        processed_combinations.add(combo)

                        graph_score = graph_scorer.score_triplet(lr['id'], pod['id'], inv['id'])
                        score, conf, fields, attention = self.match_triplet(
                            lr.get('entities', {}),
                            pod.get('entities', {}),
                            inv.get('entities', {}),
                            lr.get('embedding'),
                            pod.get('embedding'),
                            inv.get('embedding'),
                            graph_score,
                            lr.get('text_blocks'),
                            pod.get('text_blocks'),
                            inv.get('text_blocks'),
                        )

                        if score > settings.min_match_score:
                            matches.append(MatchResult(
                                lr_id=lr['id'],
                                pod_id=pod['id'],
                                invoice_id=inv['id'],
                                match_score=score,
                                confidence=conf,
                                field_matches=fields,
                                attention_map=attention,
                                embedding_similarity=fields.get('embedding_similarity', {}).get('score', 0.0),
                                contrastive_score=self.contrastive_learner.score_similarity(
                                    fields.get('embedding_similarity', {}).get('score', 0.0)
                                ),
                                graph_score=graph_score,
                            ))
        
        # Strategy 2: Fuzzy fallback for docs without shipment_id or with minor variations
        unmatched_lrs = [d for d in lr_docs if not d.get('entities', {}).get('shipment_id') or d['id'] not in {m.lr_id for m in matches}]
        unmatched_pods = [d for d in pod_docs if not d.get('entities', {}).get('shipment_id') or d['id'] not in {m.pod_id for m in matches}]
        unmatched_invs = [d for d in invoice_docs if not d.get('entities', {}).get('shipment_id') or d['id'] not in {m.invoice_id for m in matches}]
        
        # Use secondary blocking on vendor name + amount range
        if unmatched_lrs and unmatched_pods and unmatched_invs:
            fuzzy_matches = self._fuzzy_block_matching(
                unmatched_lrs,
                unmatched_pods,
                unmatched_invs,
                processed_combinations,
                graph_scorer,
            )
            matches.extend(fuzzy_matches)
        
        # Sort by score and return best non-overlapping matches
        matches.sort(key=lambda x: x.match_score, reverse=True)
        return self._select_best_non_overlapping(matches)
    
    def _build_index(self, docs: List[Dict], key: str) -> Dict[str, List[Dict]]:
        """Build an index mapping key values to documents."""
        index = {}
        for doc in docs:
            value = doc.get('entities', {}).get(key)
            if value:
                # Normalize the key
                normalized = str(value).strip().upper()
                if normalized not in index:
                    index[normalized] = []
                index[normalized].append(doc)
        return index
    
    def _fuzzy_block_matching(
        self, 
        lrs: List[Dict], 
        pods: List[Dict], 
        invs: List[Dict],
        processed: set,
        graph_scorer: GraphAttentionScorer,
    ) -> List[MatchResult]:
        """Fallback fuzzy matching using vendor/amount blocking."""
        matches = []
        
        # Build secondary index on vendor + amount bucket
        lr_blocks = self._build_secondary_index(lrs)
        pod_blocks = self._build_secondary_index(pods)
        inv_blocks = self._build_secondary_index(invs)
        
        all_blocks = set(lr_blocks.keys()) | set(pod_blocks.keys()) | set(inv_blocks.keys())
        
        for block_key in all_blocks:
            block_lrs = lr_blocks.get(block_key, [])
            block_pods = pod_blocks.get(block_key, [])
            block_invs = inv_blocks.get(block_key, [])
            
            # Only match within small blocks
            for lr in block_lrs:
                for pod in block_pods:
                    for inv in block_invs:
                        combo = (lr['id'], pod['id'], inv['id'])
                        if combo in processed:
                            continue
                        processed.add(combo)

                        graph_score = graph_scorer.score_triplet(lr['id'], pod['id'], inv['id'])
                        score, conf, fields, attention = self.match_triplet(
                            lr.get('entities', {}),
                            pod.get('entities', {}),
                            inv.get('entities', {}),
                            lr.get('embedding'),
                            pod.get('embedding'),
                            inv.get('embedding'),
                            graph_score,
                            lr.get('text_blocks'),
                            pod.get('text_blocks'),
                            inv.get('text_blocks'),
                        )

                        if score > settings.min_match_score:
                            matches.append(MatchResult(
                                lr_id=lr['id'],
                                pod_id=pod['id'],
                                invoice_id=inv['id'],
                                match_score=score,
                                confidence=conf,
                                field_matches=fields,
                                attention_map=attention,
                                embedding_similarity=fields.get('embedding_similarity', {}).get('score', 0.0),
                                contrastive_score=self.contrastive_learner.score_similarity(
                                    fields.get('embedding_similarity', {}).get('score', 0.0)
                                ),
                                graph_score=graph_score,
                            ))
        
        return matches
    
    def _build_secondary_index(self, docs: List[Dict]) -> Dict[str, List[Dict]]:
        """Build secondary index using vendor + amount bucket."""
        index = {}
        for doc in docs:
            entities = doc.get('entities', {})
            vendor = str(entities.get('party_name', '')).strip().upper()[:10]  # First 10 chars
            amount = entities.get('amount', 0)
            
            # Bucket amounts into ranges (0-10k, 10k-50k, 50k-100k, 100k+)
            if amount < 10000:
                bucket = 'A'
            elif amount < 50000:
                bucket = 'B'
            elif amount < 100000:
                bucket = 'C'
            else:
                bucket = 'D'
            
            block_key = f"{vendor}_{bucket}"
            if block_key not in index:
                index[block_key] = []
            index[block_key].append(doc)
        
        return index
    
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
