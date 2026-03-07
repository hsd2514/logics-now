import json
import os

from app.config import get_settings

settings = get_settings()


class ContrastiveLearner:
    """Tracks positive/negative similarity centroids from human feedback."""

    STATE_PATH = "contrastive_state.json"

    def __init__(self):
        self.pos_mean = settings.contrastive_positive_prior
        self.neg_mean = settings.contrastive_negative_prior
        self.pos_count = 0
        self.neg_count = 0
        self._load()

    def score_similarity(self, similarity: float) -> float:
        # Margin-normalized score in [0, 1]
        margin = max(self.pos_mean - self.neg_mean, 1e-3)
        score = (similarity - self.neg_mean) / margin
        return max(0.0, min(1.0, score))

    def update(self, similarity: float, is_positive: bool) -> None:
        if is_positive:
            self.pos_count += 1
            self.pos_mean += (similarity - self.pos_mean) / self.pos_count
        else:
            self.neg_count += 1
            self.neg_mean += (similarity - self.neg_mean) / self.neg_count
        self._save()

    def _load(self) -> None:
        if not os.path.exists(self.STATE_PATH):
            return
        try:
            with open(self.STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.pos_mean = float(data.get("pos_mean", self.pos_mean))
            self.neg_mean = float(data.get("neg_mean", self.neg_mean))
            self.pos_count = int(data.get("pos_count", 0))
            self.neg_count = int(data.get("neg_count", 0))
        except Exception:
            pass

    def _save(self) -> None:
        try:
            with open(self.STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "pos_mean": self.pos_mean,
                        "neg_mean": self.neg_mean,
                        "pos_count": self.pos_count,
                        "neg_count": self.neg_count,
                    },
                    f,
                )
        except Exception:
            pass
