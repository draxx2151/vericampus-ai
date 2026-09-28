"""
VeriCampus AI — Stage 4: Tamper Detection & Cross-Document Consistency Configuration
Defines prototype thresholds, evidence weights, and operational parameters.
NOTE: These thresholds are prototype operational heuristics, not claimed as scientifically validated constants.
"""
from typing import Dict, Any

STAGE4_VERSION = "1.0.0"

# ─── COMBINED STAGE 4 OPERATIONAL THRESHOLDS ──────────────────────────
# Score range: 0.0 to 100.0 (higher = cleaner, higher consistency, lower tamper likelihood)
STAGE4_PASS_THRESHOLD = 80.0
STAGE4_WARNING_THRESHOLD = 60.0

# ─── EVIDENCE-AWARE HIERARCHICAL WEIGHTS ──────────────────────────────
# Strong evidence should carry decisive weight; weak visual artifacts must not overpower legitimate documents.
EVIDENCE_WEIGHTS = {
    # Strong Evidence (factual contradictions)
    "dob_mismatch": 0.35,
    "id_number_mismatch": 0.30,
    "marksheet_arithmetic_contradiction": 0.25,
    
    # Moderate Evidence (significant divergence)
    "name_mismatch": 0.20,
    "certificate_date_anachronism": 0.15,
    "visual_insertion_splice": 0.15,
    "marksheet_percentage_discrepancy": 0.10,
    
    # Weak Evidence (optical/compression anomalies)
    "compression_ela_anomaly": 0.05,
    "localized_blur_inconsistency": 0.05,
    "noise_variance_anomaly": 0.05,
    "metadata_editing_software": 0.03,
}

# ─── CONSISTENCY SCORING WEIGHTS ─────────────────────────────────────
CONSISTENCY_FIELD_WEIGHTS = {
    "name": 0.30,
    "dob": 0.30,
    "government_id": 0.20,
    "marksheet_math": 0.10,
    "certificate_dates": 0.10,
}

# ─── TAMPER DETECTION PARAMETERS ─────────────────────────────────────
# ELA (Error Level Analysis)
ELA_RESCALE = 15.0
ELA_QUALITY = 90
ELA_ANOMALY_THRESHOLD = 28.0

# Local Blur / Sharpness Inconsistency
TILE_SIZE = 32
MIN_TILES_FOR_ANALYSIS = 16
BLUR_VARIANCE_RATIO_THRESHOLD = 3.5

# Noise Variance Analysis
NOISE_INCONSISTENCY_THRESHOLD = 2.8

# Copy-Move Block Match Threshold (normalized cross-correlation / distance)
COPY_MOVE_SIMILARITY_THRESHOLD = 0.96
COPY_MOVE_MIN_DISTANCE_PIXELS = 40

# ─── METADATA PARAMETERS ─────────────────────────────────────────────
# Recognized editing software keywords for advisory metadata signals
SUSPICIOUS_SOFTWARE_KEYWORDS = [
    "photoshop", "gimp", "canva", "illustrator", "inkscape",
    "coreldraw", "paint.net", "pixelmator", "acrobat distiller"
]

# Sensitive ID masking constants
MASK_CHARACTER = "*"
VISIBLE_TRAILING_CHARS = 4
