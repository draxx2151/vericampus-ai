from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field

from app.db.models.enums import DocumentType


class ReadabilityScore(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNREADABLE = "UNREADABLE"


class GovernmentIdExtraction(BaseModel):
    id_type: Optional[str] = Field(None, description="Type of Government ID, e.g. AADHAAR, PAN, VOTER_ID")
    id_number: Optional[str] = Field(None, description="Government Identification Number")
    full_name: Optional[str] = Field(None, description="Full name as printed on ID")
    date_of_birth: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD or printed format")
    gender: Optional[str] = Field(None, description="Gender (e.g. MALE, FEMALE, OTHER)")
    address: Optional[str] = Field(None, description="Residential address on ID")


class MarksheetExtraction(BaseModel):
    candidate_name: Optional[str] = Field(None, description="Student/Candidate full name")
    roll_number: Optional[str] = Field(None, description="Examination roll or seat number")
    exam_name: Optional[str] = Field(None, description="Exam title (e.g. HSC, SSC, Class 12)")
    passing_year: Optional[int] = Field(None, description="Year of examination completion")
    total_marks: Optional[float] = Field(None, description="Total marks secured")
    max_marks: Optional[float] = Field(None, description="Maximum total aggregate marks")
    percentage: Optional[float] = Field(None, description="Aggregate score percentage")
    result_status: Optional[str] = Field(None, description="Result classification (e.g. PASS, DISTINCTION)")


class IncomeCertificateExtraction(BaseModel):
    applicant_name: Optional[str] = Field(None, description="Applicant or family head name")
    father_guardian_name: Optional[str] = Field(None, description="Father or legal guardian name")
    annual_income_inr: Optional[float] = Field(None, description="Total annual family income in INR")
    certificate_number: Optional[str] = Field(None, description="Government certificate bar/serial number")
    issuing_authority: Optional[str] = Field(None, description="Designation of issuing officer (e.g. Tahsildar)")
    issue_date: Optional[str] = Field(None, description="Date of certificate issuance")
    financial_year: Optional[str] = Field(None, description="Applicable financial year (e.g. 2023-2024)")


class DomicileCertificateExtraction(BaseModel):
    candidate_name: Optional[str] = Field(None, description="Candidate name as certified")
    state: Optional[str] = Field(None, description="State of domicile (e.g. Maharashtra)")
    is_maharashtra_domicile: Optional[bool] = Field(None, description="Whether state is confirmed as Maharashtra")
    certificate_number: Optional[str] = Field(None, description="Domicile certificate serial number")
    issue_date: Optional[str] = Field(None, description="Date of certificate issuance")


# Union type of all 4 document-specific extractions
ExtractedFieldsType = Union[
    GovernmentIdExtraction,
    MarksheetExtraction,
    IncomeCertificateExtraction,
    DomicileCertificateExtraction,
]


class DocumentExtractionResult(BaseModel):
    document_type: DocumentType
    extraction_success: bool = Field(True, description="Whether the extraction process succeeded")
    readability: ReadabilityScore = Field(ReadabilityScore.HIGH, description="Readability/quality tier")
    warnings: List[str] = Field(default_factory=list, description="Warning messages or extraction issues")
    extracted_fields: Optional[ExtractedFieldsType] = Field(None, description="Typed structured fields")
    field_extraction: Optional[Any] = Field(None, description="Stage 3 structured field extraction result")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Operational extraction metadata")


class BaseAIVerifier(ABC):
    """
    Abstract contract for document verification engines (Mock, Gemini, OCR, etc.).
    Extracts structured fields according to document type without exposing raw engine internals.
    """

    @abstractmethod
    def extract_document(
        self,
        file_path: Union[str, Path],
        document_type: DocumentType,
        **kwargs: Any
    ) -> DocumentExtractionResult:
        """
        Extract structured data from a physical document file.

        Args:
            file_path: Path to the physical document file on disk.
            document_type: Target DocumentType enum member.
            **kwargs: Provider-specific execution options.

        Returns:
            DocumentExtractionResult containing structured fields and quality indicators.
        """
        pass
