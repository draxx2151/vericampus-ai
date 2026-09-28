"""
VeriCampus AI — Stage 3 Field Extraction Schemas
Standardized contracts for field-level extractions, statuses, and document extraction summaries.
"""
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

from .config import FIELD_EXTRACTOR_VERSION


class ExtractionStatus(str, Enum):
    EXTRACTED = "EXTRACTED"
    NOT_FOUND = "NOT_FOUND"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    INVALID = "INVALID"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DocumentExtractionStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    BLOCKED = "BLOCKED"


class FieldExtractionResult(BaseModel):
    """Structured extraction result for a single named field."""
    field_name: str
    raw_value: Optional[str] = Field(None, description="Original unedited string extracted from OCR")
    normalized_value: Optional[Any] = Field(None, description="Standardized type-safe value for downstream comparison")
    display_value: Optional[str] = Field(None, description="Masked or display-ready string representation")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Extraction confidence score (0.0 - 1.0)")
    extraction_status: ExtractionStatus = Field(ExtractionStatus.NOT_FOUND, description="Field-level operational status")
    page_number: Optional[int] = Field(1, description="Source page number in document")
    bounding_box: Optional[Dict[str, float]] = Field(None, description="Spatial coordinates {x_min, y_min, x_max, y_max}")
    source_text: Optional[str] = Field(None, description="Underlying OCR text line or context snippet")
    reason: Optional[str] = Field(None, description="Diagnostic reason if missing, invalid, or low confidence")


class SubjectScore(BaseModel):
    """Structured representation of an academic subject grade row."""
    subject_name: str
    marks_obtained: Optional[float] = None
    maximum_marks: Optional[float] = None
    grade: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class DocumentFieldExtractionResult(BaseModel):
    """Consolidated Stage 3 document-level extraction payload."""
    document_type: str
    extractor_version: str = Field(default=FIELD_EXTRACTOR_VERSION)
    extraction_status: DocumentExtractionStatus
    overall_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Transparent aggregated field confidence")
    completeness_score: float = Field(0.0, ge=0.0, le=1.0, description="Ratio of required fields successfully extracted")
    fields: Dict[str, FieldExtractionResult] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    source_pages: int = Field(default=1)
    ocr_summary: Dict[str, Any] = Field(default_factory=dict)
    model_metadata: Dict[str, Any] = Field(default_factory=dict)
