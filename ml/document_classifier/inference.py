"""
VeriCampus AI — Document Classifier (Inference Engine)
Provides runtime document classification, confidence scoring, mismatch detection, and heuristic fallback.
"""
from pathlib import Path
from typing import Optional, Union, Any, Dict
import logging

from .config import DEFAULT_MODEL_PATH, MODEL_VERSION
from .schemas import DocumentClassificationResult
from .features import extract_classification_features
from .scorer import evaluate_features_heuristic, map_prediction_to_result
from .model import DocumentClassifierPipeline

logger = logging.getLogger("vericampus.document_classifier")


class DocumentClassifier:
    """
    Inference interface for Stage 2 Document Classification.
    Determines document type, detects mismatches, and outputs confidence distributions.
    """

    _cached_model: Optional[DocumentClassifierPipeline] = None

    @classmethod
    def get_model(cls, model_path: Optional[Union[str, Path]] = None) -> Optional[DocumentClassifierPipeline]:
        """Loads and caches the ML classifier pipeline, or returns None if unavailable."""
        if model_path is None and cls._cached_model is not None:
            return cls._cached_model

        target_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        if not target_path.exists():
            return None

        try:
            model = DocumentClassifierPipeline.load(str(target_path))
            if model_path is None:
                cls._cached_model = model
            return model
        except Exception as e:
            logger.warning(f"Failed to load classification model from {target_path}: {e}. Using heuristic fallback.")
            return None

    @classmethod
    def predict(
        cls,
        document_input: Union[str, Path, bytes, Any],
        expected_type: Optional[str] = None,
        ocr_result: Optional[Any] = None,
        model_path: Optional[Union[str, Path]] = None,
    ) -> DocumentClassificationResult:
        """
        Main entry point for document type classification.

        Args:
            document_input: Path, bytes, or image representing the uploaded document.
            expected_type: Expected document type required by the scholarship application slot.
            ocr_result: Optional OCR result containing extracted text or tokens.
            model_path: Optional override for trained model artifact.

        Returns:
            DocumentClassificationResult containing predicted_type, confidence,
            classification_status, alternatives, and explainable reasons.
        """
        # 1. Feature extraction with robust error handling
        try:
            features = extract_classification_features(document_input, ocr_result=ocr_result)
        except Exception as e:
            logger.error(f"Error extracting classification features: {e}. Returning UNKNOWN result.")
            h_top, h_conf, h_alts, h_reasons = evaluate_features_heuristic({})
            h_reasons.append(f"Image read error: {str(e)}")
            return map_prediction_to_result(
                predicted_type="UNKNOWN",
                confidence=0.10,
                alternatives=h_alts,
                expected_type=expected_type,
                reasons=h_reasons,
                is_fallback=True,
            )

        # 2. Try ML Model prediction
        model = cls.get_model(model_path)
        is_fallback = (model is None)

        if model is not None:
            try:
                pred_type, confidence, alternatives = model.predict_single(features)
                reasons = []
            except Exception as e:
                logger.warning(f"ML classification prediction failed: {e}. Reverting to heuristic fallback.")
                pred_type, confidence, alternatives, reasons = evaluate_features_heuristic(features)
                is_fallback = True
        else:
            pred_type, confidence, alternatives, reasons = evaluate_features_heuristic(features)

        # 3. Format and threshold operational result
        result = map_prediction_to_result(
            predicted_type=pred_type,
            confidence=confidence,
            alternatives=alternatives,
            expected_type=expected_type,
            reasons=reasons,
            features_summary=features,
            is_fallback=is_fallback,
        )

        return result
