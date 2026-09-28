"""
VeriCampus AI — Stage 5: Unavailable Authority Provider (Default)
Standard default provider when no legitimate external authority is configured.
Strictly returns NOT_AVAILABLE without fabricating verification responses.
"""
from typing import Optional, Dict, Any
from app.db.models.enums import DocumentType
from .base import AuthorityVerificationProvider, AuthorityVerificationResult, AuthorityStatus


class UnavailableProvider(AuthorityVerificationProvider):
    """
    Default authority verification provider.
    Always returns NOT_AVAILABLE to preserve strict verification integrity.
    """

    @property
    def provider_name(self) -> str:
        return "UnavailableProvider"

    def is_available(self) -> bool:
        return False

    def verify_document(
        self,
        document_type: DocumentType,
        document_number: Optional[str] = None,
        student_data: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> AuthorityVerificationResult:
        return AuthorityVerificationResult(
            provider_name=self.provider_name,
            status=AuthorityStatus.NOT_AVAILABLE,
            is_available=False,
            message="No external authority verification provider is currently configured.",
            metadata={"document_type": document_type.value},
        )
