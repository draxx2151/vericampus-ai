"""
VeriCampus AI — Document Quality Gate Package
Stage 1 of the VeriCampus AI 7-stage verification architecture.

Determines whether an uploaded document is of sufficient visual/OCR quality
for reliable downstream AI processing.
"""
from .schemas import (
    QualityLevel,
    QualityGateStatus,
    QualityFeatures,
    QualityAssessment,
)
from .config import (
    HIGH_THRESHOLD,
    ACCEPTABLE_THRESHOLD,
    LOW_THRESHOLD,
    QUALITY_FEATURE_NAMES,
    MODEL_VERSION,
)
from .inference import DocumentQualityAnalyzer

__all__ = [
    "QualityLevel",
    "QualityGateStatus",
    "QualityFeatures",
    "QualityAssessment",
    "DocumentQualityAnalyzer",
    "HIGH_THRESHOLD",
    "ACCEPTABLE_THRESHOLD",
    "LOW_THRESHOLD",
    "QUALITY_FEATURE_NAMES",
    "MODEL_VERSION",
]
