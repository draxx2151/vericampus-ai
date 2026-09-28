"""
VeriCampus AI — Stage 5: Authority Verification Schemas
Pydantic v2 data models for external authority verification.
Enforces non-sensitive reference IDs, PII masking, and explicit status definitions.
"""
from enum import Enum
from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from .config import STAGE5_VERSION


class AuthorityStatus(str, Enum):
    """
    Core outcome of authority verification inspection.
    """
    MATCH = "MATCH"                    # Authority record confirmed and matches extracted data
    MISMATCH = "MISMATCH"              # Authority record found but conflicting data exists
    NOT_AVAILABLE = "NOT_AVAILABLE"    # No authority provider configured (neutral baseline)
    BLOCKED = "BLOCKED"                # Verification skipped due to prior stage quality/classification
    ERROR = "ERROR"                    # Technical failure/timeout connecting to provider
    PENDING = "PENDING"                # Reserved for asynchronous verification


class EvidenceStrength(str, Enum):
    """
    Hierarchical strength of evidence provided by authority inspection.
    """
    STRONG = "STRONG"        # Full authorized ID match or complete verified academic record
    MODERATE = "MODERATE"    # Masked ID last-4 + Name + DOB match, or partial institutional match
    WEAK = "WEAK"            # Isolated last-4 match alone or weak advisory metadata
    NONE = "NONE"            # Provider unavailable, blocked, or technical error


class ConsentStatus(str, Enum):
    """
    Future-ready student consent status for external record retrieval.
    """
    NOT_REQUIRED = "NOT_REQUIRED"  # Standard default for offline/unconfigured environments
    REQUIRED = "REQUIRED"          # Explicit student consent mandated by provider
    GRANTED = "GRANTED"            # Student granted authorization
    DENIED = "DENIED"              # Student declined authorization
    EXPIRED = "EXPIRED"            # Prior authorization expired


class RecordStatus(str, Enum):
    """
    Freshness/validity status of external authority record.
    """
    ACTIVE = "ACTIVE"              # Valid and currently effective
    EXPIRED = "EXPIRED"            # External record validity expired
    UNKNOWN = "UNKNOWN"            # Provider did not specify validity
    NOT_AVAILABLE = "NOT_AVAILABLE"# Provider unconfigured or unable to query record


class FieldMatchStatus(str, Enum):
    """
    Status of an individual field comparison against an authoritative record.
    """
    MATCH = "MATCH"                # Values agree within configured tolerance
    MISMATCH = "MISMATCH"          # Values conflict
    NOT_AVAILABLE = "NOT_AVAILABLE"# Field is missing from the authoritative record
    SKIPPED = "SKIPPED"            # Field comparison skipped due to missing extraction


class FieldComparisonResult(BaseModel):
    """
    Detailed comparison between extracted document field and authoritative record.
    """
    field_name: str = Field(..., description="Name of the evaluated field")
    extracted_value: Optional[str] = Field(None, description="Extracted document value (masked if sensitive)")
    authority_value: Optional[str] = Field(None, description="Authoritative record value (masked if sensitive)")
    status: FieldMatchStatus = Field(..., description="Comparison status")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence of comparison")
    reason: str = Field(..., description="Explanation of match or discrepancy")


class AuthorityVerificationResult(BaseModel):
    """
    Authority verification assessment for a single document.
    """
    document_type: str = Field(..., description="Target document type identifier")
    provider: str = Field(..., description="Name of the authority provider")
    provider_version: str = Field(default="1.0.0", description="Operational provider version")
    verification_id: str = Field(..., description="Unique non-sensitive audit reference ID")
    status: AuthorityStatus = Field(AuthorityStatus.NOT_AVAILABLE, description="Authority verification status")
    evidence_strength: EvidenceStrength = Field(EvidenceStrength.NONE, description="Evidence weight")
    consent_status: ConsentStatus = Field(ConsentStatus.NOT_REQUIRED, description="Student consent state")
    record_status: RecordStatus = Field(RecordStatus.NOT_AVAILABLE, description="Authority record freshness/status")
    record_date: Optional[str] = Field(None, description="External record issuance or generation date (ISO)")
    record_freshness: Optional[str] = Field(None, description="Descriptive freshness assessment")
    verified_fields: List[str] = Field(default_factory=list, description="Fields evaluated against authority")
    matched_fields: List[str] = Field(default_factory=list, description="Fields that successfully matched")
    mismatched_fields: List[str] = Field(default_factory=list, description="Fields that conflicted")
    field_comparisons: Dict[str, FieldComparisonResult] = Field(default_factory=dict, description="Detailed field comparisons")
    reference_id: Optional[str] = Field(None, description="Masked non-sensitive external reference identifier")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Overall match confidence if applicable")
    reason: str = Field(..., description="Human-readable outcome explanation")
    checked_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="ISO timestamp")
    raw_response_available: bool = Field(False, description="Whether raw provider payload is archived internally")
    is_available: bool = Field(False, description="Whether provider is actively configured")

    @field_validator("reference_id")
    @classmethod
    def validate_reference_id_masked(cls, v: Optional[str]) -> Optional[str]:
        """Ensures raw 12-digit Aadhaar or 10-char PAN is not exposed unmasked."""
        if not v:
            return v
        import re
        # Check if 12 consecutive unmasked digits (raw Aadhaar)
        if re.search(r'\b\d{12}\b', v):
            return f"********{v[-4:]}"
        # Check if 10 consecutive unmasked PAN chars
        if re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', v):
            return f"******{v[-4:]}"
        return v

    @property
    def provider_name(self) -> str:
        if self.provider in ("unavailable", "UnavailableProvider"):
            return "UnavailableProvider"
        return self.provider




class Stage5VerificationResult(BaseModel):
    """
    Application-level composite result for Stage 5 Authority Verification.
    """
    overall_status: AuthorityStatus = Field(AuthorityStatus.NOT_AVAILABLE, description="Composite stage status")
    overall_evidence_strength: EvidenceStrength = Field(EvidenceStrength.NONE, description="Composite evidence weight")
    review_required: bool = Field(False, description="Whether an authority discrepancy necessitates human review")
    documents: Dict[str, AuthorityVerificationResult] = Field(default_factory=dict, description="Per-document results")
    matched_count: int = Field(0, description="Number of documents with MATCH status")
    mismatched_count: int = Field(0, description="Number of documents with MISMATCH status")
    unavailable_count: int = Field(0, description="Number of documents with NOT_AVAILABLE status")
    blocked_count: int = Field(0, description="Number of documents with BLOCKED status")
    error_count: int = Field(0, description="Number of documents with ERROR status")
    critical_mismatches: List[str] = Field(default_factory=list, description="Summary of critical conflicting items")
    warnings: List[str] = Field(default_factory=list, description="Advisory warnings")
    summary: str = Field(..., description="High-level audit summary")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Execution timestamp")
    stage_version: str = Field(default=STAGE5_VERSION, description="Stage implementation version")
