"""
VeriCampus AI — Document Classifier Configuration
Central source of truth for classification thresholds, classes, and model parameters.
"""
from pathlib import Path

# Paths
MODULE_ROOT = Path(__file__).resolve().parent
ML_ROOT = MODULE_ROOT.parent
DEFAULT_MODEL_PATH = ML_ROOT / "models" / "document_classifier_model.joblib"
DEFAULT_DATASET_DIR = ML_ROOT / "datasets" / "run_n10_seed42"

# Target classes (4 required scholarship documents + UNKNOWN / OTHER)
TARGET_CLASSES = [
    "GOVERNMENT_ID",
    "MARKSHEET",
    "INCOME_CERTIFICATE",
    "DOMICILE_CERTIFICATE",
    "UNKNOWN",
]

# Operational Confidence Thresholds (Single Source of Truth)
# >= 0.85 -> PASS (High confidence classification)
# >= 0.70 and < 0.85 -> WARNING (Moderate confidence, soft review flag)
# < 0.70 -> UNKNOWN (Insufficient certainty for automated decision)
CONFIDENCE_THRESHOLD_PASS = 0.85
CONFIDENCE_THRESHOLD_WARNING = 0.70

# Model Metadata
MODEL_VERSION = "document_classifier_v1"
MODEL_ALGORITHM = "RandomForestClassifier(n_estimators=100, max_depth=8)"

# Class Mapping
CLASS_TO_IDX = {cls_name: idx for idx, cls_name in enumerate(TARGET_CLASSES)}
IDX_TO_CLASS = {idx: cls_name for idx, cls_name in enumerate(TARGET_CLASSES)}
