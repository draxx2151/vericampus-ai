"""
VeriCampus AI — Document Quality Rule Scorer & Reason Generator
Provides deterministic evaluation and machine-readable explanations
based on extracted physical and optical features.
"""
from typing import List, Tuple
from .config import (
    HIGH_THRESHOLD,
    ACCEPTABLE_THRESHOLD,
    REUPLOAD_REQUIRED_CUTOFF,
    MODEL_VERSION,
)
from .schemas import (
    QualityLevel,
    QualityGateStatus,
    QualityFeatures,
    QualityAssessment,
)


def evaluate_features_rule_based(features: QualityFeatures) -> Tuple[float, List[str]]:
    """
    Computes a deterministic quality score (0.0 - 100.0) and generates
    actionable, machine-readable explanation strings.
    """
    reasons: List[str] = []
    deductions = 0.0

    # 1. Blur / Sharpness check
    # Laplacian variance: >350 excellent, 150-350 acceptable, 50-150 blurry, <50 severe
    if features.blur_laplacian_variance < 40.0:
        deductions += 35.0
        reasons.append("Severe document blur detected; text characters are unreadable.")
    elif features.blur_laplacian_variance < 120.0:
        deductions += 18.0
        reasons.append("Noticeable image blur detected; text clarity is reduced.")
    elif features.blur_laplacian_variance < 200.0:
        deductions += 7.0

    # 2. Exposure & Lighting check (Mean luminance 0-255)
    # Healthy scanned white document: 120 - 253
    if features.brightness_mean < 60.0:
        deductions += 30.0
        reasons.append("Document image is severely underexposed (too dark).")
    elif features.brightness_mean < 100.0:
        deductions += 14.0
        reasons.append("Document image has poor lighting / dark shadows.")
    elif features.brightness_mean > 254.5 and features.contrast_rms < 12.0:
        deductions += 30.0
        reasons.append("Document image is severely overexposed / washed out with glare.")
    elif features.brightness_mean > 253.5 and features.contrast_rms < 18.0:
        deductions += 14.0
        reasons.append("Mild glare or washed-out highlights detected.")

    # 3. Contrast check
    if features.contrast_rms < 18.0:
        deductions += 22.0
        reasons.append("Very low document contrast; difficult to separate text from background.")
    elif features.contrast_rms < 26.0:
        deductions += 10.0
        reasons.append("Sub-optimal document contrast.")

    # 4. Skew / Rotation check
    if features.skew_angle_degrees > 12.0:
        deductions += 20.0
        reasons.append(f"Severe document skew detected ({features.skew_angle_degrees:.1f}° tilt).")
    elif features.skew_angle_degrees > 5.0:
        deductions += 10.0
        reasons.append(f"Moderate document rotation detected ({features.skew_angle_degrees:.1f}° tilt).")

    # 5. Border & Crop Completeness check
    if features.crop_margin_completeness < 0.70:
        deductions += 35.0
        reasons.append("Critical document edges and content are cut off.")
    elif features.crop_margin_completeness < 0.88:
        deductions += 18.0
        reasons.append("Document borders appear partially cropped or clipped.")

    # 6. Resolution / Megapixels check
    if features.resolution_megapixels < 0.20:  # < 0.2 MP (e.g. 400x500)
        deductions += 30.0
        reasons.append("Image resolution is too low for reliable OCR processing.")
    elif features.resolution_megapixels < 0.45:
        deductions += 12.0
        reasons.append("Image resolution is lower than recommended (recommended > 150 DPI).")

    # 7. OCR Confidence check (if OCR was run)
    if features.ocr_confidence < 0.40:
        deductions += 35.0
        reasons.append("OCR character confidence is critically low.")
    elif features.ocr_confidence < 0.70:
        deductions += 15.0
        reasons.append(f"OCR recognition confidence is below optimal threshold ({features.ocr_confidence:.0%}).")

    # 8. High Sensor Noise
    if features.noise_estimate_sigma > 18.0:
        deductions += 15.0
        reasons.append("High visual sensor noise / grain detected.")

    score = max(0.0, min(100.0, 100.0 - deductions))
    return round(score, 2), reasons


def map_score_to_assessment(
    score: float,
    reasons: List[str],
    features_dict: dict,
    model_version: str = MODEL_VERSION,
    is_fallback: bool = False,
) -> QualityAssessment:
    """
    Deterministically maps a numerical quality score to QualityLevel,
    QualityGateStatus, and produces a complete QualityAssessment.
    """
    if score >= HIGH_THRESHOLD:
        level = QualityLevel.HIGH
        status = QualityGateStatus.PASS
    elif score >= ACCEPTABLE_THRESHOLD:
        level = QualityLevel.ACCEPTABLE
        status = QualityGateStatus.WARNING
    elif score >= 40.0:
        level = QualityLevel.LOW
        status = QualityGateStatus.REUPLOAD_REQUIRED
    else:
        level = QualityLevel.UNREADABLE
        status = QualityGateStatus.REUPLOAD_REQUIRED

    # Ensure clear default reason if score is low but no specific reason was triggered
    if status == QualityGateStatus.REUPLOAD_REQUIRED and not reasons:
        reasons.append("Document quality is too low for reliable automated processing. Please upload a clearer document.")

    return QualityAssessment(
        quality_score=score,
        quality_level=level,
        quality_gate_status=status,
        reasons=reasons,
        features=features_dict,
        model_version=model_version,
        is_fallback=is_fallback,
    )
