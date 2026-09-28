import io
import os
from pathlib import Path
from typing import Optional, List, Union, Dict, Any, Callable
from PIL import Image

from app.services.verification.ocr.base_ocr import (
    BaseOCRProvider,
    OCRResult,
    OCRLine,
    OCRBoundingBox,
)


class PaddleOCRProvider(BaseOCRProvider):
    """
    Local PaddleOCR provider.
    Runs text extraction, line detection, and confidence scoring locally.
    Gracefully handles environments where PaddlePaddle is not yet built for Python 3.14.
    """

    def __init__(
        self,
        lang: str = "en",
        use_angle_cls: bool = True,
        engine_runner: Optional[Callable[[Any], List[Any]]] = None,
        custom_runner: Optional[Callable[[Any], List[Any]]] = None,
        **kwargs: Any
    ):
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.extra_kwargs = kwargs
        self._custom_runner = custom_runner if custom_runner is not None else engine_runner
        self._engine = None
        self._init_attempted = False
        self._available = False
        self._init_error_message: Optional[str] = None

        if self._custom_runner is not None:
            self._available = True
            self._init_attempted = True
        else:
            self._try_initialize()

    def _try_initialize(self) -> None:
        self._init_attempted = True
        try:
            # Dynamic import to avoid crash if paddleocr/paddlepaddle is not installed
            import paddle
            from paddleocr import PaddleOCR

            self._engine = PaddleOCR(
                use_angle_cls=self.use_angle_cls,
                lang=self.lang,
                show_log=False,
                **self.extra_kwargs
            )
            self._available = True
        except ImportError as e:
            self._available = False
            self._init_error_message = (
                f"PaddleOCR is unavailable: {str(e)}. "
                "PaddlePaddle C++ binary wheels are not currently distributed for Python 3.14 on Windows."
            )
        except Exception as e:
            self._available = False
            self._init_error_message = f"Failed to initialize PaddleOCR engine: {str(e)}"

    def is_available(self) -> bool:
        return self._available

    def extract_text(self, image_input: Union[bytes, Path, str], **kwargs: Any) -> OCRResult:
        # 1. Check if engine is available or a custom test runner is provided
        if not self._available and self._custom_runner is None:
            return OCRResult(
                success=False,
                full_text="",
                lines=[],
                average_confidence=0.0,
                engine_name="PaddleOCR (Unavailable)",
                warnings=[self._init_error_message or "PaddleOCR engine is not installed or available."]
            )

        if not image_input:
            return OCRResult(
                success=False,
                full_text="",
                lines=[],
                average_confidence=0.0,
                engine_name="PaddleOCR",
                warnings=["Empty image input provided."]
            )

        # 2. Normalize image input
        try:
            if isinstance(image_input, (str, Path)):
                img_path = Path(image_input)
                if not img_path.exists():
                    return OCRResult(
                        success=False,
                        full_text="",
                        lines=[],
                        average_confidence=0.0,
                        engine_name="PaddleOCR",
                        warnings=[f"Image file not found: {img_path}"]
                    )
                # Pass file path directly or read into PIL
                image_arg = str(img_path)
            elif isinstance(image_input, bytes):
                # Convert bytes into PIL Image for PaddleOCR
                pil_img = Image.open(io.BytesIO(image_input)).convert("RGB")
                import numpy as np
                image_arg = np.array(pil_img)
            else:
                return OCRResult(
                    success=False,
                    full_text="",
                    lines=[],
                    average_confidence=0.0,
                    engine_name="PaddleOCR",
                    warnings=["Invalid image input format."]
                )
        except Exception as e:
            return OCRResult(
                success=False,
                full_text="",
                lines=[],
                average_confidence=0.0,
                engine_name="PaddleOCR",
                warnings=[f"Error preparing image for OCR: {str(e)}"]
            )

        # 3. Execute OCR engine or runner
        try:
            if self._custom_runner is not None:
                raw_results = self._custom_runner(image_arg)
            else:
                raw_results = self._engine.ocr(image_arg, cls=self.use_angle_cls)
        except Exception as e:
            return OCRResult(
                success=False,
                full_text="",
                lines=[],
                average_confidence=0.0,
                engine_name="PaddleOCR",
                warnings=[f"OCR processing failed: {str(e)}"]
            )

        # 4. Parse PaddleOCR result format:
        # PaddleOCR returns a list of pages, each containing:
        # [ [ [ [x1,y1],[x2,y2],[x3,y3],[x4,y4] ], (text, confidence) ], ... ]
        parsed_lines: List[OCRLine] = []
        confidences: List[float] = []

        if raw_results:
            # Handle list of page results
            for page_res in raw_results:
                if not page_res:
                    continue
                for item in page_res:
                    try:
                        bbox_coords, (text_content, conf) = item
                        conf_float = float(conf)
                        confidences.append(conf_float)

                        # Bounding box
                        xs = [pt[0] for pt in bbox_coords]
                        ys = [pt[1] for pt in bbox_coords]
                        bbox = OCRBoundingBox(
                            x_min=float(min(xs)),
                            y_min=float(min(ys)),
                            x_max=float(max(xs)),
                            y_max=float(max(ys)),
                        )

                        parsed_lines.append(
                            OCRLine(
                                text=str(text_content).strip(),
                                confidence=round(conf_float, 4),
                                bounding_box=bbox,
                                page_number=1,
                            )
                        )
                    except Exception:
                        continue

        full_text = "\n".join(line.text for line in parsed_lines)
        avg_conf = (sum(confidences) / len(confidences)) if confidences else 0.0

        return OCRResult(
            success=len(parsed_lines) > 0,
            full_text=full_text,
            lines=parsed_lines,
            average_confidence=round(avg_conf, 4),
            page_count=1,
            engine_name="PaddleOCR",
            warnings=[] if parsed_lines else ["No text detected in document image."]
        )
