from pathlib import Path
from typing import Optional, Union, Dict, Any, List

from app.db.models.enums import DocumentType
from app.services.verification.base import (
    BaseAIVerifier,
    DocumentExtractionResult,
    ReadabilityScore,
    ExtractedFieldsType,
)
from app.services.verification.document_preprocessor import DocumentPreprocessor, PreprocessingResult
from app.services.verification.ocr.base_ocr import BaseOCRProvider, OCRResult, OCRLine
from app.services.verification.ocr.paddleocr_provider import PaddleOCRProvider
from app.services.verification.extractors import (
    GovernmentIdExtractor,
    MarksheetExtractor,
    IncomeCertificateExtractor,
    DomicileCertificateExtractor,
)


class PaddleOCRVerifier(BaseAIVerifier):
    """
    Real document verification engine implementing BaseAIVerifier.
    Orchestrates:
      File Input -> Preprocessing (OpenCV/Pillow/PyMuPDF) -> Local OCR (PaddleOCR) -> Document Extractors
    Fully compatible with VerificationService and interchangeable with MockAIVerifier.
    """

    def __init__(
        self,
        ocr_provider: Optional[BaseOCRProvider] = None,
        preprocessor: Optional[DocumentPreprocessor] = None,
    ):
        self.preprocessor = preprocessor if preprocessor is not None else DocumentPreprocessor()
        self.ocr_provider = ocr_provider if ocr_provider is not None else PaddleOCRProvider()

    def extract_document(
        self,
        file_path: Union[str, Path, bytes],
        document_type: DocumentType,
        **kwargs: Any
    ) -> DocumentExtractionResult:
        warnings: List[str] = []

        # 1. Validate Document Type
        if not isinstance(document_type, DocumentType):
            try:
                document_type = DocumentType(document_type)
            except (ValueError, KeyError):
                raise ValueError(f"Unsupported document type '{document_type}'.")

        if isinstance(file_path, (str, Path)):
            safe_name = Path(file_path).name
        else:
            safe_name = "in_memory_document"

        metadata: Dict[str, Any] = {
            "verifier": "PaddleOCRVerifier",
            "file_name": safe_name,
            "ocr_engine": getattr(self.ocr_provider, "lang", "en"),
        }

        # 2. Document Preprocessing (PDF page rendering, image normalization, deskew)
        prep_result: PreprocessingResult = self.preprocessor.preprocess(file_path)
        warnings.extend(prep_result.warnings)

        if not prep_result.success or not prep_result.processed_pages:
            return DocumentExtractionResult(
                document_type=document_type,
                extraction_success=False,
                readability=ReadabilityScore.UNREADABLE,
                warnings=warnings or ["Document preprocessing failed or produced no usable pages."],
                extracted_fields=None,
                metadata=metadata,
            )

        metadata["is_pdf"] = prep_result.is_pdf
        metadata["pages_processed"] = len(prep_result.processed_pages)

        # 3. OCR Text Extraction across preprocessed pages
        all_lines: List[OCRLine] = []
        confidences: List[float] = []

        for page in prep_result.processed_pages:
            ocr_res: OCRResult = self.ocr_provider.extract_text(page.image_bytes)
            warnings.extend(ocr_res.warnings)

            for line in ocr_res.lines:
                line.page_number = page.page_number
                all_lines.append(line)
                confidences.append(line.confidence)

        if not all_lines:
            readability = ReadabilityScore.UNREADABLE
            return DocumentExtractionResult(
                document_type=document_type,
                extraction_success=False,
                readability=readability,
                warnings=warnings or ["No legible text could be extracted by OCR engine."],
                extracted_fields=None,
                metadata=metadata,
            )

        full_text = "\n".join(l.text for l in all_lines)
        avg_confidence = (sum(confidences) / len(confidences)) if confidences else 0.0
        metadata["ocr_confidence"] = round(avg_confidence, 4)

        merged_ocr = OCRResult(
            success=True,
            full_text=full_text,
            lines=all_lines,
            average_confidence=round(avg_confidence, 4),
            page_count=len(prep_result.processed_pages),
            engine_name="PaddleOCR",
            warnings=warnings,
        )

        # 4. Determine Readability Score based on OCR Confidence
        if avg_confidence >= 0.75:
            readability = ReadabilityScore.HIGH
        elif avg_confidence >= 0.50:
            readability = ReadabilityScore.MEDIUM
        elif avg_confidence >= 0.25:
            readability = ReadabilityScore.LOW
        else:
            readability = ReadabilityScore.UNREADABLE

        # 5. Dispatch to Document-Specific Structured Extractor (Legacy & Stage 3)
        extracted_fields: Optional[ExtractedFieldsType] = None
        extractor_warnings: List[str] = []

        if document_type == DocumentType.GOVERNMENT_ID:
            extracted_fields, extractor_warnings = GovernmentIdExtractor.extract(merged_ocr)
        elif document_type == DocumentType.MARKSHEET:
            extracted_fields, extractor_warnings = MarksheetExtractor.extract(merged_ocr)
        elif document_type == DocumentType.INCOME_CERTIFICATE:
            extracted_fields, extractor_warnings = IncomeCertificateExtractor.extract(merged_ocr)
        elif document_type == DocumentType.DOMICILE_CERTIFICATE:
            extracted_fields, extractor_warnings = DomicileCertificateExtractor.extract(merged_ocr)

        warnings.extend(extractor_warnings)

        # Stage 3 Field Extraction
        stage3_result = None
        try:
            from ml.field_extraction import FieldExtractionService
            stage3_result = FieldExtractionService.extract(document_type.value, merged_ocr)
            if stage3_result and stage3_result.warnings:
                warnings.extend(stage3_result.warnings)
        except Exception as e:
            warnings.append(f"Stage 3 field extraction warning: {str(e)}")

        # Evaluate overall extraction success
        # Succeeded if extracted_fields has at least one primary identifier
        extraction_success = self._evaluate_extraction_success(extracted_fields, document_type)

        return DocumentExtractionResult(
            document_type=document_type,
            extraction_success=extraction_success,
            readability=readability,
            warnings=warnings,
            extracted_fields=extracted_fields,
            field_extraction=stage3_result,
            metadata=metadata,
        )

    @staticmethod
    def _evaluate_extraction_success(fields: Optional[ExtractedFieldsType], doc_type: DocumentType) -> bool:
        if fields is None:
            return False
        if doc_type == DocumentType.GOVERNMENT_ID:
            return bool(fields.id_number or fields.full_name)
        elif doc_type == DocumentType.MARKSHEET:
            return bool(fields.candidate_name or fields.roll_number or fields.percentage is not None)
        elif doc_type == DocumentType.INCOME_CERTIFICATE:
            return bool(fields.applicant_name or fields.annual_income_inr is not None or fields.certificate_number)
        elif doc_type == DocumentType.DOMICILE_CERTIFICATE:
            return bool(fields.candidate_name or fields.is_maharashtra_domicile is not None or fields.certificate_number)
        return True
