"""
VeriCampus AI — Stage 3 Field Extraction Configuration
Defines configurable prototype thresholds, version identifiers, and operational defaults.
NOTE: These thresholds are prototype operational heuristics, not scientifically validated constants.
"""

FIELD_EXTRACTOR_VERSION = "stage3_field_extractor_v1"

# Configurable prototype completeness thresholds
# Ratio of required fields successfully extracted (0.0 - 1.0)
PROTOTYPE_COMPLETENESS_COMPLETE_THRESHOLD = 0.80  # >= 80% required fields -> COMPLETE
PROTOTYPE_COMPLETENESS_PARTIAL_THRESHOLD = 0.40   # 40% - 79.9% required fields -> PARTIAL
# < 40% -> FAILED

# Extraction confidence tiers
FIELD_CONFIDENCE_HIGH = 0.85
FIELD_CONFIDENCE_MEDIUM = 0.65
FIELD_CONFIDENCE_LOW = 0.40

# Stage 1 Quality Threshold for Stage 3 execution
STAGE1_MINIMUM_QUALITY_THRESHOLD = 70.0

# Sensitive field masking mask character
MASK_CHARACTER = "*"
VISIBLE_TRAILING_DIGITS = 4
