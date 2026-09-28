"""
VeriCampus AI — Stage 5: Base Authority Provider Contract
Abstract interface for authoritative government and institutional verification sources.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from .schemas import AuthorityVerificationResult


class AuthorityVerificationProvider(ABC):
    """
    Abstract interface for authoritative verification providers
    (DigiLocker, National Academic Depository, State/Board Issuers, etc.).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this authority provider."""
        pass

    @property
    def provider_version(self) -> str:
        """Version of the provider implementation."""
        return "1.0.0"

    @abstractmethod
    def is_available(self) -> bool:
        """
        Returns True only if the provider has legitimate, verified production
        credentials, endpoint URLs, and certificates configured.
        """
        pass

    @abstractmethod
    def verify(
        self,
        document_type: str,
        extracted_fields: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AuthorityVerificationResult:
        """
        Executes external authority verification for a document.

        Args:
            document_type: Slot document type (e.g. government_id, marksheet, etc.)
            extracted_fields: Structured fields extracted from Stage 3 OCR
            context: Additional applicant or application metadata

        Returns:
            Structured AuthorityVerificationResult
        """
        pass

    def verify_document(
        self,
        document_type: Any,
        extracted_fields: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AuthorityVerificationResult:
        """
        Convenience alias for verify accepting enum or string document_type.
        """
        doc_str = getattr(document_type, "value", str(document_type))
        return self.verify(
            document_type=doc_str,
            extracted_fields=extracted_fields or {},
            context=context,
            **kwargs,
        )

