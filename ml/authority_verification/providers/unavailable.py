"""
VeriCampus AI — Stage 5: Unavailable Authority Provider (Default Prototype)
Default operational provider when no legitimate external authority is configured.
Strictly returns NOT_AVAILABLE without making external network calls or fabricating data.
"""
import uuid
from typing import Dict, Any, Optional

from ml.authority_verification.base import AuthorityVerificationProvider
from ml.authority_verification.schemas import (
    AuthorityVerificationResult,
    AuthorityStatus,
    EvidenceStrength,
    ConsentStatus,
    RecordStatus,
)


class UnavailableProvider(AuthorityVerificationProvider):
    """
    Default authority verification provider for current development and prototype environments.
    Strictly offline-safe; guarantees zero external network calls.
    """

    @property
    def provider_name(self) -> str:
        return "unavailable"



    @property
    def provider_version(self) -> str:
        return "1.0.0"

    def is_available(self) -> bool:
        # Strictly False until a legitimate provider is configured
        return False

    def verify(
        self,
        document_type: str,
        extracted_fields: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AuthorityVerificationResult:
        verification_id = f"av-{uuid.uuid4().hex[:12]}"
        return AuthorityVerificationResult(
            document_type=document_type,
            provider=self.provider_name,
            provider_version=self.provider_version,
            verification_id=verification_id,
            status=AuthorityStatus.NOT_AVAILABLE,
            evidence_strength=EvidenceStrength.NONE,
            consent_status=ConsentStatus.NOT_REQUIRED,
            record_status=RecordStatus.NOT_AVAILABLE,
            verified_fields=[],
            matched_fields=[],
            mismatched_fields=[],
            field_comparisons={},
            reference_id=None,
            confidence=None,
            reason="Authorized authority provider is not configured for this environment.",
            is_available=False,
            raw_response_available=False,
        )
