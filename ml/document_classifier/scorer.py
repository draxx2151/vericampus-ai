"""
VeriCampus AI — Document Classification Heuristic Scorer & Reason Generator
Provides deterministic evaluation, confidence thresholding, and mismatch detection.
"""
from typing import Dict, List, Tuple, Optional
from .config import (
    CONFIDENCE_THRESHOLD_PASS,
    CONFIDENCE_THRESHOLD_WARNING,
    TARGET_CLASSES,
    MODEL_VERSION,
)
from .schemas import (
    ClassificationStatus,
    ClassificationAlternative,
    DocumentClassificationResult,
)


def evaluate_features_heuristic(
    features: Dict[str, float],
) -> Tuple[str, float, List[ClassificationAlternative], List[str]]:
    """
    Deterministic rule-based classification fallback based on structural cues:
    - High table/grid density and horizontal line count -> MARKSHEET
    - Photo box detected + low vertical lines -> GOVERNMENT_ID
    - Official seal circle in lower section + revenue keyword cues -> INCOME_CERTIFICATE
    - Domicile keywords + high upper-mid density without tables -> DOMICILE_CERTIFICATE
    - Extremely low ink (blank) or high receipt strip -> UNKNOWN
    """
    scores = {cls_name: 0.10 for cls_name in TARGET_CLASSES}
    reasons = []

    # 1. Total ink check (Blank paper detection)
    if features.get("total_ink_ratio", 0.0) < 0.012:
        scores["UNKNOWN"] += 0.80
        reasons.append("Very low foreground ink detected; document resembles blank paper or empty page.")

    # 2. Table / Grid Structure (Strong indicator for Marksheets)
    h_lines = features.get("line_count_horizontal", 0.0)
    v_lines = features.get("line_count_vertical", 0.0)
    grid_density = features.get("table_grid_density", 0.0)

    if h_lines >= 4 and (v_lines >= 2 or grid_density > 0.0001):
        scores["MARKSHEET"] += 0.70
        reasons.append(f"Tabular grade/marks grid structure detected ({int(h_lines)} horizontal rows, {int(v_lines)} vertical columns).")
    elif h_lines >= 2 and features.get("kw_marksheet", 0.0) > 0.2:
        scores["MARKSHEET"] += 0.50

    # 3. Photo Box & ID format (Strong indicator for Government ID)
    if features.get("photo_box_detected", 0.0) > 0.5:
        scores["GOVERNMENT_ID"] += 0.65
        reasons.append("Identification photograph placeholder box detected on document canvas.")
    if features.get("kw_govt_id", 0.0) > 0.25:
        scores["GOVERNMENT_ID"] += 0.45

    # 4. Revenue Seal Circle & Income Proclamation (Income Certificate)
    if features.get("seal_circle_detected", 0.0) > 0.5:
        scores["INCOME_CERTIFICATE"] += 0.55
        reasons.append("Official circular revenue authority seal detected in lower document quadrant.")
    if features.get("kw_income", 0.0) > 0.25:
        scores["INCOME_CERTIFICATE"] += 0.50

    # 5. Domicile & State Declarations (Domicile Certificate)
    if features.get("kw_domicile", 0.0) > 0.25:
        scores["DOMICILE_CERTIFICATE"] += 0.60
        reasons.append("State domicile legal declaration structure identified.")

    # 6. Unrelated / Commercial cues (UNKNOWN)
    if features.get("kw_unknown", 0.0) > 0.25:
        scores["UNKNOWN"] += 0.70
        reasons.append("Keywords correspond to non-academic commercial or recreational documentation.")

    # Normalize scores to pseudo-probabilities
    total_score = sum(scores.values())
    probs = {k: v / max(1e-5, total_score) for k, v in scores.items()}

    sorted_classes = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    top_class, top_conf = sorted_classes[0]

    alternatives = [
        ClassificationAlternative(document_type=cls_name, confidence=round(prob, 3))
        for cls_name, prob in sorted_classes
    ]

    return top_class, round(top_conf, 3), alternatives, reasons


def map_prediction_to_result(
    predicted_type: str,
    confidence: float,
    alternatives: List[ClassificationAlternative],
    expected_type: Optional[str] = None,
    reasons: Optional[List[str]] = None,
    features_summary: Optional[Dict] = None,
    is_fallback: bool = False,
) -> DocumentClassificationResult:
    """
    Evaluates operational status (PASS, WARNING, UNKNOWN, DOCUMENT_TYPE_MISMATCH)
    against the configured single-source-of-truth thresholds.
    """
    effective_reasons = list(reasons or [])

    # Format human-readable names for messages
    pred_display = predicted_type.replace("_", " ").title()
    exp_display = expected_type.replace("_", " ").title() if expected_type else None

    # Check document type match against expected slot
    type_match = None
    if expected_type is not None:
        type_match = (predicted_type == expected_type)

    # 1. Unknown or Insufficient Confidence Thresholding
    if predicted_type == "UNKNOWN" or confidence < CONFIDENCE_THRESHOLD_WARNING:
        status = ClassificationStatus.UNKNOWN
        type_match = False if expected_type else None
        effective_reasons.append(
            f"Uploaded document could not be reliably classified (confidence: {confidence:.1%}). "
            "Please ensure the document is clear and matches the required scholarship document type."
        )
    # 2. Document Type Mismatch Detection
    elif expected_type is not None and not type_match:
        status = ClassificationStatus.DOCUMENT_TYPE_MISMATCH
        effective_reasons.append(
            f"Document Type Mismatch: Uploaded document appears to be {pred_display} "
            f"(confidence: {confidence:.1%}), but expected {exp_display}. "
            "Please upload the correct document."
        )
    # 3. High Confidence Match (>= 85%)
    elif confidence >= CONFIDENCE_THRESHOLD_PASS:
        status = ClassificationStatus.PASS
        effective_reasons.append(f"Document successfully classified as {pred_display} (confidence: {confidence:.1%}).")
    # 4. Moderate Confidence Match (70% - 84.99%)
    else:
        status = ClassificationStatus.WARNING
        effective_reasons.append(
            f"Document classified as {pred_display} with moderate confidence ({confidence:.1%}). "
            "Soft flag assigned for administrative review verification."
        )

    return DocumentClassificationResult(
        predicted_type=predicted_type,
        confidence=round(confidence, 3),
        classification_status=status,
        alternatives=alternatives,
        expected_type=expected_type,
        type_match=type_match,
        model_version=MODEL_VERSION,
        reasons=effective_reasons,
        features_summary=features_summary or {},
        is_fallback=is_fallback,
    )
