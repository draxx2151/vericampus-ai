"""
VeriCampus AI — Stage 6: Evidence Scorer & Synthesizer
Consolidates raw evidence items, deduplicates overlapping issues, computes weighted counts,
determines the assistive overall evidence state, and generates explainable human-readable narratives.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from .config import STAGE6_VERSION, EVIDENCE_CONFIG, ReviewReason
from .schemas import (
    EvidenceCategory,
    EvidenceStrength,
    EvidenceState,
    EvidenceItem,
    EvidenceSummary,
)


def consolidate_overlapping_evidence(items: List[EvidenceItem]) -> List[EvidenceItem]:
    """
    Consolidates multiple evidence items from different stages that report the same underlying finding.
    Strengthens explainability without artificially multiplying conflict counts.
    """
    consolidated: List[EvidenceItem] = []
    seen_keys: Dict[str, EvidenceItem] = {}

    for item in items:
        # Construct deduplication key based on check type, field name, and category
        if item.field_name and item.category in (EvidenceCategory.CONFLICTING, EvidenceCategory.SUPPORTING):
            key = f"{item.category.value}:{item.field_name}"
        elif item.reason_code and item.category == EvidenceCategory.CONFLICTING:
            key = f"{item.category.value}:{item.reason_code}"
        else:
            key = f"{item.evidence_id}"

        if key in seen_keys:
            existing = seen_keys[key]
            # Merge sources and augment explanation if different stage
            if item.source_stage not in existing.source_stage:
                existing.source_stage = f"{existing.source_stage}, {item.source_stage}"
                existing.explanation = f"{existing.explanation} Confirmed by {item.source_stage}."
            # Retain stronger evidence weight
            if item.strength == EvidenceStrength.STRONG and existing.strength != EvidenceStrength.STRONG:
                existing.strength = EvidenceStrength.STRONG
        else:
            seen_keys[key] = item
            consolidated.append(item)

    return consolidated


def synthesize_evidence_summary(
    raw_items: List[EvidenceItem],
    application_id: Optional[str] = None,
    pipeline_summary: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> EvidenceSummary:
    """
    Synthesizes consolidated evidence items into a structured EvidenceSummary.
    Determines overall review state and generates transparent explanations.
    """
    items = consolidate_overlapping_evidence(raw_items)

    supporting: List[EvidenceItem] = []
    conflicting: List[EvidenceItem] = []
    neutral: List[EvidenceItem] = []
    warnings: List[EvidenceItem] = []
    technical: List[EvidenceItem] = []

    strong_sup = 0
    mod_sup = 0
    weak_sup = 0

    strong_conf = 0
    mod_conf = 0
    weak_conf = 0

    for it in items:
        if it.category == EvidenceCategory.SUPPORTING:
            supporting.append(it)
            if it.strength == EvidenceStrength.STRONG:
                strong_sup += 1
            elif it.strength == EvidenceStrength.MODERATE:
                mod_sup += 1
            elif it.strength == EvidenceStrength.WEAK:
                weak_sup += 1
        elif it.category == EvidenceCategory.CONFLICTING:
            conflicting.append(it)
            if it.strength == EvidenceStrength.STRONG:
                strong_conf += 1
            elif it.strength == EvidenceStrength.MODERATE:
                mod_conf += 1
            elif it.strength == EvidenceStrength.WEAK:
                weak_conf += 1
        elif it.category == EvidenceCategory.NEUTRAL:
            neutral.append(it)
        elif it.category == EvidenceCategory.WARNING:
            warnings.append(it)
        elif it.category == EvidenceCategory.TECHNICAL_ERROR:
            technical.append(it)

    # Compile distinct review reasons
    review_reasons_set = set()
    for it in conflicting:
        if it.reason_code:
            review_reasons_set.add(it.reason_code)
    for it in warnings:
        if it.requires_human_review and it.reason_code:
            review_reasons_set.add(it.reason_code)

    human_review_required = (
        len(conflicting) > 0
        or any(it.requires_human_review for it in warnings)
        or strong_conf > 0
        or mod_conf > 0
    )

    # Determine overall evidence state
    # 1. Processing error check
    if any(it.category == EvidenceCategory.TECHNICAL_ERROR and it.requires_human_review for it in technical):
        overall_state = EvidenceState.PROCESSING_ERROR
        explanation = (
            "A technical processing problem occurred during automated verification. "
            "System logs should be inspected by an administrator."
        )
    # 2. Insufficient evidence check (e.g. if extraction blocked on critical documents or unreadable scans)
    elif any(it.reason_code == ReviewReason.LOW_DOCUMENT_QUALITY.value and it.status == "REUPLOAD_REQUIRED" for it in warnings) or (len(supporting) == 0 and len(conflicting) == 0):
        overall_state = EvidenceState.INSUFFICIENT_EVIDENCE
        explanation = (
            "Verification evidence is currently insufficient to complete assessment. "
            "One or more required documents were flagged as unreadable or missing, requiring replacement upload."
        )
    # 3. Conflicting evidence check
    elif human_review_required:
        overall_state = EvidenceState.HUMAN_REVIEW_REQUIRED
        conflict_titles = [c.title for c in conflicting[:3]]
        reasons_text = "; ".join(conflict_titles) if conflict_titles else "discrepancies detected"
        explanation = (
            f"Administrative review is recommended. The automated engine identified {len(conflicting)} "
            f"material discrepancy items ({reasons_text}). "
            "Authorized college review is required before taking a final scholarship action."
        )
    # 4. Clear for review
    else:
        overall_state = EvidenceState.CLEAR_FOR_REVIEW
        explanation = (
            f"All submitted documents and verified fields are consistent across {len(supporting)} "
            f"supporting evidence items. The application is clear for final administrative sign-off."
        )

    return EvidenceSummary(
        application_id=application_id,
        generated_at=datetime.now().isoformat(),
        supporting_evidence=supporting,
        conflicting_evidence=conflicting,
        neutral_evidence=neutral,
        warnings=warnings,
        technical_issues=technical,
        total_evidence_count=len(items),
        strong_support_count=strong_sup,
        moderate_support_count=mod_sup,
        weak_support_count=weak_sup,
        strong_conflict_count=strong_conf,
        moderate_conflict_count=mod_conf,
        weak_conflict_count=weak_conf,
        human_review_required=human_review_required,
        review_reasons=sorted(list(review_reasons_set)),
        overall_evidence_state=overall_state,
        explanation=explanation,
        pipeline_summary=pipeline_summary or {},
        engine_version=STAGE6_VERSION,
    )
