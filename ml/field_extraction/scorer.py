"""
VeriCampus AI — Stage 3 Field Extraction Scorer & Completeness Evaluator
Provides transparent confidence aggregation and configurable prototype completeness scoring.
Separates OCR confidence from Field Extraction confidence.
"""
from typing import Dict, List, Tuple, Optional
from .schemas import (
    FieldExtractionResult,
    ExtractionStatus,
    DocumentExtractionStatus,
)
from .config import (
    PROTOTYPE_COMPLETENESS_COMPLETE_THRESHOLD,
    PROTOTYPE_COMPLETENESS_PARTIAL_THRESHOLD,
    FIELD_CONFIDENCE_HIGH,
    FIELD_CONFIDENCE_MEDIUM,
    FIELD_CONFIDENCE_LOW,
)

# Required fields per document type for completeness evaluation
REQUIRED_DOCUMENT_FIELDS: Dict[str, List[str]] = {
    "GOVERNMENT_ID": ["full_name", "date_of_birth", "id_number"],
    "MARKSHEET": ["student_name", "roll_number", "examination_name", "examination_year", "total_marks", "percentage"],
    "INCOME_CERTIFICATE": ["applicant_name", "income_amount", "financial_year", "certificate_number", "issuing_authority"],
    "DOMICILE_CERTIFICATE": ["applicant_name", "domicile_state", "certificate_number", "issue_date"],
}


def calculate_field_confidence(
    ocr_confidence: float,
    pattern_match_quality: float = 1.0,
    proximity_bonus: float = 0.0,
    has_normalized_value: bool = True,
) -> float:
    """
    Computes field extraction confidence strictly separated from raw OCR engine confidence.
    Combines OCR line fidelity, regex precision, and layout proximity.
    """
    if not has_normalized_value:
        return 0.0

    # Base weighted: 40% OCR confidence + 50% pattern match quality + 10% spatial alignment
    base = (0.40 * ocr_confidence) + (0.50 * pattern_match_quality) + (0.10 * proximity_bonus)
    # Clamp to [0.0, 1.0]
    return round(max(0.0, min(1.0, base)), 3)


def calculate_overall_confidence(fields: Dict[str, FieldExtractionResult]) -> float:
    """
    Calculates overall document extraction confidence as a transparent, explainable
    mean of extracted non-empty field confidences.
    """
    extracted_confs = [
        f.confidence for f in fields.values()
        if f.extraction_status in (ExtractionStatus.EXTRACTED, ExtractionStatus.LOW_CONFIDENCE)
        and f.confidence > 0.0
    ]
    if not extracted_confs:
        return 0.0

    return round(sum(extracted_confs) / len(extracted_confs), 3)


def calculate_completeness(
    doc_type: str,
    fields: Dict[str, FieldExtractionResult]
) -> Tuple[float, DocumentExtractionStatus]:
    """
    Evaluates extraction completeness against configurable prototype required fields.
    Returns:
        (completeness_ratio, DocumentExtractionStatus)
    NOTE: Thresholds (>=0.80 COMPLETE, 0.40-0.79 PARTIAL) are prototype operational heuristics.
    """
    req_fields = REQUIRED_DOCUMENT_FIELDS.get(doc_type, [])
    if not req_fields:
        # Default fallback if unknown document type
        return 0.0, DocumentExtractionStatus.NOT_APPLICABLE

    extracted_count = 0
    for rf in req_fields:
        field_res = fields.get(rf)
        if field_res and field_res.extraction_status == ExtractionStatus.EXTRACTED and field_res.normalized_value is not None:
            extracted_count += 1

    ratio = round(extracted_count / len(req_fields), 3)

    if ratio >= PROTOTYPE_COMPLETENESS_COMPLETE_THRESHOLD:
        status = DocumentExtractionStatus.COMPLETE
    elif ratio >= PROTOTYPE_COMPLETENESS_PARTIAL_THRESHOLD:
        status = DocumentExtractionStatus.PARTIAL
    else:
        status = DocumentExtractionStatus.FAILED

    return ratio, status
