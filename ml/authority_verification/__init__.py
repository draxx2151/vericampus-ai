"""
VeriCampus AI — Stage 5: Authority Verification Package
Provides modular external authority verification abstractions, field matching,
and evidence synthesis for scholarship verification.
"""
from .schemas import (
    AuthorityStatus,
    EvidenceStrength,
    ConsentStatus,
    RecordStatus,
    FieldMatchStatus,
    FieldComparisonResult,
    AuthorityVerificationResult,
    Stage5VerificationResult,
)
from .base import AuthorityVerificationProvider
from .providers.unavailable import UnavailableProvider
from .providers.digilocker import DigiLockerProvider
from .providers.nad import NADProvider
from .providers.issuer import IssuerProvider
from .service import AuthorityVerificationService
from .config import (
    STAGE5_VERSION,
    AUTHORITY_PROVIDER_TIMEOUT_SECONDS,
    AUTHORITY_PROVIDER_MAX_RETRIES,
)

__all__ = [
    "AuthorityStatus",
    "EvidenceStrength",
    "ConsentStatus",
    "RecordStatus",
    "FieldMatchStatus",
    "FieldComparisonResult",
    "AuthorityVerificationResult",
    "Stage5VerificationResult",
    "AuthorityVerificationProvider",
    "UnavailableProvider",
    "DigiLockerProvider",
    "NADProvider",
    "IssuerProvider",
    "AuthorityVerificationService",
    "STAGE5_VERSION",
    "AUTHORITY_PROVIDER_TIMEOUT_SECONDS",
    "AUTHORITY_PROVIDER_MAX_RETRIES",
]
