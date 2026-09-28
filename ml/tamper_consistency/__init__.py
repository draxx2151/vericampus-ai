"""
VeriCampus AI — Stage 4: Tamper Detection & Cross-Document Consistency Package
Provides automated visual/structural tamper analysis and cross-document semantic consistency checks.
"""
from .schemas import (
    CheckStatus,
    SignalCategory,
    SignalSeverity,
    NameMatchCategory,
    EvidenceStrength,
    TamperSignal,
    TamperAssessment,
    ConsistencyCheckResult,
    ConsistencyAssessment,
    Stage4VerificationResult,
)
from .base import BaseTamperDetector, BaseConsistencyChecker
from .service import TamperConsistencyService
from .config import (
    STAGE4_VERSION,
    STAGE4_PASS_THRESHOLD,
    STAGE4_WARNING_THRESHOLD,
    EVIDENCE_WEIGHTS,
)

__all__ = [
    "CheckStatus",
    "SignalCategory",
    "SignalSeverity",
    "NameMatchCategory",
    "EvidenceStrength",
    "TamperSignal",
    "TamperAssessment",
    "ConsistencyCheckResult",
    "ConsistencyAssessment",
    "Stage4VerificationResult",
    "BaseTamperDetector",
    "BaseConsistencyChecker",
    "TamperConsistencyService",
    "STAGE4_VERSION",
    "STAGE4_PASS_THRESHOLD",
    "STAGE4_WARNING_THRESHOLD",
    "EVIDENCE_WEIGHTS",
]
