import json
import os
from typing import Dict, List

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

from app.config import get_settings

settings = get_settings()


class ActiveLearner:
    """Learns a match-calibration model from approve/reject actions."""

    DATA_PATH = "active_learning_samples.jsonl"
    MODEL_PATH = "active_learning_model.joblib"

    def __init__(self):
        self.model = None
        self._load_model()

    def predict(self, features: Dict) -> float:
        x = np.array([self._to_vector(features)])
        if self.model is None:
            # Fallback: weighted baseline from existing confidence components
            return float(
                0.35 * features.get("match_score", 0)
                + 0.20 * features.get("ocr_accuracy", 0)
                + 0.25 * features.get("ner_confidence", 0)
                + 0.20 * features.get("rule_pass_score", 0)
            )
        return float(self.model.predict_proba(x)[0][1])

    def add_feedback(self, features: Dict, label: int) -> None:
        row = {"features": features, "label": int(label)}
        try:
            with open(self.DATA_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
        except Exception:
            return
        self._retrain_if_possible()

    def _retrain_if_possible(self) -> None:
        if not os.path.exists(self.DATA_PATH):
            return
        xs: List[List[float]] = []
        ys: List[int] = []
        try:
            with open(self.DATA_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    xs.append(self._to_vector(row["features"]))
                    ys.append(int(row["label"]))
        except Exception:
            return

        if len(xs) < settings.active_learning_min_samples:
            return
        if len(set(ys)) < 2:
            return

        model = LogisticRegression(max_iter=300)
        model.fit(np.array(xs), np.array(ys))
        self.model = model
        try:
            joblib.dump(model, self.MODEL_PATH)
        except Exception:
            pass

    def _load_model(self) -> None:
        if not os.path.exists(self.MODEL_PATH):
            return
        try:
            self.model = joblib.load(self.MODEL_PATH)
        except Exception:
            self.model = None

    def _to_vector(self, features: Dict) -> List[float]:
        return [
            float(features.get("match_score", 0)),
            float(features.get("ocr_accuracy", 0)),
            float(features.get("ner_confidence", 0)),
            float(features.get("rule_pass_score", 0)),
            float(features.get("embedding_similarity", 0)),
            float(features.get("contrastive_score", 0)),
            float(features.get("graph_score", 0)),
        ]
