"""
VeriCampus AI — Stage 5: National Academic Depository (NAD) Provider
Placeholder for future official NAD verification integration.
Returns NOT_AVAILABLE when no legitimate institutional credentials are configured.
"""
from typing import Optional, Dict, Any
from app.db.models.enums import DocumentType
from .base import AuthorityVerificationProvider, AuthorityVerificationResult, AuthorityStatus


class NADProvider(AuthorityVerificationProvider):
    """
    NAD verification provider for academic marksheets and degrees.
    Strictly returns NOT_AVAILABLE without legitimate production integration.
    """

    def __init__(self, api_endpoint: Optional[str] = None, institutional_token: Optional[str] = None):
        self.api_endpoint = api_endpoint
        self.institutional_token = institutional_token

    @property
    def provider_name(self) -> str:
        return "National Academic Depository (NAD)"

    def is_available(self) -> bool:
        return bool(self.api_endpoint and self.institutional_token)

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
            message="National Academic Depository (NAD) API is unconfigured.",
            metadata={"document_type": document_type.value},
        )
