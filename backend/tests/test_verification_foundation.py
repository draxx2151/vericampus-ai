import unittest
from pathlib import Path

from app.db.models.enums import DocumentType
from app.services.verification import (
    BaseAIVerifier,
    MockAIVerifier,
    MockScenario,
    ReadabilityScore,
    DocumentExtractionResult,
    GovernmentIdExtraction,
    MarksheetExtraction,
    IncomeCertificateExtraction,
    DomicileCertificateExtraction,
)


class TestVerificationFoundation(unittest.TestCase):
    """
    Unit tests for Phase 6 Module 1 — Verification Engine Foundation.
    Verifies the abstract contract, deterministic mock verifier,
    all 4 document extractions, readability tiers, and edge cases.
    """

    def setUp(self):
        self.verifier = MockAIVerifier()

    def test_base_interface_cannot_be_instantiated_directly(self):
        """Ensure BaseAIVerifier enforces the abstract interface contract"""
        with self.assertRaises(TypeError):
            BaseAIVerifier()  # Cannot instantiate abstract class without extract_document

    def test_extract_government_id_success(self):
        """Test structured extraction for GOVERNMENT_ID"""
        result = self.verifier.extract_document(
            file_path="storage/test_aadhaar.pdf",
            document_type=DocumentType.GOVERNMENT_ID
        )

        self.assertIsInstance(result, DocumentExtractionResult)
        self.assertEqual(result.document_type, DocumentType.GOVERNMENT_ID)
        self.assertTrue(result.extraction_success)
        self.assertEqual(result.readability, ReadabilityScore.HIGH)
        self.assertEqual(len(result.warnings), 0)

        # Validate typed fields
        fields = result.extracted_fields
        self.assertIsInstance(fields, GovernmentIdExtraction)
        self.assertEqual(fields.id_type, "AADHAAR")
        self.assertEqual(fields.id_number, "TEST-1234-5678-9012")
        self.assertEqual(fields.full_name, "Test Student")
        self.assertEqual(fields.date_of_birth, "2004-01-15")
        self.assertEqual(fields.gender, "MALE")
        self.assertIn("Pune", fields.address)

    def test_extract_marksheet_success(self):
        """Test structured extraction for MARKSHEET"""
        result = self.verifier.extract_document(
            file_path="storage/test_marksheet.pdf",
            document_type=DocumentType.MARKSHEET
        )

        self.assertIsInstance(result, DocumentExtractionResult)
        self.assertEqual(result.document_type, DocumentType.MARKSHEET)
        self.assertTrue(result.extraction_success)
        self.assertEqual(result.readability, ReadabilityScore.HIGH)

        # Validate typed fields
        fields = result.extracted_fields
        self.assertIsInstance(fields, MarksheetExtraction)
        self.assertEqual(fields.candidate_name, "Test Student")
        self.assertEqual(fields.roll_number, "TEST-ROLL-987654")
        self.assertEqual(fields.passing_year, 2024)
        self.assertEqual(fields.percentage, 90.0)
        self.assertEqual(fields.total_marks, 540.0)
        self.assertEqual(fields.max_marks, 600.0)
        self.assertEqual(fields.result_status, "PASS")

    def test_extract_income_certificate_success(self):
        """Test structured extraction for INCOME_CERTIFICATE"""
        result = self.verifier.extract_document(
            file_path="storage/test_income.pdf",
            document_type=DocumentType.INCOME_CERTIFICATE
        )

        self.assertIsInstance(result, DocumentExtractionResult)
        self.assertEqual(result.document_type, DocumentType.INCOME_CERTIFICATE)
        self.assertTrue(result.extraction_success)
        self.assertEqual(result.readability, ReadabilityScore.HIGH)

        # Validate typed fields
        fields = result.extracted_fields
        self.assertIsInstance(fields, IncomeCertificateExtraction)
        self.assertEqual(fields.applicant_name, "Test Student")
        self.assertEqual(fields.father_guardian_name, "Test Father")
        self.assertEqual(fields.annual_income_inr, 250000.0)
        self.assertEqual(fields.certificate_number, "TEST-INC-2024-55555")
        self.assertEqual(fields.issuing_authority, "Tahsildar Office, Pune")
        self.assertEqual(fields.financial_year, "2023-2024")

    def test_extract_domicile_certificate_success(self):
        """Test structured extraction for DOMICILE_CERTIFICATE"""
        result = self.verifier.extract_document(
            file_path="storage/test_domicile.pdf",
            document_type=DocumentType.DOMICILE_CERTIFICATE
        )

        self.assertIsInstance(result, DocumentExtractionResult)
        self.assertEqual(result.document_type, DocumentType.DOMICILE_CERTIFICATE)
        self.assertTrue(result.extraction_success)
        self.assertEqual(result.readability, ReadabilityScore.HIGH)

        # Validate typed fields
        fields = result.extracted_fields
        self.assertIsInstance(fields, DomicileCertificateExtraction)
        self.assertEqual(fields.candidate_name, "Test Student")
        self.assertEqual(fields.state, "Maharashtra")
        self.assertTrue(fields.is_maharashtra_domicile)
        self.assertEqual(fields.certificate_number, "TEST-DOM-2024-88888")

    def test_deterministic_behavior_without_randomness(self):
        """Ensure repeated extractions return identical deterministic results"""
        res1 = self.verifier.extract_document("file.pdf", DocumentType.MARKSHEET)
        res2 = self.verifier.extract_document("file.pdf", DocumentType.MARKSHEET)

        self.assertEqual(res1.model_dump(), res2.model_dump())

    def test_unreadable_document_scenario(self):
        """Test MockScenario.UNREADABLE handling"""
        result = self.verifier.extract_document(
            file_path="blurry.pdf",
            document_type=DocumentType.GOVERNMENT_ID,
            scenario=MockScenario.UNREADABLE
        )

        self.assertFalse(result.extraction_success)
        self.assertEqual(result.readability, ReadabilityScore.UNREADABLE)
        self.assertIsNone(result.extracted_fields)
        self.assertTrue(len(result.warnings) > 0)
        self.assertIn("unreadable", result.warnings[0].lower())

    def test_field_failure_scenario(self):
        """Test MockScenario.FIELD_FAILURE handling"""
        result = self.verifier.extract_document(
            file_path="corrupt.pdf",
            document_type=DocumentType.INCOME_CERTIFICATE,
            scenario=MockScenario.FIELD_FAILURE
        )

        self.assertFalse(result.extraction_success)
        self.assertEqual(result.readability, ReadabilityScore.LOW)
        self.assertIsNone(result.extracted_fields)
        self.assertTrue(len(result.warnings) > 0)

    def test_incomplete_extraction_scenario(self):
        """Test MockScenario.INCOMPLETE handling where some fields are missing"""
        result = self.verifier.extract_document(
            file_path="partial.pdf",
            document_type=DocumentType.MARKSHEET,
            scenario=MockScenario.INCOMPLETE
        )

        self.assertTrue(result.extraction_success)
        self.assertEqual(result.readability, ReadabilityScore.MEDIUM)
        self.assertIsNotNone(result.extracted_fields)
        self.assertIsNone(result.extracted_fields.total_marks)
        self.assertIsNone(result.extracted_fields.max_marks)
        self.assertEqual(result.extracted_fields.percentage, 85.0)
        self.assertTrue(len(result.warnings) > 0)

    def test_unsupported_document_type_handling(self):
        """Ensure invalid or unsupported document types raise ValueError"""
        with self.assertRaises(ValueError):
            self.verifier.extract_document("file.pdf", "UNSUPPORTED_DOCUMENT_TYPE")

    def test_field_overrides_functionality(self):
        """Test explicit field overrides for custom scenario testing"""
        custom_income = 750000.0
        result = self.verifier.extract_document(
            file_path="income.pdf",
            document_type=DocumentType.INCOME_CERTIFICATE,
            field_overrides={"annual_income_inr": custom_income, "father_guardian_name": "Specific Father"}
        )

        self.assertEqual(result.extracted_fields.annual_income_inr, custom_income)
        self.assertEqual(result.extracted_fields.father_guardian_name, "Specific Father")

    def test_pydantic_serialization_compatibility(self):
        """Ensure extraction result can be dumped to dict and JSON for database/API storage"""
        result = self.verifier.extract_document("file.pdf", DocumentType.DOMICILE_CERTIFICATE)
        dumped_dict = result.model_dump()
        dumped_json = result.model_dump_json()

        self.assertIsInstance(dumped_dict, dict)
        self.assertIsInstance(dumped_json, str)
        self.assertIn("TEST-DOM-2024-88888", dumped_json)


if __name__ == "__main__":
    unittest.main()
