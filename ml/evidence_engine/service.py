"""
VeriCampus AI — Stage 6: Evidence & Decision Support Engine Service
Orchestrates the end-to-end evidence synthesis workflow across Stages 1 through 5 and eligibility rules.
"""
from typing import Dict, Any, Optional, List

from .base import BaseEvidenceEngine
from .schemas import EvidenceSummary, EvidenceItem
from .evidence_mapper import (
    map_stage1_quality,
    map_stage2_classification,
    map_stage3_extractions,
    map_stage4_tamper_and_consistency,
    map_stage5_authority,
    map_rules_engine_eligibility,
)
from .scorer import synthesize_evidence_summary


class EvidenceEngineService(BaseEvidenceEngine):
    """
    Central coordinator for Stage 6 Evidence and Decision Support.
    Translates raw pipeline findings into structured, assistive evidence packages.
    """

    def evaluate(
        self,
        application_id: Optional[str] = None,
        quality_results: Optional[Dict[str, Any]] = None,
        classification_results: Optional[Dict[str, Any]] = None,
        extractions: Optional[Dict[str, Any]] = None,
        tamper_results: Optional[Dict[str, Any]] = None,
        authority_results: Optional[Dict[str, Any]] = None,
        rules_evaluation: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> EvidenceSummary:
        """
        Executes comprehensive evidence mapping and synthesis across all 5 verification stages.
        """
        raw_items: List[EvidenceItem] = []

        # 1. Map Stage 1: Document Quality Gate
        raw_items.extend(map_stage1_quality(quality_results))

        # 2. Map Stage 2: AI Document Classification
        raw_items.extend(map_stage2_classification(classification_results))

        # 3. Map Stage 3: Structured Field Extractions
        raw_items.extend(map_stage3_extractions(extractions))

        # 4. Map Stage 4: Tamper Detection & Cross-Document Consistency
        raw_items.extend(map_stage4_tamper_and_consistency(tamper_results))

        # 5. Map Stage 5: Authority Verification
        raw_items.extend(map_stage5_authority(authority_results))

        # 6. Map Scheme Eligibility Rules
        raw_items.extend(map_rules_engine_eligibility(rules_evaluation))

        # Build pipeline summary dictionary for administrative auditability
        pipeline_summary = {
            "stage_1_quality": (quality_results.get("quality_gate_status") or "COMPLETE") if quality_results else "SKIPPED",
            "stage_2_classification": (classification_results.get("overall_status") or "COMPLETE") if classification_results else "SKIPPED",
            "stage_3_extraction": "COMPLETE" if extractions else "SKIPPED",
            "stage_4_tamper_consistency": (tamper_results.get("overall_status") or "COMPLETE") if tamper_results else "SKIPPED",
            "stage_5_authority": (authority_results.get("overall_status") or "NOT_AVAILABLE") if authority_results else "NOT_AVAILABLE",
        }

        # 7. Synthesize, deduplicate, and determine decision-support review state
        return synthesize_evidence_summary(
            raw_items=raw_items,
            application_id=application_id,
            pipeline_summary=pipeline_summary,
            context=context or {},
        )
