import io
import unittest
from PIL import Image

from app.db.models.enums import DocumentType
from app.services.verification.base import (
    ReadabilityScore,
    GovernmentIdExtraction,
    MarksheetExtraction,
    IncomeCertificateExtraction,
    DomicileCertificateExtraction,
    DocumentExtractionResult,
)
from app.services.verification.ocr.base_ocr import OCRResult, OCRLine, OCRBoundingBox
from app.services.verification.ocr.paddleocr_provider import PaddleOCRProvider
from app.services.verification.extractors import (
    GovernmentIdExtractor,
    MarksheetExtractor,
    IncomeCertificateExtractor,
    DomicileCertificateExtractor,
)
from app.services.verification.paddle_verifier import PaddleOCRVerifier


def _make_ocr_result(lines_text: list[str], conf: float = 0.95) -> OCRResult:
    ocr_lines = [
        OCRLine(
            text=t,
            confidence=conf,
            page_number=1,
            bounding_box=OCRBoundingBox(x_min=0, y_min=i * 20, x_max=200, y_max=(i + 1) * 20),
        )
        for i, t in enumerate(lines_text)
    ]
    return OCRResult(
        success=True,
        full_text="\n".join(lines_text),
        lines=ocr_lines,
        average_confidence=conf,
        page_count=1,
        engine_name="MockPaddleOCR",
    )


class TestDocumentExtractors(unittest.TestCase):
    """Unit tests for document-specific structured OCR extractors."""

    def test_aadhaar_extractor(self):
        lines = [
            "GOVERNMENT OF INDIA",
            "Unique Identification Authority of India",
            "Aarav Anil Patil",
            "DOB: 15/08/2003",
            "Male",
            "1234 5678 9012",
        ]
        ocr = _make_ocr_result(lines)
        extraction, warnings = GovernmentIdExtractor.extract(ocr)

        self.assertIsInstance(extraction, GovernmentIdExtraction)
        self.assertEqual(extraction.id_type, "AADHAAR")
        self.assertEqual(extraction.id_number, "1234 5678 9012")
        self.assertEqual(extraction.full_name, "Aarav Anil Patil")
        self.assertEqual(extraction.date_of_birth, "2003-08-15")
        self.assertEqual(extraction.gender, "MALE")

    def test_pan_extractor(self):
        lines = [
            "INCOME TAX DEPARTMENT",
            "GOVT OF INDIA",
            "Permanent Account Number Card",
            "ABCDE1234F",
            "Name: Aarav Anil Patil",
            "Father's Name: Anil Patil",
            "Date of Birth: 15/08/2003",
        ]
        ocr = _make_ocr_result(lines)
        extraction, warnings = GovernmentIdExtractor.extract(ocr)

        self.assertIsInstance(extraction, GovernmentIdExtraction)
        self.assertEqual(extraction.id_type, "PAN")
        self.assertEqual(extraction.id_number, "ABCDE1234F")
        self.assertEqual(extraction.full_name, "Aarav Anil Patil")
        self.assertEqual(extraction.date_of_birth, "2003-08-15")

    def test_marksheet_extractor(self):
        lines = [
            "Maharashtra State Board of Secondary and Higher Secondary Education, Pune",
            "HIGHER SECONDARY CERTIFICATE EXAMINATION",
            "Candidate's Name: Aarav Anil Patil",
            "Seat / Roll No: H098765",
            "Passing Year: MARCH 2021",
            "Total Marks: 525 / 600",
            "Percentage: 87.50%",
            "Result: PASS",
        ]
        ocr = _make_ocr_result(lines)
        extraction, warnings = MarksheetExtractor.extract(ocr)

        self.assertIsInstance(extraction, MarksheetExtraction)
        self.assertEqual(extraction.candidate_name, "Aarav Anil Patil")
        self.assertEqual(extraction.roll_number, "H098765")
        self.assertEqual(extraction.percentage, 87.5)
        self.assertEqual(extraction.passing_year, 2021)
        self.assertIsNotNone(extraction.exam_name)
        self.assertIn("HIGHER SECONDARY", extraction.exam_name.upper())
        self.assertEqual(extraction.result_status, "PASS")

    def test_income_certificate_extractor(self):
        lines = [
            "GOVERNMENT OF MAHARASHTRA",
            "OFFICE OF THE TAHSILDAR, PUNE",
            "INCOME CERTIFICATE",
            "Certificate No: REV/INC/2024/09876",
            "This is to certify that Shri Aarav Anil Patil",
            "Annual Family Income: Rs. 1,80,000/- (Rupees One Lakh Eighty Thousand)",
            "Financial Year: 2023-2024",
            "Date of Issue: 25/04/2024",
        ]
        ocr = _make_ocr_result(lines)
        extraction, warnings = IncomeCertificateExtractor.extract(ocr)

        self.assertIsInstance(extraction, IncomeCertificateExtraction)
        self.assertEqual(extraction.applicant_name, "Aarav Anil Patil")
        self.assertEqual(extraction.annual_income_inr, 180000.0)
        self.assertEqual(extraction.certificate_number, "REV/INC/2024/09876")
        self.assertEqual(extraction.financial_year, "2023-2024")
        self.assertIn("Tahsildar", extraction.issuing_authority)

    def test_domicile_certificate_extractor(self):
        lines = [
            "GOVERNMENT OF MAHARASHTRA",
            "OFFICE OF THE SUB-DIVISIONAL OFFICER, PUNE",
            "AGE, NATIONALITY AND DOMICILE CERTIFICATE",
            "Certificate No: DOM/PUN/2024/12345",
            "This is to certify that Aarav Anil Patil",
            "is a permanent resident of the State of Maharashtra",
            "Date of Issue: 12/03/2024",
        ]
        ocr = _make_ocr_result(lines)
        extraction, warnings = DomicileCertificateExtractor.extract(ocr)

        self.assertIsInstance(extraction, DomicileCertificateExtraction)
        self.assertEqual(extraction.candidate_name, "Aarav Anil Patil")
        self.assertEqual(extraction.certificate_number, "DOM/PUN/2024/12345")
        self.assertTrue(extraction.is_maharashtra_domicile)
        self.assertEqual(extraction.state, "Maharashtra")

    def test_empty_extractor_handles_gracefully(self):
        ocr = _make_ocr_result([])
        extraction, warnings = GovernmentIdExtractor.extract(ocr)
        self.assertIsInstance(extraction, GovernmentIdExtraction)
        self.assertIsNone(extraction.id_number)
        self.assertGreater(len(warnings), 0)


class TestPaddleOCRVerifierEndToEnd(unittest.TestCase):
    """End-to-end unit tests for PaddleOCRVerifier."""

    def setUp(self):
        # Create a sample synthetic PNG image
        img = Image.new("RGB", (400, 200), color=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        self.sample_png = buf.getvalue()

    def test_paddle_ocr_verifier_with_mock_runner(self):
        raw_paddle_output = [
            [
                [[[0, 0], [100, 0], [100, 20], [0, 20]], ("GOVERNMENT OF INDIA", 0.99)],
                [[[0, 30], [200, 30], [200, 50], [0, 50]], ("1234 5678 9012", 0.97)],
                [[[0, 60], [150, 60], [150, 80], [0, 80]], ("Name: Aarav Anil Patil", 0.95)],
                [[[0, 90], [120, 90], [120, 110], [0, 110]], ("DOB: 15/08/2003", 0.92)],
                [[[0, 120], [80, 120], [80, 140], [0, 140]], ("Male", 0.96)],
            ]
        ]

        custom_provider = PaddleOCRProvider(custom_runner=lambda img: raw_paddle_output)
        verifier = PaddleOCRVerifier(ocr_provider=custom_provider)

        res: DocumentExtractionResult = verifier.extract_document(
            file_path=self.sample_png,
            document_type=DocumentType.GOVERNMENT_ID,
        )

        self.assertTrue(res.extraction_success)
        self.assertEqual(res.document_type, DocumentType.GOVERNMENT_ID)
        self.assertEqual(res.readability, ReadabilityScore.HIGH)
        self.assertIsInstance(res.extracted_fields, GovernmentIdExtraction)
        self.assertEqual(res.extracted_fields.id_number, "1234 5678 9012")
        self.assertEqual(res.extracted_fields.full_name, "Aarav Anil Patil")
        self.assertEqual(res.metadata["verifier"], "PaddleOCRVerifier")

    def test_paddle_ocr_verifier_unreadable_on_empty(self):
        # Empty provider output
        custom_provider = PaddleOCRProvider(custom_runner=lambda img: [])
        verifier = PaddleOCRVerifier(ocr_provider=custom_provider)

        res = verifier.extract_document(
            file_path=self.sample_png,
            document_type=DocumentType.MARKSHEET,
        )

        self.assertFalse(res.extraction_success)
        self.assertEqual(res.readability, ReadabilityScore.UNREADABLE)


if __name__ == "__main__":
    unittest.main()
