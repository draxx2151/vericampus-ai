"""
VeriCampus AI — ML Phase 1: Stage 6 Evidence & Decision Support Engine
Combines technical verification outputs across Stages 1-5 into structured, explainable evidence packages.
"""
from .config import STAGE6_VERSION, ReviewReason, EVIDENCE_CONFIG
from .schemas import (
    EvidenceCategory,
    EvidenceStrength,
    EvidenceState,
    EvidenceItem,
    EvidenceSummary,
    mask_sensitive_pii_string,
)
from .base import BaseEvidenceEngine
from .service import EvidenceEngineService
from .evidence_mapper import (
    map_stage1_quality,
    map_stage2_classification,
    map_stage3_extractions,
    map_stage4_tamper_and_consistency,
    map_stage5_authority,
    map_rules_engine_eligibility,
)
from .scorer import (
    consolidate_overlapping_evidence,
    synthesize_evidence_summary,
)

__all__ = [
    "STAGE6_VERSION",
    "ReviewReason",
    "EVIDENCE_CONFIG",
    "EvidenceCategory",
    "EvidenceStrength",
    "EvidenceState",
    "EvidenceItem",
    "EvidenceSummary",
    "mask_sensitive_pii_string",
    "BaseEvidenceEngine",
    "EvidenceEngineService",
    "map_stage1_quality",
    "map_stage2_classification",
    "map_stage3_extractions",
    "map_stage4_tamper_and_consistency",
    "map_stage5_authority",
    "map_rules_engine_eligibility",
    "consolidate_overlapping_evidence",
    "synthesize_evidence_summary",
]
