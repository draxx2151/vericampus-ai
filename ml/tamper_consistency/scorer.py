"""
VeriCampus AI — Stage 4: Hierarchical Evidence Scorer
Implements bounded, explainable scoring separating Strong, Moderate, and Weak evidence.
Strong factual contradictions (DOB / ID / Marksheet math mismatches) decisively trigger NEEDS_REVIEW.
Weak optical / compression artifacts never independently flag fraud.
"""
from typing import List, Tuple, Dict, Any

from .schemas import (
    TamperSignal,
    ConsistencyCheckResult,
    CheckStatus,
    SignalSeverity,
    EvidenceStrength,
)
from .config import (
    STAGE4_PASS_THRESHOLD,
    STAGE4_WARNING_THRESHOLD,
    EVIDENCE_WEIGHTS,
)


def score_tamper_signals(
    signals: List[TamperSignal]
) -> Tuple[float, CheckStatus, List[str], List[str]]:
    """
    Computes consolidated tamper score and status.
    Returns: (score, status, warnings, reasons)
    """
    if not signals:
        return 100.0, CheckStatus.PASS, [], ["No document manipulation signals detected."]

    # If all signals were NOT_AVAILABLE
    available_signals = [s for s in signals if s.status != CheckStatus.NOT_AVAILABLE]
    if not available_signals:
        return 100.0, CheckStatus.NOT_AVAILABLE, [], ["Tamper analysis was not available for uploaded documents."]

    # Base score is 100
    deductions = 0.0
    warnings: List[str] = []
    reasons: List[str] = []
    has_high_severity = False
    has_warning = False

    for s in available_signals:
        if s.status == CheckStatus.WARNING or s.status == CheckStatus.NEEDS_REVIEW:
            has_warning = True
            warnings.append(f"[{s.category.value}] {s.explanation}")

            if s.severity == SignalSeverity.CRITICAL:
                deductions += 40.0
                has_high_severity = True
            elif s.severity == SignalSeverity.HIGH:
                deductions += 25.0
                has_high_severity = True
            elif s.severity == SignalSeverity.MEDIUM:
                deductions += 15.0
            elif s.severity == SignalSeverity.LOW:
                # Weak signals e.g. software metadata or mild blur ratio
                deductions += 6.0
            else:
                deductions += 2.0
        elif s.status == CheckStatus.PASS:
            pass

    score = max(0.0, min(100.0, 100.0 - deductions))

    if has_high_severity or score < STAGE4_WARNING_THRESHOLD:
        status = CheckStatus.NEEDS_REVIEW
        reasons.append(f"Elevated visual/structural anomalies observed (cleanliness score {score:.1f}).")
    elif has_warning or score < STAGE4_PASS_THRESHOLD:
        status = CheckStatus.WARNING
        reasons.append(f"Advisory optical or metadata signals flagged for administrative review (cleanliness score {score:.1f}).")
    else:
        status = CheckStatus.PASS
        reasons.append(f"Documents exhibit consistent visual and structural properties (cleanliness score {score:.1f}).")

    return round(score, 1), status, warnings, reasons


def score_consistency_checks(
    checks: List[ConsistencyCheckResult]
) -> Tuple[float, CheckStatus, List[str], List[str], List[str]]:
    """
    Computes consolidated cross-document consistency score and status.
    Returns: (score, status, warnings, critical_inconsistencies, explanations)
    """
    if not checks:
        return 100.0, CheckStatus.NOT_AVAILABLE, [], [], ["No cross-document consistency checks performed."]

    available_checks = [c for c in checks if c.status != CheckStatus.NOT_AVAILABLE]
    if not available_checks:
        return 100.0, CheckStatus.NOT_AVAILABLE, [], [], ["Cross-document comparisons not available due to missing fields."]

    deductions = 0.0
    warnings: List[str] = []
    critical_inconsistencies: List[str] = []
    explanations: List[str] = []

    for c in available_checks:
        if c.is_critical or c.status == CheckStatus.NEEDS_REVIEW:
            critical_inconsistencies.append(c.reason)
            # Critical identity or arithmetic contradictions heavily penalize consistency
            deductions += 35.0
        elif c.status == CheckStatus.WARNING:
            warnings.append(c.reason)
            deductions += 12.0
        else:
            explanations.append(c.reason)

    score = max(0.0, min(100.0, 100.0 - deductions))

    if critical_inconsistencies or score < STAGE4_WARNING_THRESHOLD:
        status = CheckStatus.NEEDS_REVIEW
    elif warnings or score < STAGE4_PASS_THRESHOLD:
        status = CheckStatus.WARNING
    else:
        status = CheckStatus.PASS

    return round(score, 1), status, warnings, critical_inconsistencies, explanations


def score_stage4_overall(
    tamper_score: float,
    tamper_status: CheckStatus,
    consistency_score: float,
    consistency_status: CheckStatus,
    critical_inconsistencies: List[str],
    warnings: List[str]
) -> Tuple[float, CheckStatus, bool, List[str]]:
    """
    Blends consistency (70%) and tamper cleanliness (30%) into Stage 4 overall score.
    Returns: (overall_score, overall_status, review_required, reasons)
    """
    # If consistency has active comparisons, weight it 70/30; otherwise fallback to tamper score
    if consistency_status != CheckStatus.NOT_AVAILABLE:
        overall_score = round((0.70 * consistency_score) + (0.30 * tamper_score), 1)
    else:
        overall_score = tamper_score

    reasons: List[str] = []
    review_required = False

    if critical_inconsistencies:
        overall_status = CheckStatus.NEEDS_REVIEW
        review_required = True
        reasons.append(f"Stage 4 flagged {len(critical_inconsistencies)} critical cross-document contradiction(s). Administrative review required.")
    elif overall_score < STAGE4_WARNING_THRESHOLD:
        overall_status = CheckStatus.NEEDS_REVIEW
        review_required = True
        reasons.append(f"Stage 4 composite verification score ({overall_score:.1f}) is below review threshold ({STAGE4_WARNING_THRESHOLD}).")
    elif overall_score < STAGE4_PASS_THRESHOLD or warnings or tamper_status == CheckStatus.WARNING or consistency_status == CheckStatus.WARNING:
        overall_status = CheckStatus.WARNING
        review_required = False  # Warning signals inform officer but don't strictly halt processing
        reasons.append(f"Stage 4 identified {len(warnings)} non-critical advisory signal(s) (composite score {overall_score:.1f}).")
    else:
        overall_status = CheckStatus.PASS
        review_required = False
        reasons.append(f"Stage 4 cross-document consistency and tamper analysis passed cleanly (score {overall_score:.1f}).")

    return overall_score, overall_status, review_required, reasons
