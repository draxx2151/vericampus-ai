"""
VeriCampus AI — Stage 6: Evidence & Decision Support Engine Schemas
Pydantic v2 data models for individual evidence items and top-level evidence summaries.
Enforces PII masking, explainable semantics, and non-autonomous review states.
"""
from enum import Enum
from typing import Optional, Dict, List, Any
from datetime import datetime
import re
from pydantic import BaseModel, Field, field_validator

from .config import STAGE6_VERSION, ReviewReason


class EvidenceCategory(str, Enum):
    """
    Standardized classification of an individual piece of evidence.
    """
    SUPPORTING = "SUPPORTING"              # Supports application consistency or eligibility
    CONFLICTING = "CONFLICTING"            # Discrepancy or conflict requiring attention
    NEUTRAL = "NEUTRAL"                    # Unconfigured provider, blocked check, or missing external record
    WARNING = "WARNING"                    # Non-fatal advisory signal (e.g. medium quality, minor formatting)
    TECHNICAL_ERROR = "TECHNICAL_ERROR"    # Processing failure (distinct from applicant discrepancy)


class EvidenceStrength(str, Enum):
    """
    Hierarchical weight of evidence.
    """
    STRONG = "STRONG"        # Critical identity confirmation/conflict, official authority match/mismatch
    MODERATE = "MODERATE"    # Reliable cross-document consistency, complete field extraction
    WEAK = "WEAK"            # Minor formatting variation, advisory metadata, image compression signal
    NONE = "NONE"            # Neutral check, unconfigured provider, or technical error


class EvidenceState(str, Enum):
    """
    Overall assistive decision-support review state.
    NOTE: These represent REVIEW STATES for the human officer, NOT autonomous approve/reject decisions.
    """
    CLEAR_FOR_REVIEW = "CLEAR_FOR_REVIEW"              # All available evidence is consistent; ready for admin sign-off
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"    # One or more material discrepancies require admin resolution
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"    # Missing documents or unreadable scans prevent full evaluation
    PROCESSING_ERROR = "PROCESSING_ERROR"              # Technical failure prevented reliable evidence generation


def mask_sensitive_pii_string(val: Optional[str]) -> Optional[str]:
    """
    Utility to mask raw 12-digit Aadhaar, 10-char PAN, or filesystem paths in string fields.
    """
    if not val or not isinstance(val, str):
        return val

    # Mask 12-digit Aadhaar numbers: replace first 8 digits with asterisks
    masked = re.sub(r'\b(\d{4})[\s\-]?(\d{4})[\s\-]?(\d{4})\b', r'********\3', val)

    # Mask 10-character PAN cards: replace first 6 characters with asterisks
    masked = re.sub(r'\b([A-Z]{5})(\d{4})([A-Z])\b', r'******\2\3', masked)

    # Sanitize Windows/Linux local absolute filesystem storage paths
    masked = re.sub(r'[A-Za-z]:\\[^:\r\n<>"]*?storage\\[^\s\r\n<>"]+', '[SECURE_STORAGE_PATH]', masked)
    masked = re.sub(r'/(?:Users|home|tmp|backend)/[^:\r\n<>"]*?storage/[^\s\r\n<>"]*', '[SECURE_STORAGE_PATH]', masked)

    return masked


class EvidenceItem(BaseModel):
    """
    Detailed, traceable record of an individual verification check or finding.
    """
    evidence_id: str = Field(..., description="Unique traceable identifier for this evidence item")
    category: EvidenceCategory = Field(..., description="Evidence classification: SUPPORTING, CONFLICTING, etc.")
    source_stage: str = Field(..., description="Originating pipeline stage (STAGE_1, STAGE_2, STAGE_3, STAGE_4, STAGE_5, RULES_ENGINE)")
    source_document: Optional[str] = Field(None, description="Affected document type if applicable")
    check_type: str = Field(..., description="Specific verification rule or check identifier")
    status: str = Field(..., description="Raw check status string (PASS, WARNING, MISMATCH, NOT_AVAILABLE, etc.)")
    strength: EvidenceStrength = Field(default=EvidenceStrength.MODERATE, description="Evidence weight")
    title: str = Field(..., description="Concise human-readable title of the evidence finding")
    explanation: str = Field(..., description="Detailed, explainable justification without opaque AI jargon")
    field_name: Optional[str] = Field(None, description="Specific field compared (e.g. name, dob, id_number)")
    expected_value: Optional[str] = Field(None, description="Expected value (masked if sensitive)")
    observed_value: Optional[str] = Field(None, description="Observed value (masked if sensitive)")
    masked_value: Optional[str] = Field(None, description="Safely masked representation of sensitive identifiers")
    reason_code: Optional[str] = Field(None, description="Standardized ReviewReason code")
    requires_human_review: bool = Field(default=False, description="Whether this finding necessitates human inspection")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional non-sensitive diagnostic metadata")

    @field_validator("expected_value", "observed_value", "masked_value", "explanation", mode="after")
    @classmethod
    def validate_pii_masked(cls, v: Optional[str]) -> Optional[str]:
        return mask_sensitive_pii_string(v)


class EvidenceSummary(BaseModel):
    """
    Consolidated, top-level decision-support package synthesizing Stages 1 through 5.
    Provides clear, transparent evidence breakdowns to assist human administrative review.
    """
    application_id: Optional[str] = Field(None, description="Target scholarship application ID")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="ISO execution timestamp")
    supporting_evidence: List[EvidenceItem] = Field(default_factory=list, description="Findings confirming consistency/eligibility")
    conflicting_evidence: List[EvidenceItem] = Field(default_factory=list, description="Findings indicating discrepancies")
    neutral_evidence: List[EvidenceItem] = Field(default_factory=list, description="Checks unavailable or blocked without prejudice")
    warnings: List[EvidenceItem] = Field(default_factory=list, description="Advisory observations requiring attention")
    technical_issues: List[EvidenceItem] = Field(default_factory=list, description="System/network issues during processing")
    
    total_evidence_count: int = Field(default=0, description="Total number of evaluated evidence items")
    strong_support_count: int = Field(default=0, description="Count of strong supporting items")
    moderate_support_count: int = Field(default=0, description="Count of moderate supporting items")
    weak_support_count: int = Field(default=0, description="Count of weak supporting items")
    strong_conflict_count: int = Field(default=0, description="Count of strong conflicting items")
    moderate_conflict_count: int = Field(default=0, description="Count of moderate conflicting items")
    weak_conflict_count: int = Field(default=0, description="Count of weak conflicting items")

    human_review_required: bool = Field(default=False, description="True if any finding demands human review")
    review_reasons: List[str] = Field(default_factory=list, description="Deduplicated list of review reason codes")
    overall_evidence_state: EvidenceState = Field(default=EvidenceState.CLEAR_FOR_REVIEW, description="Assistive review state")
    explanation: str = Field(..., description="High-level narrative explaining the evidence balance and review state")
    pipeline_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary status of Stages 1-5")
    engine_version: str = Field(default=STAGE6_VERSION, description="Version of the Evidence Engine")
