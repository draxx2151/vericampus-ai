"""
VeriCampus AI — Stage 5: DigiLocker Authority Provider
Placeholder for future official DigiLocker API integration.
Returns NOT_AVAILABLE when no legitimate production provider is configured.
"""
from typing import Optional, Dict, Any
from app.db.models.enums import DocumentType
from .base import AuthorityVerificationProvider, AuthorityVerificationResult, AuthorityStatus


class DigiLockerProvider(AuthorityVerificationProvider):
    """
    DigiLocker verification provider for government IDs, marksheets, and domicile certificates.
    Strictly returns NOT_AVAILABLE until legitimate government credentials are provided.
    """

    def __init__(self, api_key: Optional[str] = None, client_id: Optional[str] = None):
        self.api_key = api_key
        self.client_id = client_id

    @property
    def provider_name(self) -> str:
        return "DigiLocker"

    def is_available(self) -> bool:
        # Never fake availability without valid credentials
        return bool(self.api_key and self.client_id)

    def verify_document(
        self,
        document_type: DocumentType,
        document_number: Optional[str] = None,
        student_data: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> AuthorityVerificationResult:
        if not self.is_available():
            return AuthorityVerificationResult(
                provider_name=self.provider_name,
                status=AuthorityStatus.NOT_AVAILABLE,
                is_available=False,
                message="DigiLocker API integration is unconfigured or credentials are not present.",
                metadata={"document_type": document_type.value},
            )
        # Real DigiLocker API calls will be implemented in future phases
        return AuthorityVerificationResult(
            provider_name=self.provider_name,
            status=AuthorityStatus.NOT_AVAILABLE,
            is_available=True,
            message="DigiLocker gateway integration pending official activation.",
        )
