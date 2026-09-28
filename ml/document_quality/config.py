"""
VeriCampus AI — Document Quality Gate Configuration
Central single source of truth for quality thresholds, feature definitions, and model parameters.
"""
from pathlib import Path

# Paths
MODULE_DIR = Path(__file__).resolve().parent
ML_ROOT = MODULE_DIR.parent
DEFAULT_MODEL_DIR = ML_ROOT / "models"
DEFAULT_MODEL_PATH = DEFAULT_MODEL_DIR / "quality_gate_model.joblib"
DEFAULT_META_PATH = DEFAULT_MODEL_DIR / "feature_meta.json"

# Model metadata
MODEL_VERSION = "1.0.0-rf-baseline"
MODEL_NAME = "RandomForestQualityGate"

# Quality Score Thresholds (Configurable central definitions)
# 85.0 - 100.0: HIGH
# 70.0 - 84.99: ACCEPTABLE
#  0.0 - 69.99: LOW / UNREADABLE
HIGH_THRESHOLD = 85.0
ACCEPTABLE_THRESHOLD = 70.0
LOW_THRESHOLD = 0.0

# Reupload cutoff: score strictly below 70.0 triggers REUPLOAD_REQUIRED
REUPLOAD_REQUIRED_CUTOFF = 70.0

# 10 Concrete, interpretable features used by the ML model & heuristic scorer
QUALITY_FEATURE_NAMES = [
    "resolution_megapixels",    # Total image megapixels (width * height / 1M)
    "blur_laplacian_variance",  # Variance of Laplacian operator (sharpness)
    "normalized_sharpness",     # Scaled sharpness score (0 - 100)
    "brightness_mean",          # Mean luminance of image (0 - 255)
    "brightness_std",           # Uniformity / standard deviation of brightness
    "contrast_rms",             # Root-mean-square contrast of gray channel
    "noise_estimate_sigma",     # High-frequency noise estimation (residual vs median)
    "skew_angle_degrees",       # Absolute skew / rotation angle in degrees
    "crop_margin_completeness", # Estimated border integrity / lack of edge cutoff (0 - 1)
    "ocr_confidence",           # OCR average character/line confidence (0 - 1)
]

# Physical bounds for sanity checks
MIN_ACCEPTABLE_WIDTH = 300
MIN_ACCEPTABLE_HEIGHT = 300
OPTIMAL_RESOLUTION_MP = 0.88  # Approx 800x1100

# Training defaults
DEFAULT_N_ESTIMATORS = 100
DEFAULT_MAX_DEPTH = 8
DEFAULT_RANDOM_STATE = 42
