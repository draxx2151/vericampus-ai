"""
VeriCampus AI — Stage 5: Authority Verification Configuration
Operational configurations, thresholds, evidence weights, and provider parameters.
All thresholds are prototype operational heuristics.
"""
from typing import Dict, Any

# Package & Engine Version
STAGE5_VERSION = "stage5_authority_verification_v1"

# Provider Timeout & Retry Settings
AUTHORITY_PROVIDER_TIMEOUT_SECONDS: float = 5.0
AUTHORITY_PROVIDER_MAX_RETRIES: int = 2
AUTHORITY_PROVIDER_BACKOFF_FACTOR: float = 0.5

# Field Matching Tolerances
NAME_SIMILARITY_THRESHOLD: float = 0.85
MARKS_SUM_TOLERANCE: float = 2.0
PERCENTAGE_TOLERANCE: float = 1.0
INCOME_TOLERANCE_INR: float = 1000.0

# Supported Authority Providers
PROVIDER_UNAVAILABLE = "unavailable"
PROVIDER_DIGILOCKER = "digilocker"
PROVIDER_NAD = "nad"
PROVIDER_ISSUER = "issuer"

# Evidence Strength Hierarchy
# Prototype weights used for downstream Stage 6 evidence synthesis
EVIDENCE_STRENGTH_WEIGHTS: Dict[str, float] = {
    "STRONG": 1.0,
    "MODERATE": 0.6,
    "WEAK": 0.2,
    "NONE": 0.0,
}

# Audit Event Types
EVENT_AUTHORITY_VERIFICATION_STARTED = "AUTHORITY_VERIFICATION_STARTED"
EVENT_AUTHORITY_VERIFICATION_MATCH = "AUTHORITY_VERIFICATION_MATCH"
EVENT_AUTHORITY_VERIFICATION_MISMATCH = "AUTHORITY_VERIFICATION_MISMATCH"
EVENT_AUTHORITY_VERIFICATION_UNAVAILABLE = "AUTHORITY_VERIFICATION_UNAVAILABLE"
EVENT_AUTHORITY_VERIFICATION_BLOCKED = "AUTHORITY_VERIFICATION_BLOCKED"
EVENT_AUTHORITY_VERIFICATION_ERROR = "AUTHORITY_VERIFICATION_ERROR"
