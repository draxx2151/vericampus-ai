"""
VeriCampus AI — Stage 6: Evidence & Decision Support Engine Configuration
Central policies, constants, and standardized reason codes for evidence aggregation.
All thresholds are prototype/assistive decision-support policies, not autonomous legal judgments.
"""
from enum import Enum

STAGE6_VERSION = "stage6_evidence_engine_v1"


class ReviewReason(str, Enum):
    """
    Standardized reason codes indicating why human administrative review is recommended.
    Reuses established project criteria across Stages 1-5 and eligibility rules.
    """
    LOW_DOCUMENT_QUALITY = "LOW_DOCUMENT_QUALITY"
    DOCUMENT_TYPE_MISMATCH = "DOCUMENT_TYPE_MISMATCH"
    REQUIRED_FIELD_MISSING = "REQUIRED_FIELD_MISSING"
    NAME_MISMATCH = "NAME_MISMATCH"
    DOB_MISMATCH = "DOB_MISMATCH"
    GOVERNMENT_ID_MISMATCH = "GOVERNMENT_ID_MISMATCH"
    CROSS_DOCUMENT_CONFLICT = "CROSS_DOCUMENT_CONFLICT"
    MARKS_ARITHMETIC_CONFLICT = "MARKS_ARITHMETIC_CONFLICT"
    AUTHORITY_MISMATCH = "AUTHORITY_MISMATCH"
    AUTHORITY_UNAVAILABLE = "AUTHORITY_UNAVAILABLE"
    AUTHORITY_CHECK_BLOCKED = "AUTHORITY_CHECK_BLOCKED"
    OCR_LOW_CONFIDENCE = "OCR_LOW_CONFIDENCE"
    TAMPER_SIGNAL = "TAMPER_SIGNAL"
    SCHEME_ELIGIBILITY_CONFLICT = "SCHEME_ELIGIBILITY_CONFLICT"
    TECHNICAL_PROCESSING_ERROR = "TECHNICAL_PROCESSING_ERROR"
    INCOMPLETE_DOCUMENTATION = "INCOMPLETE_DOCUMENTATION"


# Configurable Prototype Policies for Decision Support
EVIDENCE_CONFIG = {
    # Threshold for document quality to be considered supporting vs warning
    "quality_pass_threshold": 70.0,
    "quality_high_threshold": 85.0,

    # Classification confidence thresholds
    "classification_pass_threshold": 0.85,
    "classification_warning_threshold": 0.70,

    # OCR extraction completeness threshold
    "extraction_completeness_threshold": 0.80,

    # Maximum warnings allowed before flagging for closer administrative inspection
    "max_advisory_warnings_for_clear": 4,

    # Engine metadata
    "engine_version": STAGE6_VERSION,
}
