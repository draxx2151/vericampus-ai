"""
VeriCampus AI — Stage 4: Tamper Detection & Cross-Document Consistency Schemas
Standardized data contracts for tamper signals, consistency checks, and Stage 4 assessment summaries.
"""
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

from .config import STAGE4_VERSION


class CheckStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class SignalCategory(str, Enum):
    VISUAL = "VISUAL"
    STRUCTURAL = "STRUCTURAL"
    METADATA = "METADATA"
    CROSS_DOCUMENT_IDENTITY = "CROSS_DOCUMENT_IDENTITY"
    CROSS_DOCUMENT_ELIGIBILITY = "CROSS_DOCUMENT_ELIGIBILITY"


class SignalSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NameMatchCategory(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    NORMALIZED_MATCH = "NORMALIZED_MATCH"
    MINOR_VARIATION = "MINOR_VARIATION"
    POSSIBLE_MISMATCH = "POSSIBLE_MISMATCH"
    MISMATCH = "MISMATCH"


class EvidenceStrength(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"


class TamperSignal(BaseModel):
    """Structured evidence signal for potential image/structural/metadata manipulation."""
    signal_name: str
    category: SignalCategory
    severity: SignalSeverity
    score: float = Field(..., ge=0.0, le=100.0, description="Normalized score (100=clean, 0=highly anomalous)")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence in this detector signal")
    status: CheckStatus = CheckStatus.PASS
    explanation: str
    affected_region: Optional[Dict[str, float]] = Field(None, description="Spatial coordinates {x_min, y_min, x_max, y_max}")
    page_number: Optional[int] = Field(1, description="Source page number")
    affected_document: Optional[str] = None
    evidence_strength: EvidenceStrength = EvidenceStrength.WEAK


class TamperAssessment(BaseModel):
    """Consolidated visual and structural tamper assessment across all documents."""
    status: CheckStatus = CheckStatus.PASS
    overall_score: float = Field(100.0, ge=0.0, le=100.0, description="Composite tamper cleanliness score")
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    signals: List[TamperSignal] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    detector_version: str = STAGE4_VERSION


class ConsistencyCheckResult(BaseModel):
    """Result of comparing a specific field across two or more uploaded documents."""
    check_name: str
    category: str
    status: CheckStatus
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    documents_compared: List[str]
    field_name: str
    values_compared: Dict[str, Optional[str]] = Field(default_factory=dict, description="Masked string values for display")
    normalized_values: Dict[str, Any] = Field(default_factory=dict, description="Normalized representations used for comparison")
    match_type: Optional[str] = None
    reason: str
    is_critical: bool = False


class ConsistencyAssessment(BaseModel):
    """Consolidated cross-document consistency assessment."""
    status: CheckStatus = CheckStatus.PASS
    overall_score: float = Field(100.0, ge=0.0, le=100.0, description="Composite cross-document consistency score")
    checks: List[ConsistencyCheckResult] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    critical_inconsistencies: List[str] = Field(default_factory=list)
    explanation: List[str] = Field(default_factory=list)


class Stage4VerificationResult(BaseModel):
    """Consolidated Stage 4 payload combining tamper signals and cross-document consistency."""
    stage_version: str = STAGE4_VERSION
    tamper_assessment: TamperAssessment
    consistency_assessment: ConsistencyAssessment
    overall_status: CheckStatus
    overall_score: float = Field(100.0, ge=0.0, le=100.0)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    review_required: bool = False
    model_metadata: Dict[str, Any] = Field(default_factory=dict)
