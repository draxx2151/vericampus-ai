"""
VeriCampus AI — Stage 3: OCR + Field Extraction Automated Test Suite
Comprehensive test suite covering all Stage 3 requirements and constraints:
- Schemas & confidence score validation ([0.0, 1.0])
- Normalizers: names (no forced title case), dates (ISO), currency/numbers, percentage, sensitive ID masking
- Field aliases coverage across all 4 document types
- Confidence and completeness scorers (prototype operational thresholds)
- Generic Government ID Extractor (Aadhaar, PAN, Voter ID, Driving License; advisory Verhoeff checksum)
- Marksheet Extractor (roll number, board, year, total marks, percentage, subjects table, strict CGPA NOT_FOUND)
- Income Certificate Extractor (applicant, father, income float, cert no, date, authority)
- Domicile Certificate Extractor (applicant, DOB, state, district, cert no, date, authority)
- OCR degradation & empty text robustness
- Pipeline Gating: Stage 1 Quality Gate (<70 blocks, >=70 proceeds)
- Pipeline Gating: Stage 2 Document Classification (MISMATCH/UNKNOWN blocks, WARNING proceeds)
- Constraint 4 explicit regression test: Re-verification safe merge preserving review_history,
  correction_request, risk_analysis, authority_verification, Stage 1, and Stage 2 metadata
- Document replacement re-verification regression test
- Multi-college tenant isolation & sensitive data masking security
"""
import unittest
import uuid
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.models.college import College
from app.db.models.student import Student
from app.db.models.admin_officer import AdminOfficer
from app.db.models.scholarship_application import ScholarshipApplication
from app.db.models.document import Document
from app.db.models.verification_result import VerificationResult
from app.db.models.enums import UserRole, ApplicationStatus, DocumentType, UploadStatus, VerificationStatus
from app.core.security import create_access_token, get_password_hash
from app.services.verification import VerificationService, MockAIVerifier, MockScenario
from app.services.verification.base import DocumentExtractionResult

from ml.field_extraction import (
    FIELD_EXTRACTOR_VERSION,
    PROTOTYPE_COMPLETENESS_COMPLETE_THRESHOLD,
    PROTOTYPE_COMPLETENESS_PARTIAL_THRESHOLD,
    FIELD_CONFIDENCE_HIGH,
    FIELD_CONFIDENCE_MEDIUM,
    FIELD_CONFIDENCE_LOW,
    STAGE1_MINIMUM_QUALITY_THRESHOLD,
    ExtractionStatus,
    DocumentExtractionStatus,
    FieldExtractionResult,
    SubjectScore,
    DocumentFieldExtractionResult,
    FieldExtractionService,
    GovernmentIdFieldExtractor,
    MarksheetFieldExtractor,
    IncomeCertificateFieldExtractor,
    DomicileCertificateFieldExtractor,
    normalize_name,
    normalize_date,
    normalize_currency,
    normalize_percentage,
    normalize_id_number,
    mask_sensitive_id,
    calculate_field_confidence,
    calculate_overall_confidence,
    calculate_completeness,
    FIELD_ALIASES,
)


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class DummyOcrLine:
    def __init__(self, text: str, confidence: float = 0.95, bbox=None):
        self.text = text
        self.confidence = confidence
        self.bbox = bbox or [10.0, 10.0, 200.0, 30.0]


class DummyOcrResult:
    def __init__(self, lines: List[str] = None, confidences: List[float] = None, page_count: int = 1):
        self.page_count = page_count
        self.lines = []
        if lines:
            for i, line_text in enumerate(lines):
                conf = confidences[i] if confidences and i < len(confidences) else 0.95
                y = 20.0 + i * 25.0
                self.lines.append(DummyOcrLine(line_text, confidence=conf, bbox=[10.0, y, 300.0, y + 20.0]))
        self.full_text = "\n".join(lines) if lines else ""


class TestFieldExtractionSchemas(unittest.TestCase):
    """Test 1-5: Stage 3 Schemas and Confidence Bounds."""

    def test_extraction_status_enums(self):
        self.assertEqual(ExtractionStatus.EXTRACTED.value, "EXTRACTED")
        self.assertEqual(ExtractionStatus.NOT_FOUND.value, "NOT_FOUND")
        self.assertEqual(ExtractionStatus.LOW_CONFIDENCE.value, "LOW_CONFIDENCE")
        self.assertEqual(ExtractionStatus.INVALID.value, "INVALID")
        self.assertEqual(ExtractionStatus.NOT_APPLICABLE.value, "NOT_APPLICABLE")

    def test_document_extraction_status_enums(self):
        self.assertEqual(DocumentExtractionStatus.COMPLETE.value, "COMPLETE")
        self.assertEqual(DocumentExtractionStatus.PARTIAL.value, "PARTIAL")
        self.assertEqual(DocumentExtractionStatus.FAILED.value, "FAILED")
        self.assertEqual(DocumentExtractionStatus.NOT_APPLICABLE.value, "NOT_APPLICABLE")
        self.assertEqual(DocumentExtractionStatus.BLOCKED.value, "BLOCKED")

    def test_field_extraction_result_bounds(self):
        field_res = FieldExtractionResult(
            field_name="student_name",
            raw_value="Aarav Sharma",
            normalized_value="aarav sharma",
            display_value="Aarav Sharma",
            confidence=0.92,
            extraction_status=ExtractionStatus.EXTRACTED,
        )
        self.assertEqual(field_res.field_name, "student_name")
        self.assertTrue(0.0 <= field_res.confidence <= 1.0)

        with self.assertRaises(ValueError):
            FieldExtractionResult(field_name="test", confidence=1.5)
        with self.assertRaises(ValueError):
            FieldExtractionResult(field_name="test", confidence=-0.1)

    def test_subject_score_schema(self):
        subj = SubjectScore(
            subject_name="Mathematics",
            marks_obtained=95.0,
            maximum_marks=100.0,
            grade="A1",
            confidence=0.98,
        )
        self.assertEqual(subj.subject_name, "Mathematics")
        self.assertEqual(subj.marks_obtained, 95.0)
        self.assertEqual(subj.grade, "A1")
        self.assertTrue(0.0 <= subj.confidence <= 1.0)

    def test_document_field_extraction_result_serialization(self):
        doc_res = DocumentFieldExtractionResult(
            document_type="GOVERNMENT_ID",
            extraction_status=DocumentExtractionStatus.COMPLETE,
            overall_confidence=0.94,
            completeness_score=1.0,
            fields={
                "id_number": FieldExtractionResult(
                    field_name="id_number",
                    raw_value="9876 5432 1098",
                    normalized_value="987654321098",
                    display_value="********1098",
                    confidence=0.96,
                    extraction_status=ExtractionStatus.EXTRACTED,
                )
            },
        )
        dumped = doc_res.model_dump()
        self.assertEqual(dumped["document_type"], "GOVERNMENT_ID")
        self.assertEqual(dumped["fields"]["id_number"]["display_value"], "********1098")
        self.assertEqual(dumped["extraction_status"], "COMPLETE")


class TestNormalizers(unittest.TestCase):
    """Test 6-14: Stage 3 Data Normalizers and Masking."""

    def test_normalize_name_preserves_raw_and_no_forced_titlecase(self):
        # Constraint 2: Name normalization must not force title case
        raw_upper = "AARAV SURESH SHARMA"
        raw_mixed = "aaRAv shARMa"
        r1, norm_upper = normalize_name(raw_upper)
        r2, norm_mixed = normalize_name(raw_mixed)

        # Raw preserved exactly
        self.assertEqual(r1, "AARAV SURESH SHARMA")
        self.assertEqual(r2, "aaRAv shARMa")
        # Must return lowercase with trimmed whitespace
        self.assertEqual(norm_upper, "aarav suresh sharma")
        self.assertEqual(norm_mixed, "aarav sharma")
        # Ensure it does NOT force Title Case
        self.assertNotEqual(norm_upper, "Aarav Suresh Sharma")

    def test_normalize_name_handles_honorifics_and_titles(self):
        _, norm1 = normalize_name("Mr. Aarav Sharma")
        _, norm2 = normalize_name("Shri Suresh Sharma")
        _, norm3 = normalize_name("Smt. Sunita Sharma")
        _, norm4 = normalize_name("Kum. Ananya Patil")
        self.assertEqual(norm1, "aarav sharma")
        self.assertEqual(norm2, "suresh sharma")
        self.assertEqual(norm3, "sunita sharma")
        self.assertEqual(norm4, "ananya patil")

    def test_normalize_date_iso_formats(self):
        _, d1 = normalize_date("15/08/2004")
        _, d2 = normalize_date("15-08-2004")
        _, d3 = normalize_date("2004-08-15")
        _, d4 = normalize_date("15.08.2004")
        _, d5 = normalize_date("15 Aug 2004")
        _, d6 = normalize_date("August 15, 2004")
        self.assertEqual(d1, "2004-08-15")
        self.assertEqual(d2, "2004-08-15")
        self.assertEqual(d3, "2004-08-15")
        self.assertEqual(d4, "2004-08-15")
        self.assertEqual(d5, "2004-08-15")
        self.assertEqual(d6, "2004-08-15")

    def test_normalize_date_invalid_strings(self):
        _, d1 = normalize_date("not-a-date")
        _, d2 = normalize_date("")
        _, d3 = normalize_date("32/13/2099")
        self.assertIsNone(d1)
        self.assertIsNone(d2)
        self.assertIsNone(d3)

    def test_normalize_currency_inr(self):
        _, c1 = normalize_currency("Rs. 1,50,000/-")
        _, c2 = normalize_currency("₹ 2,40,000")
        _, c3 = normalize_currency("INR 80,000.00")
        _, c4 = normalize_currency("180000")
        _, c5 = normalize_currency("One Lakh Fifty Thousand")
        self.assertEqual(c1, 150000.0)
        self.assertEqual(c2, 240000.0)
        self.assertEqual(c3, 80000.0)
        self.assertEqual(c4, 180000.0)
        self.assertIsNone(c5)

    def test_normalize_percentage(self):
        _, p1 = normalize_percentage("85.5%")
        _, p2 = normalize_percentage("85.50 %")
        _, p3 = normalize_percentage("92.4")
        _, p4 = normalize_percentage("100%")
        _, p5 = normalize_percentage("abc%")
        self.assertEqual(p1, 85.5)
        self.assertEqual(p2, 85.5)
        self.assertEqual(p3, 92.4)
        self.assertEqual(p4, 100.0)
        self.assertIsNone(p5)

    def test_mask_sensitive_id_aadhaar(self):
        masked = mask_sensitive_id("987654321098")
        self.assertEqual(masked, "********1098")
        masked_spaced = mask_sensitive_id("9876 5432 1098")
        self.assertEqual(masked_spaced, "********1098")

    def test_mask_sensitive_id_pan(self):
        masked_pan = mask_sensitive_id("ABCDE1234F")
        self.assertEqual(masked_pan, "******234F")

    def test_mask_sensitive_id_generic_and_edge_cases(self):
        self.assertEqual(mask_sensitive_id("123"), "123")
        self.assertEqual(mask_sensitive_id(None), "")
        self.assertEqual(mask_sensitive_id(""), "")


class TestFieldAliasesAndScorer(unittest.TestCase):
    """Test 15-18: Aliases and Scorer Thresholds."""

    def test_all_doc_types_have_aliases(self):
        expected_types = ["GOVERNMENT_ID", "MARKSHEET", "INCOME_CERTIFICATE", "DOMICILE_CERTIFICATE"]
        for dt in expected_types:
            self.assertIn(dt, FIELD_ALIASES)
            self.assertIsInstance(FIELD_ALIASES[dt], dict)

    def test_field_confidence_calculation(self):
        conf_high = calculate_field_confidence(ocr_confidence=0.98, pattern_match_quality=1.0)
        conf_low = calculate_field_confidence(ocr_confidence=0.60, pattern_match_quality=0.5)
        self.assertTrue(conf_high > conf_low)
        self.assertTrue(0.0 <= conf_high <= 1.0)
        self.assertTrue(0.0 <= conf_low <= 1.0)

    def test_overall_confidence_aggregation(self):
        fields = {
            "f1": FieldExtractionResult(field_name="f1", confidence=0.90, extraction_status=ExtractionStatus.EXTRACTED),
            "f2": FieldExtractionResult(field_name="f2", confidence=0.80, extraction_status=ExtractionStatus.EXTRACTED),
            "f3": FieldExtractionResult(field_name="f3", confidence=0.0, extraction_status=ExtractionStatus.NOT_FOUND),
        }
        overall = calculate_overall_confidence(fields)
        self.assertAlmostEqual(overall, 0.85, places=2)

    def test_completeness_calculation_and_prototype_thresholds(self):
        # GOVERNMENT_ID required fields: ["full_name", "date_of_birth", "id_number"]
        # 3 out of 3 extracted -> 100% (>= PROTOTYPE_COMPLETENESS_COMPLETE_THRESHOLD 0.80) -> COMPLETE
        fields_complete = {
            "full_name": FieldExtractionResult(field_name="full_name", normalized_value="aarav", extraction_status=ExtractionStatus.EXTRACTED),
            "date_of_birth": FieldExtractionResult(field_name="date_of_birth", normalized_value="2004-08-15", extraction_status=ExtractionStatus.EXTRACTED),
            "id_number": FieldExtractionResult(field_name="id_number", normalized_value="123456789012", extraction_status=ExtractionStatus.EXTRACTED),
        }
        comp_score, status = calculate_completeness("GOVERNMENT_ID", fields_complete)
        self.assertEqual(comp_score, 1.0)
        self.assertEqual(status, DocumentExtractionStatus.COMPLETE)

        # 2 out of 3 extracted -> 66.7% (>= 0.40 but < 0.80) -> PARTIAL
        fields_partial = {
            "full_name": FieldExtractionResult(field_name="full_name", normalized_value="aarav", extraction_status=ExtractionStatus.EXTRACTED),
            "date_of_birth": FieldExtractionResult(field_name="date_of_birth", normalized_value="2004-08-15", extraction_status=ExtractionStatus.EXTRACTED),
            "id_number": FieldExtractionResult(field_name="id_number", normalized_value=None, extraction_status=ExtractionStatus.NOT_FOUND),
        }
        comp_score_part, status_part = calculate_completeness("GOVERNMENT_ID", fields_partial)
        self.assertAlmostEqual(comp_score_part, 0.667, places=2)
        self.assertEqual(status_part, DocumentExtractionStatus.PARTIAL)

        # 1 out of 3 extracted -> 33.3% (< 0.40) -> FAILED
        fields_failed = {
            "full_name": FieldExtractionResult(field_name="full_name", normalized_value="aarav", extraction_status=ExtractionStatus.EXTRACTED),
            "date_of_birth": FieldExtractionResult(field_name="date_of_birth", normalized_value=None, extraction_status=ExtractionStatus.NOT_FOUND),
            "id_number": FieldExtractionResult(field_name="id_number", normalized_value=None, extraction_status=ExtractionStatus.NOT_FOUND),
        }
        comp_score_fail, status_fail = calculate_completeness("GOVERNMENT_ID", fields_failed)
        self.assertAlmostEqual(comp_score_fail, 0.333, places=2)
        self.assertEqual(status_fail, DocumentExtractionStatus.FAILED)


class TestGenericGovernmentIdExtractor(unittest.TestCase):
    """Test 19-24: Generic Government ID Extractor (Aadhaar, PAN, Voter ID, DL)."""

    def setUp(self):
        self.extractor = GovernmentIdFieldExtractor()

    def test_aadhaar_extraction_and_masking(self):
        ocr = DummyOcrResult([
            "GOVERNMENT OF INDIA",
            "Unique Identification Authority of India",
            "Name: Aarav Suresh Sharma",
            "DOB: 15/08/2004",
            "Gender: Male",
            "9876 5432 1098",
        ])
        result = self.extractor.extract(ocr)
        self.assertIn("id_number", result.fields)
        self.assertEqual(result.fields["id_number"].extraction_status, ExtractionStatus.EXTRACTED)
        self.assertEqual(result.fields["id_number"].display_value, "********1098")
        self.assertEqual(result.fields["full_name"].normalized_value, "aarav suresh sharma")
        self.assertEqual(result.fields["date_of_birth"].normalized_value, "2004-08-15")

    def test_advisory_verhoeff_checksum_never_fails_extraction(self):
        # Constraint 1: Checksum failure must remain advisory and never fail extraction
        # 1111 2222 3334 fails Verhoeff checksum
        ocr = DummyOcrResult([
            "Government of India",
            "Unique Identification Authority",
            "Name: Rohan Verma",
            "1111 2222 3334",
        ])
        result = self.extractor.extract(ocr)
        id_field = result.fields.get("id_number")
        self.assertIsNotNone(id_field)
        # MUST remain EXTRACTED despite invalid checksum
        self.assertEqual(id_field.extraction_status, ExtractionStatus.EXTRACTED)
        self.assertEqual(id_field.normalized_value, "111122223334")
        # Checksum advisory notice placed in warnings or reasons
        has_advisory = any("checksum" in w.lower() for w in result.warnings) or (id_field.reason and "checksum" in id_field.reason.lower())
        self.assertTrue(has_advisory)

    def test_pan_card_extraction(self):
        ocr = DummyOcrResult([
            "INCOME TAX DEPARTMENT",
            "GOVT. OF INDIA",
            "Permanent Account Number Card",
            "ABCDE1234F",
            "Name: Aarav Sharma",
            "Father's Name: Suresh Sharma",
            "Date of Birth: 15/08/2004",
        ])
        result = self.extractor.extract(ocr)
        self.assertEqual(result.fields["id_number"].normalized_value, "ABCDE1234F")
        self.assertEqual(result.fields["id_number"].display_value, "******234F")
        self.assertEqual(result.fields["id_type"].normalized_value, "PAN")

    def test_voter_id_extraction(self):
        ocr = DummyOcrResult([
            "ELECTION COMMISSION OF INDIA",
            "ELECTOR PHOTO IDENTITY CARD",
            "EPIC NO: WBF1234567",
            "Name: Aarav Sharma",
        ])
        result = self.extractor.extract(ocr)
        self.assertEqual(result.fields["id_number"].normalized_value, "WBF1234567")
        self.assertEqual(result.fields["id_type"].normalized_value, "VOTER_ID")

    def test_driving_license_extraction(self):
        ocr = DummyOcrResult([
            "UNION OF INDIA DRIVING LICENCE",
            "MAHARASHTRA STATE",
            "DL NO: MH1220190012345",
            "Name: Aarav Sharma",
        ])
        result = self.extractor.extract(ocr)
        self.assertEqual(result.fields["id_number"].normalized_value, "MH1220190012345")
        self.assertEqual(result.fields["id_type"].normalized_value, "DRIVING_LICENSE")


class TestMarksheetExtractor(unittest.TestCase):
    """Test 25-28: Marksheet Extractor, Subjects, and Strict CGPA Handling."""

    def setUp(self):
        self.extractor = MarksheetFieldExtractor()

    def test_marksheet_academic_fields(self):
        ocr = DummyOcrResult([
            "CENTRAL BOARD OF SECONDARY EDUCATION",
            "SENIOR SCHOOL CERTIFICATE EXAMINATION 2022",
            "Roll No: 12345678",
            "Candidate Name: Aarav Sharma",
            "Total Marks: 450",
            "Maximum Marks: 500",
            "Percentage: 90.0%",
        ])
        result = self.extractor.extract(ocr)
        self.assertEqual(result.fields["roll_number"].normalized_value, "12345678")
        self.assertEqual(result.fields["examination_year"].normalized_value, 2022)
        self.assertEqual(result.fields["total_marks"].normalized_value, 450.0)
        self.assertEqual(result.fields["percentage"].normalized_value, 90.0)

    def test_marksheet_subjects_table_parsing(self):
        ocr = DummyOcrResult([
            "Roll No: 87654321",
            "Subject Name Marks Max Grade",
            "English Core 085 100 A2",
            "Mathematics 095 100 A1",
            "Physics 090 100 A1",
            "Chemistry 088 100 A2",
            "Computer Science 092 100 A1",
            "Total: 450 / 500",
        ])
        result = self.extractor.extract(ocr)
        subjects_field = result.fields.get("subjects")
        self.assertIsNotNone(subjects_field)
        self.assertEqual(subjects_field.extraction_status, ExtractionStatus.EXTRACTED)
        self.assertIsInstance(subjects_field.normalized_value, list)
        self.assertGreaterEqual(len(subjects_field.normalized_value), 3)

    def test_cgpa_strict_not_found_when_absent(self):
        # Strict requirement: Never invent or hallucinate CGPA if absent
        ocr = DummyOcrResult([
            "MAHARASHTRA STATE BOARD",
            "HIGHER SECONDARY CERTIFICATE",
            "Roll No: M123456",
            "Percentage: 84.5%",
        ])
        result = self.extractor.extract(ocr)
        cgpa_field = result.fields.get("cgpa")
        self.assertIsNotNone(cgpa_field)
        self.assertEqual(cgpa_field.extraction_status, ExtractionStatus.NOT_FOUND)
        self.assertIsNone(cgpa_field.normalized_value)

    def test_cgpa_extracted_when_present(self):
        ocr = DummyOcrResult([
            "CENTRAL BOARD OF SECONDARY EDUCATION",
            "Roll No: 99887766",
            "CGPA: 8.8",
            "Overall Grade: A1",
        ])
        result = self.extractor.extract(ocr)
        cgpa_field = result.fields.get("cgpa")
        self.assertIsNotNone(cgpa_field)
        self.assertEqual(cgpa_field.extraction_status, ExtractionStatus.EXTRACTED)
        self.assertEqual(cgpa_field.normalized_value, 8.8)


class TestIncomeAndDomicileExtractors(unittest.TestCase):
    """Test 29-32: Income and Domicile Certificate Extractors."""

    def test_income_certificate_all_fields(self):
        extractor = IncomeCertificateFieldExtractor()
        ocr = DummyOcrResult([
            "GOVERNMENT OF MAHARASHTRA",
            "OFFICE OF THE TAHSILDAR, HAVELI, PUNE",
            "INCOME CERTIFICATE",
            "Certificate No: INC/2023/12345",
            "Date of Issue: 20/06/2023",
            "This is to certify that Shri Aarav Sharma",
            "Son of Suresh Sharma",
            "Annual Family Income is Rs. 1,50,000/- (One Lakh Fifty Thousand Only)",
            "Financial Year: 2022-2023",
            "Issuing Authority: Tahsildar Pune",
        ])
        result = extractor.extract(ocr)
        self.assertEqual(result.fields["applicant_name"].normalized_value, "aarav sharma")
        self.assertEqual(result.fields["father_guardian_name"].normalized_value, "suresh sharma")
        self.assertEqual(result.fields["income_amount"].normalized_value, 150000.0)
        self.assertEqual(result.fields["certificate_number"].normalized_value, "INC/2023/12345")
        self.assertEqual(result.fields["issue_date"].normalized_value, "2023-06-20")

    def test_domicile_certificate_all_fields(self):
        extractor = DomicileCertificateFieldExtractor()
        ocr = DummyOcrResult([
            "GOVERNMENT OF MAHARASHTRA",
            "OFFICE OF THE SUB-DIVISIONAL MAGISTRATE",
            "DOMICILE CERTIFICATE",
            "Certificate No: DOM/2022/98765",
            "Date of Issue: 12/04/2022",
            "This is to certify that Aarav Suresh Sharma",
            "Date of Birth: 15/08/2004",
            "Resident of Pune, District Pune, State of Maharashtra",
            "Issuing Authority: Executive Magistrate",
        ])
        result = extractor.extract(ocr)
        self.assertEqual(result.fields["applicant_name"].normalized_value, "aarav suresh sharma")
        self.assertEqual(result.fields["date_of_birth"].normalized_value, "2004-08-15")
        self.assertEqual(result.fields["domicile_state"].normalized_value, "maharashtra")
        self.assertEqual(result.fields["certificate_number"].normalized_value, "DOM/2022/98765")
        self.assertEqual(result.fields["issue_date"].normalized_value, "2022-04-12")


class TestPipelineGatingAndDegradedOcr(unittest.TestCase):
    """Test 33-37: Stage 1 and Stage 2 Pipeline Gating, and Degraded OCR Robustness."""

    def test_empty_ocr_returns_not_found_without_crashing(self):
        ocr = DummyOcrResult([])
        extractor = GovernmentIdFieldExtractor()
        result = extractor.extract(ocr)
        self.assertEqual(result.extraction_status, DocumentExtractionStatus.FAILED)
        self.assertEqual(result.overall_confidence, 0.0)
        self.assertEqual(result.completeness_score, 0.0)

    def test_stage1_low_quality_blocks_extraction(self):
        # Quality < 70 must block extraction with LOW_DOCUMENT_QUALITY
        ocr = DummyOcrResult(["GOVERNMENT OF INDIA", "Aarav Sharma"])
        quality_mock = {"quality_score": 52.0, "quality_gate_status": "REUPLOAD_REQUIRED"}
        result = FieldExtractionService.extract(
            doc_type="GOVERNMENT_ID",
            ocr_result=ocr,
            quality_assessment=quality_mock,
        )
        self.assertEqual(result.extraction_status, DocumentExtractionStatus.BLOCKED)
        self.assertIn("LOW_DOCUMENT_QUALITY", result.errors)
        self.assertEqual(len(result.fields), 0)

    def test_stage1_pass_quality_proceeds_with_extraction(self):
        ocr = DummyOcrResult(["GOVERNMENT OF INDIA", "Name: Aarav Sharma", "9876 5432 1098"])
        quality_mock = {"quality_score": 88.0, "quality_gate_status": "PASS"}
        result = FieldExtractionService.extract(
            doc_type="GOVERNMENT_ID",
            ocr_result=ocr,
            quality_assessment=quality_mock,
        )
        self.assertNotEqual(result.extraction_status, DocumentExtractionStatus.BLOCKED)
        self.assertIn("id_number", result.fields)

    def test_stage2_classification_mismatch_blocks_extraction(self):
        ocr = DummyOcrResult(["ANNUAL FAMILY INCOME CERTIFICATE", "Income Rs. 150000"])
        classification_mock = {
            "classification_status": "DOCUMENT_TYPE_MISMATCH",
            "predicted_type": "INCOME_CERTIFICATE",
        }
        result = FieldExtractionService.extract(
            doc_type="MARKSHEET",  # Uploaded to Marksheet slot
            ocr_result=ocr,
            classification_result=classification_mock,
        )
        self.assertEqual(result.extraction_status, DocumentExtractionStatus.BLOCKED)
        self.assertIn("DOCUMENT_TYPE_MISMATCH", result.errors)

    def test_stage2_warning_proceeds_with_warning(self):
        ocr = DummyOcrResult(["GOVERNMENT OF INDIA", "Name: Aarav Sharma", "9876 5432 1098"])
        classification_mock = {
            "classification_status": "WARNING",
            "predicted_type": "GOVERNMENT_ID",
        }
        result = FieldExtractionService.extract(
            doc_type="GOVERNMENT_ID",
            ocr_result=ocr,
            classification_result=classification_mock,
        )
        self.assertNotEqual(result.extraction_status, DocumentExtractionStatus.BLOCKED)
        self.assertTrue(any("warning" in w.lower() for w in result.warnings))


class TestReVerificationSafeMergeRegression(unittest.TestCase):
    """
    Test 38: Constraint 4 Explicit Regression Test.
    Re-verification must merge Stage 3 data without overwriting review_history,
    correction_request, risk_analysis, authority_verification, Stage 1, or Stage 2 metadata.
    """

    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)

    def setUp(self):
        self.db = TestingSessionLocal()

        self.college = College(
            id=uuid.uuid4(),
            college_name="Pune Institute of Technology",
            college_code=f"PIT_{uuid.uuid4().hex[:6].upper()}",
            address="Pune, Maharashtra",
        )
        self.db.add(self.college)

        self.student = Student(
            id=uuid.uuid4(),
            college_id=self.college.id,
            email=f"aarav.{uuid.uuid4().hex[:6]}@example.com",
            password_hash=get_password_hash("StudentPass123!"),
            full_name="Aarav Sharma",
            is_active=True,
        )
        self.db.add(self.student)

        self.app_record = ScholarshipApplication(
            id=uuid.uuid4(),
            student_id=self.student.id,
            application_number=f"APP-{uuid.uuid4().hex[:8].upper()}",
            scholarship_name="Post Matric Scholarship to OBC Students",
            status=ApplicationStatus.SUBMITTED,
        )
        self.db.add(self.app_record)

        # Add all 4 required documents
        for dt in [DocumentType.GOVERNMENT_ID, DocumentType.MARKSHEET, DocumentType.INCOME_CERTIFICATE, DocumentType.DOMICILE_CERTIFICATE]:
            doc = Document(
                id=uuid.uuid4(),
                application_id=self.app_record.id,
                document_type=dt,
                original_filename=f"{dt.value.lower()}_test.png",
                file_size=10240,
                mime_type="image/png",
                storage_path=f"test_storage/{dt.value.lower()}.png",
                upload_status=UploadStatus.UPLOADED,
            )
            self.db.add(doc)

        # Existing initial VerificationResult with prior stages and administrative audit trail
        self.initial_review_history = [
            {
                "timestamp": "2026-09-20T10:00:00",
                "admin_id": str(uuid.uuid4()),
                "admin_name": "Verification Officer Patil",
                "action": "FLAGGED_FOR_MANUAL_INSPECTION",
                "notes": "Aadhaar address needs cross-verification with Tahsildar stamp.",
            }
        ]
        self.initial_correction_request = {
            "status": "PENDING",
            "requested_at": "2026-09-20T10:05:00",
            "admin_name": "Verification Officer Patil",
            "document_types": ["INCOME_CERTIFICATE"],
            "reason": "Income certificate stamp partially smudged.",
            "resolved_documents": [],
        }
        self.initial_risk_analysis = {
            "risk_score": 15,
            "risk_level": "LOW",
            "contributing_factors": ["Minor OCR blur"],
        }
        self.initial_authority_verification = {
            "GOVERNMENT_ID": {"status": "NOT_AVAILABLE", "provider": "UnavailableProvider"},
        }
        self.initial_stage1_quality = {
            "overall_quality_score": 92.0,
            "overall_quality_level": "HIGH",
            "quality_gate_status": "PASS",
        }
        self.initial_stage2_classification = {
            "overall_status": "PASS",
            "mismatched_documents": [],
        }

        self.existing_result = VerificationResult(
            id=uuid.uuid4(),
            application_id=self.app_record.id,
            document_id=None,
            overall_score=85.0,
            verification_status=VerificationStatus.VERIFIED,
            extracted_data={
                "review_history": self.initial_review_history,
                "correction_request": self.initial_correction_request,
                "risk_analysis": self.initial_risk_analysis,
                "authority_verification": self.initial_authority_verification,
                "document_quality": self.initial_stage1_quality,
                "document_classification": self.initial_stage2_classification,
            },
            field_checks={},
            cross_document_matches=[],
            issues=[],
        )
        self.db.add(self.existing_result)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_reverification_safely_merges_stage3_and_preserves_all_metadata(self):
        """
        Verify that running re-verification via VerificationService:
        1. Adds Stage 3 'field_extraction' to extracted_data
        2. Preserves 'review_history' exactly
        3. Preserves 'correction_request'
        4. Preserves 'risk_analysis'
        5. Preserves 'authority_verification'
        6. Preserves Stage 1 'document_quality'
        7. Preserves Stage 2 'document_classification'
        """
        mock_verifier = MockAIVerifier(default_scenario=MockScenario.SUCCESS)

        res = VerificationService.verify_application(
            db=self.db,
            app_id_str=self.app_record.id,
            user_id_str=self.student.id,
            user_college_id_str=self.college.id,
            role=UserRole.STUDENT,
            verifier=mock_verifier,
        )

        self.db.refresh(self.existing_result)
        extracted = self.existing_result.extracted_data

        # 1. Stage 3 Field Extraction is present
        self.assertIn("field_extraction", extracted)
        s3 = extracted["field_extraction"]
        self.assertIn("GOVERNMENT_ID", s3)
        self.assertIn("MARKSHEET", s3)
        self.assertIn("INCOME_CERTIFICATE", s3)
        self.assertIn("DOMICILE_CERTIFICATE", s3)

        # 2. Administrative Review History is 100% PRESERVED
        self.assertIn("review_history", extracted)
        self.assertEqual(len(extracted["review_history"]), 1)
        self.assertEqual(extracted["review_history"][0]["admin_name"], "Verification Officer Patil")
        self.assertEqual(extracted["review_history"][0]["notes"], "Aadhaar address needs cross-verification with Tahsildar stamp.")

        # 3. Correction Request is PRESERVED
        self.assertIn("correction_request", extracted)
        self.assertEqual(extracted["correction_request"]["reason"], "Income certificate stamp partially smudged.")

        # 4. Risk Analysis is PRESERVED/UPDATED
        self.assertIn("risk_analysis", extracted)

        # 5. Authority Verification is PRESERVED
        self.assertIn("authority_verification", extracted)

        # 6. Stage 1 Document Quality is PRESERVED
        self.assertIn("document_quality", extracted)

        # 7. Stage 2 Document Classification is PRESERVED
        self.assertIn("document_classification", extracted)


class TestDocumentReplacementReverification(unittest.TestCase):
    """Test 39: Document replacement re-verification scenario."""

    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        Base.metadata.create_all(bind=engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)

    def setUp(self):
        self.db = TestingSessionLocal()
        self.college = College(
            id=uuid.uuid4(),
            college_name="Mumbai Tech",
            college_code=f"MT_{uuid.uuid4().hex[:6].upper()}",
            address="Mumbai, Maharashtra",
        )
        self.db.add(self.college)

        self.student = Student(
            id=uuid.uuid4(),
            college_id=self.college.id,
            email=f"student2.{uuid.uuid4().hex[:6]}@example.com",
            password_hash=get_password_hash("Pass123!"),
            full_name="Rohan Verma",
            is_active=True,
        )
        self.db.add(self.student)

        self.app_record = ScholarshipApplication(
            id=uuid.uuid4(),
            student_id=self.student.id,
            application_number=f"APP-{uuid.uuid4().hex[:8].upper()}",
            scholarship_name="Post Matric Scholarship to OBC Students",
            status=ApplicationStatus.SUBMITTED,
        )
        self.db.add(self.app_record)

        self.doc_records = {}
        for dt in [DocumentType.GOVERNMENT_ID, DocumentType.MARKSHEET, DocumentType.INCOME_CERTIFICATE, DocumentType.DOMICILE_CERTIFICATE]:
            d = Document(
                id=uuid.uuid4(),
                application_id=self.app_record.id,
                document_type=dt,
                original_filename=f"{dt.value.lower()}_v1.png",
                file_size=10240,
                mime_type="image/png",
                storage_path=f"storage/{dt.value.lower()}_v1.png",
                upload_status=UploadStatus.UPLOADED,
            )
            self.db.add(d)
            self.doc_records[dt] = d
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_document_replacement_updates_extractions(self):
        # Initial verification run
        mock_verifier_1 = MockAIVerifier(default_scenario=MockScenario.SUCCESS)
        res1 = VerificationService.verify_application(
            db=self.db,
            app_id_str=self.app_record.id,
            user_id_str=self.student.id,
            user_college_id_str=self.college.id,
            role=UserRole.STUDENT,
            verifier=mock_verifier_1,
        )
        self.assertIn("field_extraction", res1["extracted_data"])

        # Replace Marksheet document record with updated file
        marksheet_doc = self.doc_records[DocumentType.MARKSHEET]
        marksheet_doc.original_filename = "marksheet_v2.png"
        marksheet_doc.storage_path = "storage/marksheet_v2.png"
        self.db.commit()

        # Re-verify
        mock_verifier_2 = MockAIVerifier(default_scenario=MockScenario.SUCCESS)
        res2 = VerificationService.verify_application(
            db=self.db,
            app_id_str=self.app_record.id,
            user_id_str=self.student.id,
            user_college_id_str=self.college.id,
            role=UserRole.STUDENT,
            verifier=mock_verifier_2,
        )
        self.assertEqual(str(res2["application_id"]), str(res1["application_id"]))
        db_results = self.db.query(VerificationResult).filter(VerificationResult.application_id == self.app_record.id).all()
        self.assertEqual(len(db_results), 1)  # Same database record updated in place
        self.assertIn("field_extraction", res2["extracted_data"])
        self.assertEqual(res2["extracted_data"]["field_extraction"]["MARKSHEET"]["extraction_status"], "COMPLETE")


class TestMultiTenantIsolationAndSecurity(unittest.TestCase):
    """Test 40: Multi-college tenant isolation and data security."""

    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        Base.metadata.create_all(bind=engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)

    def setUp(self):
        self.db = TestingSessionLocal()
        self.college_a = College(
            id=uuid.uuid4(),
            college_name="College A",
            college_code=f"COLA_{uuid.uuid4().hex[:6].upper()}",
            address="Pune, Maharashtra",
        )
        self.college_b = College(
            id=uuid.uuid4(),
            college_name="College B",
            college_code=f"COLB_{uuid.uuid4().hex[:6].upper()}",
            address="Nagpur, Maharashtra",
        )
        self.db.add_all([self.college_a, self.college_b])

        self.student_a = Student(
            id=uuid.uuid4(),
            college_id=self.college_a.id,
            email=f"student.a.{uuid.uuid4().hex[:6]}@example.com",
            password_hash=get_password_hash("Pass123!"),
            full_name="A Student",
            is_active=True,
        )
        self.db.add(self.student_a)

        self.app_a = ScholarshipApplication(
            id=uuid.uuid4(),
            student_id=self.student_a.id,
            application_number=f"APP-{uuid.uuid4().hex[:8].upper()}",
            scholarship_name="Post Matric Scholarship to OBC Students",
            status=ApplicationStatus.SUBMITTED,
        )
        self.db.add(self.app_a)

        for dt in [DocumentType.GOVERNMENT_ID, DocumentType.MARKSHEET, DocumentType.INCOME_CERTIFICATE, DocumentType.DOMICILE_CERTIFICATE]:
            self.db.add(Document(
                id=uuid.uuid4(),
                application_id=self.app_a.id,
                document_type=dt,
                original_filename=f"{dt.value}.png",
                file_size=10240,
                mime_type="image/png",
                storage_path=f"storage/{dt.value}.png",
                upload_status=UploadStatus.UPLOADED,
            ))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_cross_college_admin_verification_is_forbidden(self):
        from fastapi import HTTPException
        # Admin from College B tries to verify Application from College A
        with self.assertRaises(HTTPException) as ctx:
            VerificationService.verify_application(
                db=self.db,
                app_id_str=self.app_a.id,
                user_id_str=uuid.uuid4(),
                user_college_id_str=self.college_b.id,  # College B admin
                role=UserRole.ADMIN,
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Cross-college application access is prohibited", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
