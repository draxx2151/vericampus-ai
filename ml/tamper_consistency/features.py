"""
VeriCampus AI — Stage 4: Tabular ML Feature Extraction
Flattens Stage 4 visual signals and cross-document consistency results into
standardized numeric feature vectors for downstream machine learning models (GBDT / Random Forest).
"""
from typing import Dict, Any, List, Optional
import numpy as np

from .schemas import TamperSignal, ConsistencyCheckResult, CheckStatus


FEATURE_NAMES = [
    "name_consistency_score",
    "name_mismatch_flag",
    "dob_mismatch_flag",
    "id_mismatch_flag",
    "marks_math_error_flag",
    "marks_percentage_error_flag",
    "future_date_flag",
    "chronological_sanity_score",
    "ela_anomaly_score",
    "local_blur_anomaly_score",
    "noise_variance_anomaly_score",
    "copy_move_flag",
    "bbox_overlap_flag",
    "software_metadata_flag",
    "total_critical_inconsistencies",
    "total_warning_signals",
]


def extract_features_from_assessments(
    tamper_signals: List[TamperSignal],
    consistency_checks: List[ConsistencyCheckResult]
) -> Dict[str, float]:
    """
    Extracts a tabular dictionary of float features suitable for ML classifiers.
    """
    feat: Dict[str, float] = {k: 0.0 for k in FEATURE_NAMES}

    # Consistency Features
    critical_count = 0
    warning_count = 0

    for chk in consistency_checks:
        if chk.is_critical or chk.status == CheckStatus.NEEDS_REVIEW:
            critical_count += 1
        elif chk.status == CheckStatus.WARNING:
            warning_count += 1

        name = chk.check_name.lower()
        if "name_consistency" in name:
            if chk.status == CheckStatus.PASS:
                feat["name_consistency_score"] = max(feat["name_consistency_score"], 100.0)
            elif chk.status == CheckStatus.WARNING:
                feat["name_consistency_score"] = max(feat["name_consistency_score"], 65.0)
            elif chk.status == CheckStatus.NEEDS_REVIEW:
                feat["name_mismatch_flag"] = 1.0

        if "dob_consistency" in name:
            if chk.status == CheckStatus.NEEDS_REVIEW:
                feat["dob_mismatch_flag"] = 1.0

        if "id_consistency" in name:
            if chk.status == CheckStatus.NEEDS_REVIEW:
                feat["id_mismatch_flag"] = 1.0

        if "marksheet" in name:
            if chk.status == CheckStatus.NEEDS_REVIEW:
                if "sum" in name or "bounds" in name:
                    feat["marks_math_error_flag"] = 1.0
                if "percentage" in name:
                    feat["marks_percentage_error_flag"] = 1.0

        if "future_date" in name and chk.status == CheckStatus.NEEDS_REVIEW:
            feat["future_date_flag"] = 1.0

        if "dob_vs_passing_year" in name:
            feat["chronological_sanity_score"] = 100.0 if chk.status == CheckStatus.PASS else 0.0

    # Tamper Features
    for sig in tamper_signals:
        s_name = sig.signal_name.lower()
        if sig.status == CheckStatus.WARNING:
            warning_count += 1

        if "ela" in s_name:
            feat["ela_anomaly_score"] = float(sig.score)
        elif "blur" in s_name:
            feat["local_blur_anomaly_score"] = float(sig.score)
        elif "noise" in s_name:
            feat["noise_variance_anomaly_score"] = float(sig.score)
        elif "copy_move" in s_name and sig.status == CheckStatus.WARNING:
            feat["copy_move_flag"] = 1.0
        elif "overlap" in s_name and sig.status == CheckStatus.WARNING:
            feat["bbox_overlap_flag"] = 1.0
        elif "software" in s_name and sig.status == CheckStatus.WARNING:
            feat["software_metadata_flag"] = 1.0

    feat["total_critical_inconsistencies"] = float(critical_count)
    feat["total_warning_signals"] = float(warning_count)

    return feat


def extract_feature_vector(
    tamper_signals: List[TamperSignal],
    consistency_checks: List[ConsistencyCheckResult]
) -> np.ndarray:
    """Returns the features as a dense 1D numpy array ordered by FEATURE_NAMES."""
    feat_dict = extract_features_from_assessments(tamper_signals, consistency_checks)
    return np.array([feat_dict[k] for k in FEATURE_NAMES], dtype=np.float32)
