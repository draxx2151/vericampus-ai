from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field


class OCRBoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class OCRLine(BaseModel):
    text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bounding_box: Optional[OCRBoundingBox] = None
    page_number: int = 1


class OCRResult(BaseModel):
    success: bool
    full_text: str
    lines: List[OCRLine] = Field(default_factory=list)
    average_confidence: float = Field(0.0, ge=0.0, le=1.0)
    page_count: int = 1
    engine_name: str
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseOCRProvider(ABC):
    """
    Abstract contract for OCR providers (PaddleOCR, Tesseract, Local Mock, etc.).
    Extracts text lines and bounding boxes from image bytes or files.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the underlying OCR engine is installed and operational."""
        pass

    @abstractmethod
    def extract_text(self, image_input: Union[bytes, Path, str], **kwargs: Any) -> OCRResult:
        """
        Runs OCR on a preprocessed image and returns an OCRResult.

        Args:
            image_input: Image bytes (PNG/JPEG) or a Path to an image file.
            **kwargs: Engine-specific execution parameters.
        """
        pass
