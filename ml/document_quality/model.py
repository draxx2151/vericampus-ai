"""
VeriCampus AI — Document Quality Classifier Model
Lightweight classical ML baseline (RandomForestClassifier) using scikit-learn.
"""
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib

from .config import (
    QUALITY_FEATURE_NAMES,
    DEFAULT_N_ESTIMATORS,
    DEFAULT_MAX_DEPTH,
    DEFAULT_RANDOM_STATE,
    MODEL_VERSION,
)


class QualityGateClassifier:
    """
    RandomForest pipeline for 4-class document quality classification:
    HIGH, MEDIUM, LOW, UNREADABLE.
    """

    def __init__(
        self,
        n_estimators: int = DEFAULT_N_ESTIMATORS,
        max_depth: int = DEFAULT_MAX_DEPTH,
        random_state: int = DEFAULT_RANDOM_STATE,
    ):
        self.feature_names = list(QUALITY_FEATURE_NAMES)
        self.classes_ = ["HIGH", "MEDIUM", "LOW", "UNREADABLE"]
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                class_weight="balanced",
                random_state=random_state,
            )),
        ])
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: List[str]):
        """Fits the pipeline on feature matrix X and target labels y."""
        self.pipeline.fit(X, y)
        self.classes_ = list(self.pipeline.named_steps["rf"].classes_)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predicts class labels for feature matrix X."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict.")
        return self.pipeline.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predicts class probabilities for feature matrix X."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict_proba.")
        return self.pipeline.predict_proba(X)

    def predict_single(self, features_dict: Dict[str, Any]) -> Tuple[str, Dict[str, float], float]:
        """
        Predicts quality label and estimated continuous score for a single sample.
        Returns: (predicted_class, class_probabilities, estimated_score)
        """
        row = [float(features_dict.get(fname, 0.0)) for fname in self.feature_names]
        X = np.array([row], dtype=np.float32)
        probs = self.predict_proba(X)[0]
        prob_dict = {cls_name: float(probs[i]) for i, cls_name in enumerate(self.classes_)}
        pred_label = self.classes_[int(np.argmax(probs))]

        # Continuous score approximation from class probabilities:
        # HIGH -> 92, MEDIUM -> 77, LOW -> 55, UNREADABLE -> 20
        class_weights = {
            "HIGH": 92.0,
            "MEDIUM": 77.0,
            "ACCEPTABLE": 77.0,
            "LOW": 55.0,
            "UNREADABLE": 20.0,
        }
        est_score = sum(prob_dict.get(c, 0.0) * class_weights.get(c, 50.0) for c in prob_dict)
        return pred_label, prob_dict, round(est_score, 2)

    def save(self, filepath: str):
        """Saves model pipeline to disk."""
        data = {
            "pipeline": self.pipeline,
            "feature_names": self.feature_names,
            "classes_": self.classes_,
            "model_version": MODEL_VERSION,
        }
        joblib.dump(data, filepath)

    @classmethod
    def load(cls, filepath: str) -> "QualityGateClassifier":
        """Loads fitted model pipeline from disk."""
        data = joblib.load(filepath)
        instance = cls()
        instance.pipeline = data["pipeline"]
        instance.feature_names = data.get("feature_names", list(QUALITY_FEATURE_NAMES))
        instance.classes_ = data.get("classes_", ["HIGH", "MEDIUM", "LOW", "UNREADABLE"])
        instance.is_fitted = True
        return instance
