"""
VeriCampus AI — Stage 3 Field Extraction Service
Orchestrates Stage 1 (Quality Gate) and Stage 2 (Classification) pipeline gating,
and dispatches to the corresponding document-specific field extractor.
"""
from typing import Optional, Dict, Any
from .schemas import (
    DocumentFieldExtractionResult,
    DocumentExtractionStatus,
    FieldExtractionResult,
    ExtractionStatus,
)
from .config import STAGE1_MINIMUM_QUALITY_THRESHOLD, FIELD_EXTRACTOR_VERSION
from .extractors import (
    GovernmentIdFieldExtractor,
    MarksheetFieldExtractor,
    IncomeCertificateFieldExtractor,
    DomicileCertificateFieldExtractor,
)


class FieldExtractionService:
    """
    Central coordinator for Stage 3 Field Extraction.
    Enforces Stage 1 and Stage 2 gating contracts before running document-specific extractors.
    """

    _extractors = {
        "GOVERNMENT_ID": GovernmentIdFieldExtractor(),
        "MARKSHEET": MarksheetFieldExtractor(),
        "INCOME_CERTIFICATE": IncomeCertificateFieldExtractor(),
        "DOMICILE_CERTIFICATE": DomicileCertificateFieldExtractor(),
    }

    @classmethod
    def extract(
        cls,
        doc_type: str,
        ocr_result: Any,
        quality_assessment: Optional[Any] = None,
        classification_result: Optional[Any] = None,
        **kwargs: Any
    ) -> DocumentFieldExtractionResult:
        warnings = []
        errors = []
        upper_doc_type = str(doc_type).upper()

        # ─── GATE 1: STAGE 1 QUALITY GATE CHECK ──────────────────────────
        # If quality score is < 70, block extraction to prevent processing degraded garbage
        if quality_assessment is not None:
            q_score = (
                getattr(quality_assessment, "quality_score", None)
                if hasattr(quality_assessment, "quality_score")
                else (quality_assessment.get("quality_score") if isinstance(quality_assessment, dict) else None)
            )
            q_status = (
                getattr(quality_assessment, "quality_gate_status", None)
                if hasattr(quality_assessment, "quality_gate_status")
                else (quality_assessment.get("quality_gate_status") if isinstance(quality_assessment, dict) else None)
            )
            q_status_str = q_status.value if hasattr(q_status, "value") else str(q_status)

            if (q_score is not None and q_score < STAGE1_MINIMUM_QUALITY_THRESHOLD) or q_status_str == "REUPLOAD_REQUIRED":
                return DocumentFieldExtractionResult(
                    document_type=upper_doc_type,
                    extractor_version=FIELD_EXTRACTOR_VERSION,
                    extraction_status=DocumentExtractionStatus.BLOCKED,
                    overall_confidence=0.0,
                    completeness_score=0.0,
                    fields={},
                    warnings=[f"Stage 3 extraction blocked: Document quality too low (score: {q_score}, threshold: {STAGE1_MINIMUM_QUALITY_THRESHOLD})."],
                    errors=["LOW_DOCUMENT_QUALITY"],
                    source_pages=getattr(ocr_result, "page_count", 1) if ocr_result else 1,
                    ocr_summary={"blocked_by": "Stage 1 Quality Gate"},
                )

        # ─── GATE 2: STAGE 2 CLASSIFICATION CHECK ────────────────────────
        if classification_result is not None:
            c_status = (
                getattr(classification_result, "classification_status", None)
                if hasattr(classification_result, "classification_status")
                else (classification_result.get("classification_status") if isinstance(classification_result, dict) else None)
            )
            c_status_str = c_status.value if hasattr(c_status, "value") else str(c_status)
            c_pred = (
                getattr(classification_result, "predicted_type", None)
                if hasattr(classification_result, "predicted_type")
                else (classification_result.get("predicted_type") if isinstance(classification_result, dict) else None)
            )

            if c_status_str == "UNKNOWN" or c_pred == "UNKNOWN":
                return DocumentFieldExtractionResult(
                    document_type=upper_doc_type,
                    extractor_version=FIELD_EXTRACTOR_VERSION,
                    extraction_status=DocumentExtractionStatus.NOT_APPLICABLE,
                    overall_confidence=0.0,
                    completeness_score=0.0,
                    fields={},
                    warnings=["Stage 3 extraction not applicable: Document classified as UNKNOWN or unidentifiable."],
                    errors=[],
                    source_pages=getattr(ocr_result, "page_count", 1) if ocr_result else 1,
                    ocr_summary={"classification_status": "UNKNOWN"},
                )

            if c_status_str == "DOCUMENT_TYPE_MISMATCH":
                return DocumentFieldExtractionResult(
                    document_type=upper_doc_type,
                    extractor_version=FIELD_EXTRACTOR_VERSION,
                    extraction_status=DocumentExtractionStatus.BLOCKED,
                    overall_confidence=0.0,
                    completeness_score=0.0,
                    fields={},
                    warnings=[f"Stage 3 extraction blocked: Document slot mismatch (expected {upper_doc_type}, identified as {c_pred})."],
                    errors=["DOCUMENT_TYPE_MISMATCH"],
                    source_pages=getattr(ocr_result, "page_count", 1) if ocr_result else 1,
                    ocr_summary={"classification_status": "DOCUMENT_TYPE_MISMATCH", "predicted_type": c_pred},
                )

            if c_status_str == "WARNING":
                warnings.append(f"Stage 2 Classification warning: Moderate confidence on {upper_doc_type}.")

        # ─── DISPATCH TO DOCUMENT-SPECIFIC EXTRACTOR ─────────────────────
        extractor = cls._extractors.get(upper_doc_type)
        if extractor is None:
            return DocumentFieldExtractionResult(
                document_type=upper_doc_type,
                extractor_version=FIELD_EXTRACTOR_VERSION,
                extraction_status=DocumentExtractionStatus.NOT_APPLICABLE,
                overall_confidence=0.0,
                completeness_score=0.0,
                fields={},
                warnings=[f"No dedicated extractor registered for document type {upper_doc_type}."],
                errors=[],
            )

        # Run extraction
        result = extractor.extract(ocr_result=ocr_result, expected_type=upper_doc_type, **kwargs)
        if warnings:
            result.warnings.extend(warnings)

        return result
