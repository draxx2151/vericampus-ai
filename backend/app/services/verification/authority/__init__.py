"""
VeriCampus AI — Stage 5: Authority Verification Provider Architecture
Bridge to ml.authority_verification package.
"""
from ml.authority_verification import (
    AuthorityVerificationProvider,
    AuthorityVerificationResult,
    AuthorityStatus,
    UnavailableProvider,
    DigiLockerProvider,
    NADProvider,
    IssuerProvider,
    AuthorityVerificationService,
)

__all__ = [
    "AuthorityVerificationProvider",
    "AuthorityVerificationResult",
    "AuthorityStatus",
    "DigiLockerProvider",
    "NADProvider",
    "IssuerProvider",
    "UnavailableProvider",
    "AuthorityVerificationService",
]
