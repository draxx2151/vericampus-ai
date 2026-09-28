"""
VeriCampus AI — Stage 5: Authority Verification Provider Architecture

Contract and models for Stage 5 of the 7-stage verification architecture.
Stage 5 acts as an independent authority signal to the Evidence Engine.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.db.models.enums import DocumentType


class AuthorityStatus(str, Enum):
    VERIFIED = "VERIFIED"
    MISMATCH = "MISMATCH"
    NOT_FOUND = "NOT_FOUND"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class AuthorityVerificationResult(BaseModel):
    provider_name: str = Field(..., description="Name of the authority provider (e.g. DigiLocker, NAD, Issuer)")
    status: AuthorityStatus = Field(AuthorityStatus.NOT_AVAILABLE, description="Authority verification outcome")
    is_available: bool = Field(False, description="Whether the authority provider service is active and accessible")
    issuer_reference: Optional[str] = Field(None, description="External authority issue or transaction identifier")
    verified_data: Dict[str, Any] = Field(default_factory=dict, description="Verified institutional fields if available")
    message: str = Field("Authority verification service is currently not configured or available.", description="Descriptive status message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Operational audit metadata")


class AuthorityVerificationProvider(ABC):
    """
    Abstract interface for authoritative government and institutional verification sources
    (DigiLocker, National Academic Depository (NAD), direct Issuer APIs, etc.).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is legitimately configured with valid production credentials."""
        pass

    @abstractmethod
    def verify_document(
        self,
        document_type: DocumentType,
        document_number: Optional[str] = None,
        student_data: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> AuthorityVerificationResult:
        """
        Queries the authoritative database or returns NOT_AVAILABLE if unconfigured.
        """
        pass
