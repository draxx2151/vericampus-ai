"""
VeriCampus AI — Document Quality Feature Extraction
Extracts 10 concrete, interpretable physical and optical signals from document images
and OCR results using OpenCV and Pillow.
"""
import io
from pathlib import Path
from typing import Optional, Union, Dict, Any, Tuple
import cv2
import numpy as np
from PIL import Image

from .schemas import QualityFeatures


def load_image_bgr(
    image_input: Union[str, Path, bytes, np.ndarray, Image.Image]
) -> Tuple[np.ndarray, int, int]:
    """
    Safely normalizes various input formats into a cv2 BGR uint8 ndarray.
    Returns (img_bgr, width, height).
    """
    if isinstance(image_input, np.ndarray):
        if len(image_input.shape) == 2:
            img_bgr = cv2.cvtColor(image_input, cv2.COLOR_GRAY2BGR)
        elif image_input.shape[2] == 4:
            img_bgr = cv2.cvtColor(image_input, cv2.COLOR_BGRA2BGR)
        elif image_input.shape[2] == 3:
            img_bgr = image_input.copy()
        else:
            raise ValueError(f"Unsupported array shape: {image_input.shape}")
        h, w = img_bgr.shape[:2]
        return img_bgr, w, h

    if isinstance(image_input, Image.Image):
        rgb = np.array(image_input.convert("RGB"))
        img_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        return img_bgr, image_input.width, image_input.height

    if isinstance(image_input, (str, Path)):
        p = Path(image_input)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"Image file does not exist: {p}")
        img_bytes = p.read_bytes()
    elif isinstance(image_input, bytes):
        img_bytes = image_input
    else:
        raise TypeError(f"Unsupported input type for image: {type(image_input)}")

    # Decode from memory bytes
    arr = np.frombuffer(img_bytes, np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        # Try PIL fallback (for TIFF or unusual formats)
        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        rgb = np.array(pil_img)
        img_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    h, w = img_bgr.shape[:2]
    return img_bgr, w, h


def estimate_skew_angle(gray: np.ndarray) -> float:
    """
    Estimates document skew angle in degrees using image thresholding
    and minimum area bounding box on prominent contours.
    """
    try:
        # Invert binary threshold to identify dark text on light background
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 50:
            return 0.0

        # Sample coordinates for performance if very large
        if len(coords) > 20_000:
            indices = np.random.choice(len(coords), 20_000, replace=False)
            coords = coords[indices]

        angle = cv2.minAreaRect(coords)[-1]
        # OpenCv minAreaRect returns angles in [-90, 0] or [0, 90]
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        return float(abs(angle))
    except Exception:
        return 0.0


def estimate_border_completeness(gray: np.ndarray) -> float:
    """
    Estimates whether document text or critical content is cut off at boundaries
    by examining text contour distances to image borders.
    """
    h, w = gray.shape
    try:
        # Segment foreground text (dark text on light background, threshold < 140 ignores light watermarks)
        _, thresh = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY_INV)
        # Ignore outermost 30px to allow for standard document borders
        if h <= 70 or w <= 70:
            return 1.0
        inner = thresh[30:h - 30, 30:w - 30]
        coords = np.column_stack(np.where(inner > 0))
        if len(coords) < 30:
            return 1.0

        y_min = int(np.min(coords[:, 0])) + 30
        y_max = int(np.max(coords[:, 0])) + 30
        x_min = int(np.min(coords[:, 1])) + 30
        x_max = int(np.max(coords[:, 1])) + 30

        # Cutoff occurs when text touches margin boundaries within 3px
        cut_left = x_min <= 33
        cut_top = y_min <= 33
        cut_right = (w - x_max) <= 33
        cut_bottom = (h - y_max) <= 33

        cut_edges = sum([cut_left, cut_top, cut_right, cut_bottom])
        completeness = max(0.40, 1.0 - (cut_edges * 0.15))
        return float(round(completeness, 3))
    except Exception:
        return 1.0


def estimate_noise_sigma(gray: np.ndarray) -> float:
    """
    Estimates high-frequency noise level by comparing image against median filtered image.
    """
    try:
        med = cv2.medianBlur(gray, 3)
        diff = cv2.absdiff(gray, med)
        return float(np.mean(diff))
    except Exception:
        return 0.0


def extract_quality_features(
    image_input: Union[str, Path, bytes, np.ndarray, Image.Image],
    ocr_result: Optional[Any] = None,
) -> QualityFeatures:
    """
    Extracts all 10 measurable quality features from image and optional OCR result.
    """
    img_bgr, width, height = load_image_bgr(image_input)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # 1. Image Resolution (Megapixels)
    mp = float((width * height) / 1_000_000.0)

    # 2. Blur / Sharpness via Laplacian Variance
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # 3. Normalized Sharpness Score (0 - 100)
    # Typical sharp document > 400, blurry < 80
    norm_sharpness = min(100.0, max(0.0, lap_var / 5.0))

    # 4. Brightness (Mean luminance)
    brightness_mean = float(np.mean(gray))

    # 5. Brightness Uniformity / Standard Deviation
    brightness_std = float(np.std(gray))

    # 6. Contrast (RMS contrast)
    contrast_rms = float(np.std(gray))

    # 7. High-frequency Noise
    noise_sigma = estimate_noise_sigma(gray)

    # 8. Skew Angle in degrees
    skew_angle = estimate_skew_angle(gray)

    # 9. Border Completeness Ratio (0.0 - 1.0)
    crop_completeness = estimate_border_completeness(gray)

    # 10. OCR Confidence & Coverage
    ocr_conf = 0.85  # Default estimate if OCR is not yet executed
    ocr_word_count = None
    ocr_text_len = None

    if ocr_result is not None:
        # Support dict, OCRResult model, or duck-typed object
        if hasattr(ocr_result, "average_confidence"):
            ocr_conf = float(ocr_result.average_confidence)
        elif isinstance(ocr_result, dict) and "average_confidence" in ocr_result:
            ocr_conf = float(ocr_result["average_confidence"])

        if hasattr(ocr_result, "full_text"):
            text = str(ocr_result.full_text)
            ocr_text_len = len(text)
            ocr_word_count = len(text.split())
        elif isinstance(ocr_result, dict) and "full_text" in ocr_result:
            text = str(ocr_result["full_text"])
            ocr_text_len = len(text)
            ocr_word_count = len(text.split())

    return QualityFeatures(
        resolution_megapixels=round(mp, 3),
        blur_laplacian_variance=round(lap_var, 2),
        normalized_sharpness=round(norm_sharpness, 2),
        brightness_mean=round(brightness_mean, 2),
        brightness_std=round(brightness_std, 2),
        contrast_rms=round(contrast_rms, 2),
        noise_estimate_sigma=round(noise_sigma, 2),
        skew_angle_degrees=round(skew_angle, 2),
        crop_margin_completeness=round(crop_completeness, 3),
        ocr_confidence=round(ocr_conf, 3),
        image_width=width,
        image_height=height,
        ocr_word_count=ocr_word_count,
        ocr_text_length=ocr_text_len,
    )
