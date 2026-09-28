"""
VeriCampus AI — Stage 5: Direct Issuer Authority Provider
Placeholder for direct state revenue/tehsildar verification interfaces.
Returns NOT_AVAILABLE when unconfigured.
"""
from typing import Optional, Dict, Any
from app.db.models.enums import DocumentType
from .base import AuthorityVerificationProvider, AuthorityVerificationResult, AuthorityStatus


class IssuerProvider(AuthorityVerificationProvider):
    """
    Direct certificate issuer authority interface (e.g. MahaOnline / Aaple Sarkar).
    Strictly returns NOT_AVAILABLE without legitimate portal credentials.
    """

    def __init__(self, portal_url: Optional[str] = None, auth_secret: Optional[str] = None):
        self.portal_url = portal_url
        self.auth_secret = auth_secret

    @property
    def provider_name(self) -> str:
        return "Direct Issuer Gateway"

    def is_available(self) -> bool:
        return bool(self.portal_url and self.auth_secret)

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
            is_available=self.is_available(),
            message="Direct Issuer Gateway is not configured.",
            metadata={"document_type": document_type.value},
        )
