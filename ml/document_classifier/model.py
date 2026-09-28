"""
VeriCampus AI — Document Classifier ML Model Pipeline
Wraps scikit-learn RandomForestClassifier with StandardScaler for multi-class document classification.
"""
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from .config import TARGET_CLASSES, MODEL_VERSION, DEFAULT_MODEL_PATH
from .schemas import ClassificationAlternative


class DocumentClassifierPipeline:
    """
    Random Forest multi-class document classification pipeline.
    Produces well-calibrated class probability distributions across all target classes.
    """

    def __init__(
        self,
        feature_names: Optional[List[str]] = None,
        classes: Optional[List[str]] = None,
    ):
        self.feature_names = feature_names or []
        self.classes_ = classes or TARGET_CLASSES
        self.scaler = StandardScaler()
        self.clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_split=3,
            class_weight="balanced",
            random_state=42,
        )
        self.is_fitted = False

    def _features_dict_to_array(self, features_dict: Dict[str, float]) -> np.ndarray:
        if not self.feature_names:
            self.feature_names = sorted(list(features_dict.keys()))
        row = [features_dict.get(k, 0.0) for k in self.feature_names]
        return np.array(row, dtype=np.float32).reshape(1, -1)

    def fit(self, X: np.ndarray, y: List[str], feature_names: List[str]):
        """Fits the scaler and random forest classifier on training data."""
        self.feature_names = list(feature_names)
        self.classes_ = sorted(list(set(y)))
        
        X_scaled = self.scaler.fit_transform(X)
        self.clf.fit(X_scaled, y)
        self.is_fitted = True

    def predict_single(
        self,
        features_dict: Dict[str, float],
    ) -> Tuple[str, float, List[ClassificationAlternative]]:
        """
        Infers probabilities for a single feature dictionary.
        Returns: (predicted_class, top_confidence, list_of_alternatives)
        """
        if not self.is_fitted:
            raise RuntimeError("DocumentClassifierPipeline is not fitted.")

        X_raw = self._features_dict_to_array(features_dict)
        X_scaled = self.scaler.transform(X_raw)

        probs = self.clf.predict_proba(X_scaled)[0]
        class_prob_map = {self.clf.classes_[i]: float(probs[i]) for i in range(len(self.clf.classes_))}

        # Ensure all target classes are represented even if zero
        for cls_name in TARGET_CLASSES:
            if cls_name not in class_prob_map:
                class_prob_map[cls_name] = 0.0

        sorted_probs = sorted(class_prob_map.items(), key=lambda x: x[1], reverse=True)
        top_class, top_conf = sorted_probs[0]

        alternatives = [
            ClassificationAlternative(document_type=c, confidence=round(p, 3))
            for c, p in sorted_probs
        ]

        return top_class, round(top_conf, 3), alternatives

    def save(self, file_path: Optional[str] = None):
        """Serializes the pipeline artifact to disk."""
        target_path = Path(file_path) if file_path else DEFAULT_MODEL_PATH
        target_path.parent.mkdir(parents=True, exist_ok=True)
        artifact = {
            "model_version": MODEL_VERSION,
            "feature_names": self.feature_names,
            "classes": list(self.clf.classes_),
            "scaler": self.scaler,
            "clf": self.clf,
        }
        joblib.dump(artifact, str(target_path))

    @classmethod
    def load(cls, file_path: Optional[str] = None) -> "DocumentClassifierPipeline":
        """Deserializes the trained pipeline from disk."""
        target_path = Path(file_path) if file_path else DEFAULT_MODEL_PATH
        if not target_path.exists():
            raise FileNotFoundError(f"Model artifact not found at: {target_path}")

        artifact = joblib.load(str(target_path))
        pipeline = cls(
            feature_names=artifact["feature_names"],
            classes=artifact["classes"],
        )
        pipeline.scaler = artifact["scaler"]
        pipeline.clf = artifact["clf"]
        pipeline.is_fitted = True
        return pipeline
