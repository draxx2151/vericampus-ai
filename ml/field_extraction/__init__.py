"""
VeriCampus AI — ML Phase 1 — Stage 3: OCR + Field Extraction Package
"""
from .config import (
    FIELD_EXTRACTOR_VERSION,
    PROTOTYPE_COMPLETENESS_COMPLETE_THRESHOLD,
    PROTOTYPE_COMPLETENESS_PARTIAL_THRESHOLD,
    FIELD_CONFIDENCE_HIGH,
    FIELD_CONFIDENCE_MEDIUM,
    FIELD_CONFIDENCE_LOW,
    STAGE1_MINIMUM_QUALITY_THRESHOLD,
)
from .schemas import (
    ExtractionStatus,
    DocumentExtractionStatus,
    FieldExtractionResult,
    SubjectScore,
    DocumentFieldExtractionResult,
)
from .base import BaseFieldExtractor
from .service import FieldExtractionService
from .extractors import (
    GovernmentIdFieldExtractor,
    MarksheetFieldExtractor,
    IncomeCertificateFieldExtractor,
    DomicileCertificateFieldExtractor,
)
from .normalizers import (
    normalize_name,
    normalize_date,
    normalize_currency,
    normalize_percentage,
    normalize_id_number,
    mask_sensitive_id,
    normalize_whitespace,
)
from .scorer import (
    calculate_field_confidence,
    calculate_overall_confidence,
    calculate_completeness,
)
from .aliases import FIELD_ALIASES

__all__ = [
    "FIELD_EXTRACTOR_VERSION",
    "PROTOTYPE_COMPLETENESS_COMPLETE_THRESHOLD",
    "PROTOTYPE_COMPLETENESS_PARTIAL_THRESHOLD",
    "FIELD_CONFIDENCE_HIGH",
    "FIELD_CONFIDENCE_MEDIUM",
    "FIELD_CONFIDENCE_LOW",
    "STAGE1_MINIMUM_QUALITY_THRESHOLD",
    "ExtractionStatus",
    "DocumentExtractionStatus",
    "FieldExtractionResult",
    "SubjectScore",
    "DocumentFieldExtractionResult",
    "BaseFieldExtractor",
    "FieldExtractionService",
    "GovernmentIdFieldExtractor",
    "MarksheetFieldExtractor",
    "IncomeCertificateFieldExtractor",
    "DomicileCertificateFieldExtractor",
    "normalize_name",
    "normalize_date",
    "normalize_currency",
    "normalize_percentage",
    "normalize_id_number",
    "mask_sensitive_id",
    "normalize_whitespace",
    "calculate_field_confidence",
    "calculate_overall_confidence",
    "calculate_completeness",
    "FIELD_ALIASES",
]
