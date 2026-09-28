"""
VeriCampus AI — Document Quality Analyzer (Inference Engine)
Provides runtime document quality assessment for uploaded files and bytes.
"""
from pathlib import Path
from typing import Optional, Union, Any
import logging

from .config import (
    DEFAULT_MODEL_PATH,
    MODEL_VERSION,
)
from .schemas import (
    QualityAssessment,
    QualityFeatures,
)
from .features import extract_quality_features
from .scorer import evaluate_features_rule_based, map_score_to_assessment
from .model import QualityGateClassifier

logger = logging.getLogger("vericampus.document_quality")


class DocumentQualityAnalyzer:
    """
    Inference interface for Stage 1 Document Quality Gate.
    Analyzes physical/optical quality and generates explainable machine-readable reasons.
    """

    _cached_model: Optional[QualityGateClassifier] = None
    _model_load_attempted: bool = False

    @classmethod
    def get_model(cls, model_path: Optional[Union[str, Path]] = None) -> Optional[QualityGateClassifier]:
        """Loads and caches the ML classifier pipeline, or returns None if not available."""
        if model_path is None and cls._cached_model is not None:
            return cls._cached_model

        target_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        if not target_path.exists():
            return None

        try:
            model = QualityGateClassifier.load(str(target_path))
            if model_path is None:
                cls._cached_model = model
            return model
        except Exception as e:
            logger.warning(f"Failed to load quality model from {target_path}: {e}. Using rule fallback.")
            return None

    @classmethod
    def analyze(
        cls,
        document_input: Union[str, Path, bytes, Any],
        ocr_result: Optional[Any] = None,
        model_path: Optional[Union[str, Path]] = None,
    ) -> QualityAssessment:
        """
        Main entry point for document quality analysis.

        Args:
            document_input: Path to physical document, image bytes, PIL Image, or numpy array.
            ocr_result: Optional OCR result (from BaseOCRProvider or extraction engine).
            model_path: Optional override for trained model artifact.

        Returns:
            QualityAssessment containing quality_score, quality_level,
            quality_gate_status, reasons list, and extracted features.
        """
        # 1. Feature extraction with robust error handling
        try:
            features: QualityFeatures = extract_quality_features(document_input, ocr_result=ocr_result)
        except Exception as e:
            logger.error(f"Error extracting features: {e}. Returning UNREADABLE assessment.")
            return map_score_to_assessment(
                score=10.0,
                reasons=[f"Unable to read document image file: {str(e)}"],
                features_dict={},
                model_version=MODEL_VERSION,
                is_fallback=True,
            )

        features_dict = features.model_dump()

        # 2. Heuristic rule analysis (produces primary actionable reasons and baseline score)
        rule_score, rule_reasons = evaluate_features_rule_based(features)

        # 3. ML Model prediction (if model artifact exists)
        model = cls.get_model(model_path)
        is_fallback = model is None

        if model is not None:
            try:
                pred_label, class_probs, ml_score = model.predict_single(features_dict)
                # Combine ML score and rule score (balanced blend)
                # If either detected severe issues (< 50), preserve conservative caution
                if rule_score < 50.0 or ml_score < 50.0:
                    combined_score = min(rule_score, ml_score)
                else:
                    combined_score = round(0.60 * rule_score + 0.40 * ml_score, 2)
            except Exception as e:
                logger.warning(f"Model prediction failed: {e}. Reverting to rule score.")
                combined_score = rule_score
                is_fallback = True
        else:
            combined_score = rule_score

        # 4. Map final composite score to QualityAssessment
        assessment = map_score_to_assessment(
            score=combined_score,
            reasons=rule_reasons,
            features_dict=features_dict,
            model_version=MODEL_VERSION,
            is_fallback=is_fallback,
        )
        return assessment
