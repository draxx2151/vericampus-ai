"""
VeriCampus AI — Stage 5: Institutional Issuer Authority Provider
Adapter boundary for direct integration with educational boards, universities, and revenue offices.
Strictly returns NOT_AVAILABLE until legitimate issuer endpoints are configured.
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


class IssuerProvider(AuthorityVerificationProvider):
    """
    Adapter boundary for direct institutional verification APIs
    (Maharashtra State Board, University Exam Registrars, District Tahsildar offices).
    """

    def __init__(
        self,
        issuer_code: Optional[str] = None,
        api_token: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.issuer_code = issuer_code
        self.api_token = api_token
        self.base_url = base_url

    @property
    def provider_name(self) -> str:
        return f"issuer_{self.issuer_code}" if self.issuer_code else "issuer"

    @property
    def provider_version(self) -> str:
        return "1.0.0"

    def is_available(self) -> bool:
        return bool(self.issuer_code and self.api_token and self.base_url)

    def verify(
        self,
        document_type: str,
        extracted_fields: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AuthorityVerificationResult:
        verification_id = f"av-iss-{uuid.uuid4().hex[:10]}"

        if not self.is_available():
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
                reason=f"Direct issuer integration for '{self.provider_name}' is not configured in this environment.",
                is_available=False,
                raw_response_available=False,
            )

        return AuthorityVerificationResult(
            document_type=document_type,
            provider=self.provider_name,
            provider_version=self.provider_version,
            verification_id=verification_id,
            status=AuthorityStatus.NOT_AVAILABLE,
            evidence_strength=EvidenceStrength.NONE,
            consent_status=ConsentStatus.NOT_REQUIRED,
            record_status=RecordStatus.NOT_AVAILABLE,
            reason="Direct issuer connection pending activation.",
            is_available=True,
        )
