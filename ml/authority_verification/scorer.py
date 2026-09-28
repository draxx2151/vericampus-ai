"""
VeriCampus AI — Stage 5: Composite Evaluation & Scorer
Aggregates per-document authority results into Stage5VerificationResult.
Enforces the Stage 6 Evidence Engine contract:
- NOT_AVAILABLE, BLOCKED, and ERROR contribute ZERO negative evidence.
- Only MISMATCH triggers review_required = True.
"""
from typing import Dict, List
from datetime import datetime

from .schemas import (
    AuthorityStatus,
    EvidenceStrength,
    AuthorityVerificationResult,
    Stage5VerificationResult,
)
from .config import STAGE5_VERSION


def synthesize_stage5_result(
    document_results: Dict[str, AuthorityVerificationResult],
) -> Stage5VerificationResult:
    """
    Synthesizes individual document authority verification outcomes into
    an application-level Stage5VerificationResult.
    """
    matched_count = sum(1 for r in document_results.values() if r.status == AuthorityStatus.MATCH)
    mismatched_count = sum(1 for r in document_results.values() if r.status == AuthorityStatus.MISMATCH)
    unavailable_count = sum(1 for r in document_results.values() if r.status == AuthorityStatus.NOT_AVAILABLE)
    blocked_count = sum(1 for r in document_results.values() if r.status == AuthorityStatus.BLOCKED)
    error_count = sum(1 for r in document_results.values() if r.status == AuthorityStatus.ERROR)

    critical_mismatches: List[str] = []
    warnings: List[str] = []

    for dt, r in document_results.items():
        if r.status == AuthorityStatus.MISMATCH:
            critical_mismatches.append(f"{dt}: {r.reason}")
        elif r.status == AuthorityStatus.ERROR:
            warnings.append(f"{dt}: Provider technical advisory ({r.reason})")
        elif r.status == AuthorityStatus.BLOCKED:
            warnings.append(f"{dt}: Authority check skipped ({r.reason})")

    # Determine overall status and review requirement
    # Stage 6 Contract: Only MISMATCH sets review_required = True.
    # NOT_AVAILABLE, BLOCKED, and ERROR are neutral/non-punitive.
    if mismatched_count > 0:
        overall_status = AuthorityStatus.MISMATCH
        review_required = True
        overall_evidence = EvidenceStrength.NONE
        summary = (
            f"Authority record mismatch detected across {mismatched_count} document(s). "
            f"Administrative officer review recommended."
        )
    elif matched_count > 0:
        overall_status = AuthorityStatus.MATCH
        review_required = False
        # Calculate composite evidence strength
        strengths = [r.evidence_strength for r in document_results.values() if r.status == AuthorityStatus.MATCH]
        if EvidenceStrength.STRONG in strengths:
            overall_evidence = EvidenceStrength.STRONG
        elif EvidenceStrength.MODERATE in strengths:
            overall_evidence = EvidenceStrength.MODERATE
        else:
            overall_evidence = EvidenceStrength.WEAK

        summary = (
            f"Authoritative record confirmation obtained for {matched_count} document(s). "
            f"Provides supporting evidence."
        )
    elif blocked_count > 0 and (blocked_count + unavailable_count + error_count) == len(document_results):
        if blocked_count == len(document_results):
            overall_status = AuthorityStatus.BLOCKED
            summary = "Authority verification skipped for all documents due to prior stage quality or slot flags."
        else:
            overall_status = AuthorityStatus.BLOCKED
            summary = f"Authority verification partially blocked ({blocked_count} doc(s)) and unavailable."
        review_required = False
        overall_evidence = EvidenceStrength.NONE
    elif error_count > 0 and (error_count + unavailable_count) == len(document_results):
        overall_status = AuthorityStatus.ERROR
        review_required = False
        overall_evidence = EvidenceStrength.NONE
        summary = f"External authority provider experienced technical issues across {error_count} document(s)."
    else:
        # Default prototype state: NOT_AVAILABLE
        overall_status = AuthorityStatus.NOT_AVAILABLE
        review_required = False
        overall_evidence = EvidenceStrength.NONE
        summary = "Authorized external authority provider is not configured for this environment."

    return Stage5VerificationResult(
        overall_status=overall_status,
        overall_evidence_strength=overall_evidence,
        review_required=review_required,
        documents=document_results,
        matched_count=matched_count,
        mismatched_count=mismatched_count,
        unavailable_count=unavailable_count,
        blocked_count=blocked_count,
        error_count=error_count,
        critical_mismatches=critical_mismatches,
        warnings=warnings,
        summary=summary,
        timestamp=datetime.now().isoformat(),
        stage_version=STAGE5_VERSION,
    )
