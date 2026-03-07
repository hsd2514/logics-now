import hashlib
import json
from typing import Dict, List

import numpy as np

from app.config import get_settings

settings = get_settings()


class EmbeddingService:
    """Deterministic text/entity embedding for similarity scoring."""

    def __init__(self, dim: int | None = None):
        self.dim = dim or settings.embedding_dim

    def embed_document(self, text: str, entities: Dict) -> List[float]:
        payload = f"{text or ''} {json.dumps(entities or {}, sort_keys=True)}".lower()
        if not payload.strip():
            return [0.0] * self.dim

        vec = np.zeros(self.dim, dtype=np.float32)
        for token in payload.split():
            idx = self._hash_idx(token)
            vec[idx] += 1.0

        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec = vec / norm
        return vec.round(6).tolist()

    @staticmethod
    def cosine_similarity(a: List[float] | None, b: List[float] | None) -> float:
        if not a or not b:
            return 0.0
        va = np.array(a, dtype=np.float32)
        vb = np.array(b, dtype=np.float32)
        denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
        if denom == 0:
            return 0.0
        return float(np.dot(va, vb) / denom)

    def _hash_idx(self, token: str) -> int:
        digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
        return int(digest, 16) % self.dim
