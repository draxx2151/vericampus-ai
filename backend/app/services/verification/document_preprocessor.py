import io
import os
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any, Union
import cv2
import numpy as np
from PIL import Image, ImageOps
import pymupdf
from pydantic import BaseModel, Field

# Constants for document resource protection
MAX_UPLOAD_SIZE_BYTES = 2_621_440  # Exactly 2.5 MiB
MAX_PDF_PAGES = 5  # Limit multi-page PDF processing
MAX_IMAGE_PIXELS = 25_000_000  # Max 25 megapixels to prevent decompression bomb
MAX_IMAGE_DIMENSION = 6000  # Max width or height


class PreprocessedPage(BaseModel):
    page_number: int
    original_dimensions: Tuple[int, int]  # (width, height)
    processed_dimensions: Tuple[int, int]  # (width, height)
    operations_applied: List[str]
    image_bytes: bytes  # PNG bytes of preprocessed image for OCR
    deskew_angle: Optional[float] = None

    @property
    def width(self) -> int:
        return self.processed_dimensions[0]

    @property
    def height(self) -> int:
        return self.processed_dimensions[1]


class PreprocessingResult(BaseModel):
    success: bool
    is_pdf: bool
    page_count: int
    original_page_count: Optional[int] = None
    processed_pages: List[PreprocessedPage] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if self.original_page_count is None:
            self.original_page_count = self.page_count


class DocumentPreprocessor:
    """
    Local document preprocessor supporting PDFs and raster images (JPG, JPEG, PNG).
    Handles format detection, PDF rendering, grayscale conversion, contrast enhancement,
    denoising, and deskewing without destructive over-processing.
    """

    def __init__(
        self,
        max_pdf_pages: int = MAX_PDF_PAGES,
        max_pages: Optional[int] = None,
        enhance_contrast: bool = True,
        apply_deskew: bool = True,
        render_dpi: int = 200,
        target_dpi: Optional[int] = None,
    ):
        self.max_pdf_pages = max_pages if max_pages is not None else max_pdf_pages
        self.enhance_contrast = enhance_contrast
        self.apply_deskew = apply_deskew
        self.render_dpi = target_dpi if target_dpi is not None else render_dpi

    def preprocess(self, file_input: Union[str, Path, bytes], filename: Optional[str] = None) -> PreprocessingResult:
        warnings: List[str] = []

        # 1. Determine input source and bytes
        file_bytes: bytes
        safe_filename: str = filename or "document"

        if isinstance(file_input, (str, Path)):
            file_path = Path(file_input)
            if not file_path.exists() or not file_path.is_file():
                return PreprocessingResult(
                    success=False,
                    is_pdf=False,
                    page_count=0,
                    warnings=[f"Document file does not exist or is not a file: {file_path.name}"],
                )
            try:
                file_bytes = file_path.read_bytes()
                safe_filename = file_path.name
            except Exception as e:
                return PreprocessingResult(
                    success=False,
                    is_pdf=False,
                    page_count=0,
                    warnings=[f"Failed to read document file: {str(e)}"],
                )
        elif isinstance(file_input, bytes):
            file_bytes = file_input
        else:
            return PreprocessingResult(
                success=False,
                is_pdf=False,
                page_count=0,
                warnings=["Invalid input type: expected str, Path, or bytes."],
            )

        # 2. Check file size
        if len(file_bytes) == 0:
            return PreprocessingResult(
                success=False,
                is_pdf=False,
                page_count=0,
                warnings=["Document file is empty (0 bytes)."],
            )

        if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
            warnings.append(f"Document exceeds expected size limit ({len(file_bytes)} bytes).")

        # 3. Detect format: PDF vs Image
        is_pdf = file_bytes.startswith(b"%PDF-") or safe_filename.lower().endswith(".pdf")

        if is_pdf:
            return self._process_pdf(file_bytes, safe_filename, warnings)
        else:
            return self._process_image(file_bytes, safe_filename, warnings)

    def _process_pdf(self, pdf_bytes: bytes, filename: str, warnings: List[str]) -> PreprocessingResult:
        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            return PreprocessingResult(
                success=False,
                is_pdf=True,
                page_count=0,
                warnings=[f"Corrupted or invalid PDF document: {str(e)}"],
            )

        total_pages = len(doc)
        if total_pages == 0:
            doc.close()
            return PreprocessingResult(
                success=False,
                is_pdf=True,
                page_count=0,
                warnings=["PDF document contains 0 pages."],
            )

        pages_to_process = min(total_pages, self.max_pdf_pages)
        if total_pages > self.max_pdf_pages:
            warnings.append(
                f"PDF contains {total_pages} pages; processing is truncated and bounded to the first {self.max_pdf_pages} pages."
            )

        processed_pages: List[PreprocessedPage] = []

        try:
            for page_idx in range(pages_to_process):
                page = doc[page_idx]
                # Render page at high DPI for crisp OCR text recognition
                pix = page.get_pixmap(dpi=self.render_dpi)
                orig_w, orig_h = pix.width, pix.height

                # Convert pixmap bytes to numpy image array
                img_data = np.frombuffer(pix.samples, dtype=np.uint8)
                if pix.n == 4:
                    img = img_data.reshape((pix.height, pix.width, 4))
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                elif pix.n == 3:
                    img = img_data.reshape((pix.height, pix.width, 3))
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                elif pix.n == 1:
                    img = img_data.reshape((pix.height, pix.width))
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                else:
                    # Fallback via Pillow
                    pil_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

                processed_cv, ops, angle = self._apply_enhancements(img)
                _, out_bytes = cv2.imencode(".png", processed_cv)

                processed_pages.append(
                    PreprocessedPage(
                        page_number=page_idx + 1,
                        original_dimensions=(orig_w, orig_h),
                        processed_dimensions=(processed_cv.shape[1], processed_cv.shape[0]),
                        operations_applied=ops,
                        image_bytes=out_bytes.tobytes(),
                        deskew_angle=angle,
                    )
                )
        except Exception as e:
            warnings.append(f"Error occurred during PDF page rendering: {str(e)}")
            if not processed_pages:
                doc.close()
                return PreprocessingResult(
                    success=False,
                    is_pdf=True,
                    page_count=total_pages,
                    warnings=warnings,
                )
        finally:
            doc.close()

        return PreprocessingResult(
            success=len(processed_pages) > 0,
            is_pdf=True,
            page_count=total_pages,
            processed_pages=processed_pages,
            warnings=warnings,
            metadata={"filename": filename, "rendered_dpi": self.render_dpi},
        )

    def _process_image(self, img_bytes: bytes, filename: str, warnings: List[str]) -> PreprocessingResult:
        try:
            # 1. Inspect with Pillow for metadata & orientation
            pil_img = Image.open(io.BytesIO(img_bytes))
            pil_img.verify()
            # Reopen after verify
            pil_img = Image.open(io.BytesIO(img_bytes))
            pil_img = ImageOps.exif_transpose(pil_img)
            orig_w, orig_h = pil_img.size

            if orig_w == 0 or orig_h == 0:
                return PreprocessingResult(
                    success=False,
                    is_pdf=False,
                    page_count=0,
                    warnings=["Image has zero dimensions (invalid image)."],
                )

            if orig_w * orig_h > MAX_IMAGE_PIXELS:
                warnings.append(f"Image resolution ({orig_w}x{orig_h}) exceeds maximum recommended size.")

            # Convert to RGB numpy array
            rgb_img = pil_img.convert("RGB")
            cv_img = cv2.cvtColor(np.array(rgb_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            return PreprocessingResult(
                success=False,
                is_pdf=False,
                page_count=0,
                warnings=[f"Failed to load or decode image: {str(e)}"],
            )

        processed_cv, ops, angle = self._apply_enhancements(cv_img)
        _, out_bytes = cv2.imencode(".png", processed_cv)

        page_result = PreprocessedPage(
            page_number=1,
            original_dimensions=(orig_w, orig_h),
            processed_dimensions=(processed_cv.shape[1], processed_cv.shape[0]),
            operations_applied=ops,
            image_bytes=out_bytes.tobytes(),
            deskew_angle=angle,
        )

        return PreprocessingResult(
            success=True,
            is_pdf=False,
            page_count=1,
            processed_pages=[page_result],
            warnings=warnings,
            metadata={"filename": filename},
        )

    def _apply_enhancements(self, img: np.ndarray) -> Tuple[np.ndarray, List[str], Optional[float]]:
        operations: List[str] = []
        deskew_angle: Optional[float] = None

        # 1. Resize down if excessively large
        h, w = img.shape[:2]
        if max(h, w) > MAX_IMAGE_DIMENSION:
            scale = MAX_IMAGE_DIMENSION / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            operations.append(f"resized_{w}x{h}_to_{new_w}x{new_h}")

        # 2. Grayscale conversion
        if len(img.shape) == 3 and img.shape[2] == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            operations.append("converted_to_grayscale")
        else:
            gray = img.copy()

        # 3. Deskew where practical
        if self.apply_deskew:
            angle = self._detect_skew_angle(gray)
            if angle is not None and abs(angle) >= 0.5 and abs(angle) <= 15.0:
                gray = self._rotate_image(gray, angle)
                deskew_angle = angle
                operations.append(f"deskewed_{angle:.1f}_deg")

        # 4. Contrast Enhancement via CLAHE
        if self.enhance_contrast:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
            operations.append("clahe_contrast_enhancement")

        # 5. Denoising: gentle median blur to eliminate grain without smudging characters
        gray = cv2.medianBlur(gray, 3)
        operations.append("median_denoise_filter")

        # Convert back to BGR for uniform color-independent OCR input
        final_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        return final_bgr, operations, deskew_angle

    @staticmethod
    def _detect_skew_angle(gray_img: np.ndarray) -> Optional[float]:
        try:
            # Threshold to isolate dark text lines
            _, thresh = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            coords = np.column_stack(np.where(thresh > 0))
            if coords.shape[0] < 50:
                return None
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            return float(angle)
        except Exception:
            return None

    @staticmethod
    def _rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
