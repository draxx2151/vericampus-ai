from app.services.verification.ocr.base_ocr import (
    BaseOCRProvider,
    OCRResult,
    OCRLine,
    OCRBoundingBox,
)
from app.services.verification.ocr.paddleocr_provider import PaddleOCRProvider

__all__ = [
    "BaseOCRProvider",
    "OCRResult",
    "OCRLine",
    "OCRBoundingBox",
    "PaddleOCRProvider",
]
