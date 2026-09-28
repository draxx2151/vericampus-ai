from enum import Enum
from pathlib import Path
from typing import Optional, Union, Dict, Any

from app.db.models.enums import DocumentType
from app.services.verification.base import (
    BaseAIVerifier,
    ReadabilityScore,
    GovernmentIdExtraction,
    MarksheetExtraction,
    IncomeCertificateExtraction,
    DomicileCertificateExtraction,
    DocumentExtractionResult,
)


class MockScenario(str, Enum):
    SUCCESS = "SUCCESS"
    UNREADABLE = "UNREADABLE"
    INCOMPLETE = "INCOMPLETE"
    FIELD_FAILURE = "FIELD_FAILURE"


class MockAIVerifier(BaseAIVerifier):
    """
    Deterministic mock verification engine for local development, automated testing,
    and offline test suites without external API dependencies or mock database seeds.
    """

    def __init__(self, default_scenario: Union[MockScenario, str] = MockScenario.SUCCESS):
        if isinstance(default_scenario, str):
            try:
                self.default_scenario = MockScenario(default_scenario.upper())
            except ValueError:
                raise ValueError(f"Invalid mock scenario '{default_scenario}'. Valid scenarios: {[s.value for s in MockScenario]}")
        else:
            self.default_scenario = default_scenario

    def extract_document(
        self,
        file_path: Union[str, Path],
        document_type: DocumentType,
        scenario: Optional[Union[MockScenario, str]] = None,
        field_overrides: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> DocumentExtractionResult:
        # 1. Validate Document Type
        if not isinstance(document_type, DocumentType):
            try:
                document_type = DocumentType(document_type)
            except (ValueError, KeyError):
                raise ValueError(
                    f"Unsupported document type '{document_type}'. "
                    f"Expected one of: {[dt.value for dt in DocumentType]}"
                )

        # 2. Determine active scenario
        active_scenario = self.default_scenario
        if scenario is not None:
            if isinstance(scenario, str):
                try:
                    active_scenario = MockScenario(scenario.upper())
                except ValueError:
                    raise ValueError(f"Invalid mock scenario '{scenario}'. Valid scenarios: {[s.value for s in MockScenario]}")
            else:
                active_scenario = scenario

        safe_path = Path(file_path) if file_path else Path("document.pdf")
        metadata: Dict[str, Any] = {
            "provider": "MockAIVerifier",
            "is_mock": True,
            "scenario": active_scenario.value,
            "file_name": safe_path.name,
        }

        # 3. Handle Scenario: UNREADABLE
        if active_scenario == MockScenario.UNREADABLE:
            return DocumentExtractionResult(
                document_type=document_type,
                extraction_success=False,
                readability=ReadabilityScore.UNREADABLE,
                warnings=["Document image/scan is unreadable, blurred, or heavily corrupted."],
                extracted_fields=None,
                metadata=metadata,
            )

        # 4. Handle Scenario: FIELD_FAILURE
        if active_scenario == MockScenario.FIELD_FAILURE:
            return DocumentExtractionResult(
                document_type=document_type,
                extraction_success=False,
                readability=ReadabilityScore.LOW,
                warnings=["Mandatory anchor text and identifier fields could not be located."],
                extracted_fields=None,
                metadata=metadata,
            )

        # 5. Handle Scenario: INCOMPLETE
        if active_scenario == MockScenario.INCOMPLETE:
            extracted = self._generate_incomplete_fields(document_type, field_overrides)
            stage3_res = self._build_stage3_result(document_type, extracted, is_success=True, is_partial=True)
            return DocumentExtractionResult(
                document_type=document_type,
                extraction_success=True,
                readability=ReadabilityScore.MEDIUM,
                warnings=["Certain optional or secondary fields could not be confidently identified."],
                extracted_fields=extracted,
                field_extraction=stage3_res,
                metadata=metadata,
            )

        # 6. Default Scenario: SUCCESS
        extracted = self._generate_success_fields(document_type, field_overrides)
        stage3_res = self._build_stage3_result(document_type, extracted, is_success=True, is_partial=False)
        return DocumentExtractionResult(
            document_type=document_type,
            extraction_success=True,
            readability=ReadabilityScore.HIGH,
            warnings=[],
            extracted_fields=extracted,
            field_extraction=stage3_res,
            metadata=metadata,
        )

    def _build_stage3_result(self, doc_type: DocumentType, extracted_fields: Any, is_success: bool, is_partial: bool = False):
        try:
            from ml.field_extraction.schemas import (
                DocumentFieldExtractionResult, DocumentExtractionStatus, FieldExtractionResult, ExtractionStatus
            )
            if not extracted_fields or not is_success:
                return DocumentFieldExtractionResult(
                    document_type=doc_type.value,
                    extraction_status=DocumentExtractionStatus.FAILED,
                    overall_confidence=0.0,
                    completeness_score=0.0,
                    fields={},
                )
            fields_dict = {}
            for k, v in extracted_fields.model_dump().items():
                status = ExtractionStatus.EXTRACTED if v is not None else ExtractionStatus.NOT_FOUND
                fields_dict[k] = FieldExtractionResult(
                    field_name=k,
                    raw_value=str(v) if v is not None else None,
                    normalized_value=v,
                    confidence=0.95 if v is not None else 0.0,
                    extraction_status=status,
                )
            return DocumentFieldExtractionResult(
                document_type=doc_type.value,
                extraction_status=DocumentExtractionStatus.PARTIAL if is_partial else DocumentExtractionStatus.COMPLETE,
                overall_confidence=0.75 if is_partial else 0.95,
                completeness_score=0.70 if is_partial else 1.0,
                fields=fields_dict,
            )
        except Exception:
            return None

    def _generate_success_fields(
        self,
        doc_type: DocumentType,
        overrides: Optional[Dict[str, Any]] = None
    ):
        data: Dict[str, Any] = {}
        overrides = overrides or {}

        if doc_type == DocumentType.GOVERNMENT_ID:
            data = {
                "id_type": "AADHAAR",
                "id_number": "TEST-1234-5678-9012",
                "full_name": "Test Student",
                "date_of_birth": "2004-01-15",
                "gender": "MALE",
                "address": "123 Test Street, Pune, Maharashtra 411001",
            }
            data.update(overrides)
            return GovernmentIdExtraction(**data)

        elif doc_type == DocumentType.MARKSHEET:
            data = {
                "candidate_name": "Test Student",
                "roll_number": "TEST-ROLL-987654",
                "exam_name": "Higher Secondary Certificate (HSC)",
                "passing_year": 2024,
                "total_marks": 540.0,
                "max_marks": 600.0,
                "percentage": 90.0,
                "result_status": "PASS",
            }
            data.update(overrides)
            return MarksheetExtraction(**data)

        elif doc_type == DocumentType.INCOME_CERTIFICATE:
            data = {
                "applicant_name": "Test Student",
                "father_guardian_name": "Test Father",
                "annual_income_inr": 250000.0,
                "certificate_number": "TEST-INC-2024-55555",
                "issuing_authority": "Tahsildar Office, Pune",
                "issue_date": "2024-04-10",
                "financial_year": "2023-2024",
            }
            data.update(overrides)
            return IncomeCertificateExtraction(**data)

        elif doc_type == DocumentType.DOMICILE_CERTIFICATE:
            data = {
                "candidate_name": "Test Student",
                "state": "Maharashtra",
                "is_maharashtra_domicile": True,
                "certificate_number": "TEST-DOM-2024-88888",
                "issue_date": "2024-03-20",
            }
            data.update(overrides)
            return DomicileCertificateExtraction(**data)

        raise ValueError(f"Unhandled document type '{doc_type}' in mock generator.")

    def _generate_incomplete_fields(
        self,
        doc_type: DocumentType,
        overrides: Optional[Dict[str, Any]] = None
    ):
        data: Dict[str, Any] = {}
        overrides = overrides or {}

        if doc_type == DocumentType.GOVERNMENT_ID:
            data = {
                "id_type": "AADHAAR",
                "id_number": "TEST-1234-5678-9012",
                "full_name": "Test Student",
                "date_of_birth": None,  # Missing DOB
                "gender": None,
                "address": None,
            }
            data.update(overrides)
            return GovernmentIdExtraction(**data)

        elif doc_type == DocumentType.MARKSHEET:
            data = {
                "candidate_name": "Test Student",
                "roll_number": "TEST-ROLL-987654",
                "exam_name": "HSC",
                "passing_year": 2024,
                "total_marks": None,  # Incomplete marks breakdown
                "max_marks": None,
                "percentage": 85.0,
                "result_status": "PASS",
            }
            data.update(overrides)
            return MarksheetExtraction(**data)

        elif doc_type == DocumentType.INCOME_CERTIFICATE:
            data = {
                "applicant_name": "Test Student",
                "father_guardian_name": None,  # Missing guardian name
                "annual_income_inr": 300000.0,
                "certificate_number": "TEST-INC-2024-55555",
                "issuing_authority": None,
                "issue_date": "2024-04-10",
                "financial_year": None,
            }
            data.update(overrides)
            return IncomeCertificateExtraction(**data)

        elif doc_type == DocumentType.DOMICILE_CERTIFICATE:
            data = {
                "candidate_name": "Test Student",
                "state": "Maharashtra",
                "is_maharashtra_domicile": True,
                "certificate_number": None,  # Missing cert number
                "issue_date": None,
            }
            data.update(overrides)
            return DomicileCertificateExtraction(**data)

        raise ValueError(f"Unhandled document type '{doc_type}' in mock generator.")
