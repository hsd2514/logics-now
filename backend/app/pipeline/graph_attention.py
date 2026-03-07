from typing import Dict, List, Tuple

import numpy as np


class GraphAttentionScorer:
    """Lightweight GAT-style scorer using shared-entity edge attention."""

    def __init__(self, docs: List[Dict]):
        self.edge_weights: Dict[Tuple[str, str], float] = {}
        self._build_edges(docs)

    def score_triplet(self, lr_id: str, pod_id: str, inv_id: str) -> float:
        pairs = [(lr_id, pod_id), (lr_id, inv_id), (pod_id, inv_id)]
        scores = [self.edge_weights.get(self._pair_key(a, b), 0.0) for a, b in pairs]
        if not scores:
            return 0.0
        logits = np.array(scores, dtype=np.float32)
        exp = np.exp(logits - np.max(logits))
        attn = exp / (exp.sum() if exp.sum() > 0 else 1.0)
        return float(np.dot(attn, logits))

    def _build_edges(self, docs: List[Dict]) -> None:
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                a = docs[i]
                b = docs[j]
                w = self._shared_entity_score(a.get("entities", {}), b.get("entities", {}))
                if w > 0:
                    self.edge_weights[self._pair_key(a["id"], b["id"])] = w

    def _shared_entity_score(self, a: Dict, b: Dict) -> float:
        key_fields = ["shipment_id", "party_name", "origin", "destination", "vehicle_number"]
        total = 0.0
        seen = 0
        for field in key_fields:
            av = str(a.get(field, "")).strip().lower()
            bv = str(b.get(field, "")).strip().lower()
            if not av or not bv:
                continue
            seen += 1
            total += 1.0 if av == bv else self._token_overlap(av, bv)
        if seen == 0:
            return 0.0
        return total / seen

    def _token_overlap(self, a: str, b: str) -> float:
        sa = set(a.split())
        sb = set(b.split())
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    def _pair_key(self, a: str, b: str) -> Tuple[str, str]:
        return tuple(sorted((a, b)))
