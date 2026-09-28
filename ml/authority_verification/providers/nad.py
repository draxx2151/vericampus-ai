"""
VeriCampus AI — Stage 5: National Academic Depository (NAD) Authority Provider
Adapter boundary for academic awards and marksheets verification via NAD.
Strictly returns NOT_AVAILABLE until legitimate institutional access is configured.
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


class NADProvider(AuthorityVerificationProvider):
    """
    Adapter boundary for National Academic Depository (NAD) verification.
    Requires institutional API key, academic institution ID, and NAD gateway credentials.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        institution_id: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.institution_id = institution_id
        self.endpoint_url = endpoint_url

    @property
    def provider_name(self) -> str:
        return "nad"

    @property
    def provider_version(self) -> str:
        return "1.0.0"

    def is_available(self) -> bool:
        return bool(self.api_key and self.institution_id and self.endpoint_url)

    def verify(
        self,
        document_type: str,
        extracted_fields: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AuthorityVerificationResult:
        verification_id = f"av-nad-{uuid.uuid4().hex[:10]}"

        if not self.is_available():
            return AuthorityVerificationResult(
                document_type=document_type,
                provider=self.provider_name,
                provider_version=self.provider_version,
                verification_id=verification_id,
                status=AuthorityStatus.NOT_AVAILABLE,
                evidence_strength=EvidenceStrength.NONE,
                consent_status=ConsentStatus.REQUIRED,
                record_status=RecordStatus.NOT_AVAILABLE,
                verified_fields=[],
                matched_fields=[],
                mismatched_fields=[],
                field_comparisons={},
                reference_id=None,
                confidence=None,
                reason="National Academic Depository (NAD) API integration requires authorized institutional credentials.",
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
            consent_status=ConsentStatus.REQUIRED,
            record_status=RecordStatus.NOT_AVAILABLE,
            reason="NAD gateway integration pending institutional access configuration.",
            is_available=True,
        )
