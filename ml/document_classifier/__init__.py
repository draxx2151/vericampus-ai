"""
VeriCampus AI — Document Classification Module (Stage 2)
Provides document type classification, mismatch detection, and confidence scoring.
"""
from .schemas import (
    ClassificationStatus,
    ClassificationAlternative,
    DocumentClassificationResult,
)
from .config import (
    TARGET_CLASSES,
    CONFIDENCE_THRESHOLD_PASS,
    CONFIDENCE_THRESHOLD_WARNING,
    MODEL_VERSION,
)
from .inference import DocumentClassifier

CLASSIFIER_PASS_THRESHOLD = CONFIDENCE_THRESHOLD_PASS
CLASSIFIER_WARNING_THRESHOLD = CONFIDENCE_THRESHOLD_WARNING

__all__ = [
    "ClassificationStatus",
    "ClassificationAlternative",
    "DocumentClassificationResult",
    "TARGET_CLASSES",
    "CONFIDENCE_THRESHOLD_PASS",
    "CONFIDENCE_THRESHOLD_WARNING",
    "CLASSIFIER_PASS_THRESHOLD",
    "CLASSIFIER_WARNING_THRESHOLD",
    "MODEL_VERSION",
    "DocumentClassifier",
]
