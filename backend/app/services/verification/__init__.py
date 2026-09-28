from app.services.verification.base import (
    BaseAIVerifier,
    ReadabilityScore,
    GovernmentIdExtraction,
    MarksheetExtraction,
    IncomeCertificateExtraction,
    DomicileCertificateExtraction,
    DocumentExtractionResult,
    ExtractedFieldsType,
)
from app.services.verification.mock_verifier import (
    MockAIVerifier,
    MockScenario,
)
from app.services.verification.rules_engine import (
    RulesEngine,
    NameMatcher,
    CheckStatus,
    FieldCheckResult,
    CrossDocumentMatch,
    VerificationEvaluation,
    DEFAULT_SCHOLARSHIP_RULES,
)
from app.services.verification.verification_service import (
    VerificationService,
    map_evaluation_to_statuses,
    REQUIRED_VERIFICATION_DOCUMENTS,
)

from app.services.verification.document_preprocessor import (
    DocumentPreprocessor,
    PreprocessingResult,
    PreprocessedPage,
)
from app.services.verification.ocr.base_ocr import (
    BaseOCRProvider,
    OCRResult,
    OCRLine,
    OCRBoundingBox,
)
from app.services.verification.ocr.paddleocr_provider import PaddleOCRProvider
from app.services.verification.paddle_verifier import PaddleOCRVerifier

__all__ = [
    "BaseAIVerifier",
    "ReadabilityScore",
    "GovernmentIdExtraction",
    "MarksheetExtraction",
    "IncomeCertificateExtraction",
    "DomicileCertificateExtraction",
    "DocumentExtractionResult",
    "ExtractedFieldsType",
    "MockAIVerifier",
    "MockScenario",
    "RulesEngine",
    "NameMatcher",
    "CheckStatus",
    "FieldCheckResult",
    "CrossDocumentMatch",
    "VerificationEvaluation",
    "DEFAULT_SCHOLARSHIP_RULES",
    "VerificationService",
    "map_evaluation_to_statuses",
    "REQUIRED_VERIFICATION_DOCUMENTS",
    "DocumentPreprocessor",
    "PreprocessingResult",
    "PreprocessedPage",
    "BaseOCRProvider",
    "OCRResult",
    "OCRLine",
    "OCRBoundingBox",
    "PaddleOCRProvider",
    "PaddleOCRVerifier",
]


