"""
VeriCampus AI — Verification Service Bridge: Stage 6 Evidence Engine
"""
try:
    from ml.evidence_engine import (
        STAGE6_VERSION,
        ReviewReason,
        EVIDENCE_CONFIG,
        EvidenceCategory,
        EvidenceStrength,
        EvidenceState,
        EvidenceItem,
        EvidenceSummary,
        BaseEvidenceEngine,
        EvidenceEngineService,
        synthesize_evidence_summary,
    )
except ImportError:
    STAGE6_VERSION = "stage6_evidence_engine_v1"
    ReviewReason = None
    EVIDENCE_CONFIG = {}
    EvidenceCategory = None
    EvidenceStrength = None
    EvidenceState = None
    EvidenceItem = None
    EvidenceSummary = None
    BaseEvidenceEngine = None
    EvidenceEngineService = None
    synthesize_evidence_summary = None

__all__ = [
    "STAGE6_VERSION",
    "ReviewReason",
    "EVIDENCE_CONFIG",
    "EvidenceCategory",
    "EvidenceStrength",
    "EvidenceState",
    "EvidenceItem",
    "EvidenceSummary",
    "BaseEvidenceEngine",
    "EvidenceEngineService",
    "synthesize_evidence_summary",
]
