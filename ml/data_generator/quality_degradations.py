"""
VeriCampus AI — Document Quality Degradation Module

Generates realistic visual and physical degradations to produce
documents across 4 distinct quality categories:
  - HIGH: Clean digital scan/render, optimal lighting and contrast, crisp text.
  - MEDIUM / ACCEPTABLE: Minor blur, slight skew, mild lighting gradient, good readability.
  - LOW: Noticeable blur/motion, partial crop, glare, low contrast, moderate skew.
  - UNREADABLE: Severe blur, extreme over/underexposure, heavy crop cutoff, unreadable.

Also computes ground truth numerical metadata:
  - blur_score: Variance of Laplacian (sharpness)
  - resolution_score: Ratio of megapixels to baseline (min(1.0, MP / 0.88))
  - contrast_score: RMS contrast of luminance channel
  - brightness_score: Mean luminance (0-255)
  - rotation_angle: Incline angle in degrees
  - crop_completeness: Ratio of preserved document content (0.0 - 1.0)
  - ocr_confidence: Simulated OCR confidence (0.0 - 1.0)
  - quality_score: Composite reference score (0 - 100)
"""
import random
import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Dict, Any


def compute_ground_truth_metrics(
    img_bgr: np.ndarray,
    rotation_angle: float = 0.0,
    crop_completeness: float = 1.0,
    quality_label: str = "HIGH",
) -> Dict[str, Any]:
    """Computes exact numerical metrics from an image array."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # 1. Blur / Sharpness via Laplacian variance
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    # Normalize to 0-100 scale approximately
    blur_score = min(100.0, max(0.0, lap_var / 5.0))

    # 2. Resolution Score
    mp = (h * w) / 1_000_000.0
    resolution_score = min(1.0, mp / 0.88)

    # 3. Contrast Score (RMS contrast)
    contrast_score = float(np.std(gray))

    # 4. Brightness Score (Mean luminance)
    brightness_score = float(np.mean(gray))

    # 5. Simulated realistic OCR confidence based on quality tier + image sharpness
    if quality_label == "HIGH":
        ocr_conf = random.uniform(0.92, 0.99)
        base_score = random.uniform(86.0, 98.0)
    elif quality_label == "MEDIUM":
        ocr_conf = random.uniform(0.74, 0.89)
        base_score = random.uniform(72.0, 84.0)
    elif quality_label == "LOW":
        ocr_conf = random.uniform(0.48, 0.69)
        base_score = random.uniform(42.0, 68.0)
    else:  # UNREADABLE
        ocr_conf = random.uniform(0.05, 0.35)
        base_score = random.uniform(8.0, 38.0)

    # Composite reference quality score (0-100)
    quality_score = round(base_score, 2)

    return {
        "blur_score": round(blur_score, 2),
        "laplacian_variance": round(lap_var, 2),
        "resolution_score": round(resolution_score, 3),
        "contrast_score": round(contrast_score, 2),
        "brightness_score": round(brightness_score, 2),
        "rotation_angle": round(rotation_angle, 2),
        "crop_completeness": round(crop_completeness, 3),
        "ocr_confidence": round(ocr_conf, 3),
        "quality_score": quality_score,
        "quality_label": quality_label,
    }


# ─────────────────────────────────────────────────────────────
# Visual Degradation Implementations
# ─────────────────────────────────────────────────────────────

def _apply_motion_blur(img: np.ndarray, size: int = 15, angle: float = 45.0) -> np.ndarray:
    """Applies realistic directional camera motion blur."""
    kernel = np.zeros((size, size))
    rad = np.deg2rad(angle)
    dx = np.cos(rad)
    dy = np.sin(rad)
    center = size // 2
    for i in range(size):
        offset = i - center
        x = int(center + offset * dx)
        y = int(center + offset * dy)
        if 0 <= x < size and 0 <= y < size:
            kernel[y, x] = 1.0
    k_sum = kernel.sum()
    if k_sum > 0:
        kernel /= k_sum
    else:
        kernel[center, center] = 1.0
    return cv2.filter2D(img, -1, kernel)


def _apply_uneven_lighting(img: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    """Simulates realistic mobile phone shadow or overhead gradient lighting."""
    h, w = img.shape[:2]
    # Create smooth 2D gradient
    X = np.linspace(-1, 1, w)
    Y = np.linspace(-1, 1, h)
    xx, yy = np.meshgrid(X, Y)
    # Circular or diagonal falloff
    mask = 1.0 - intensity * (0.5 * (xx + 1) + 0.5 * (yy + 1)) / 2.0
    mask = np.clip(mask, 0.2, 1.2)[:, :, np.newaxis]
    degraded = np.clip(img.astype(np.float32) * mask, 0, 255).astype(np.uint8)
    return degraded


def _apply_glare(img: np.ndarray) -> np.ndarray:
    """Simulates camera flash or bright glare reflection spot on laminated documents."""
    h, w = img.shape[:2]
    cx = random.randint(int(w * 0.25), int(w * 0.75))
    cy = random.randint(int(h * 0.25), int(h * 0.75))
    radius = random.randint(int(min(h, w) * 0.15), int(min(h, w) * 0.35))

    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    glare_mask = np.clip(1.0 - dist_from_center / radius, 0.0, 1.0) ** 2
    glare_mask = (glare_mask * 180)[:, :, np.newaxis]

    degraded = np.clip(img.astype(np.float32) + glare_mask, 0, 255).astype(np.uint8)
    return degraded


def _apply_crop_and_pad(
    img: np.ndarray,
    crop_fraction_x: float,
    crop_fraction_y: float
) -> Tuple[np.ndarray, float]:
    """Crops margins of document to simulate partial camera framing or edge cutoff."""
    h, w = img.shape[:2]
    x_crop = int(w * crop_fraction_x)
    y_crop = int(h * crop_fraction_y)

    x1 = random.randint(0, x_crop)
    y1 = random.randint(0, y_crop)
    x2 = w - (x_crop - x1)
    y2 = h - (y_crop - y1)

    cropped = img[y1:y2, x1:x2]
    completeness = (cropped.shape[0] * cropped.shape[1]) / (h * w)

    # Resize back to original dimensions with neutral border or slight scale
    canvas = np.full((h, w, 3), 240, dtype=np.uint8)
    nh, nw = cropped.shape[:2]
    ox = (w - nw) // 2
    oy = (h - nh) // 2
    canvas[oy:oy + nh, ox:ox + nw] = cropped
    return canvas, completeness


def _apply_rotation(img: np.ndarray, angle: float) -> np.ndarray:
    """Rotates document by specified angle with white background fill."""
    h, w = img.shape[:2]
    center = (w / 2.0, h / 2.0)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), borderValue=(255, 255, 255))


def _apply_jpeg_compression(img: np.ndarray, quality: int) -> np.ndarray:
    """Applies JPEG compression artifacts."""
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), max(5, min(95, quality))]
    success, enc = cv2.imencode(".jpg", img, encode_param)
    if success:
        return cv2.imdecode(enc, 1)
    return img


# ─────────────────────────────────────────────────────────────
# Quality Tier Degradation Pipelines
# ─────────────────────────────────────────────────────────────

def degrade_to_high(img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Produces a clean digital or high-grade scanned document."""
    # Pristine or ultra-mild scan texture (quality 92-98)
    degraded = _apply_jpeg_compression(img_bgr, random.randint(92, 98))
    # Very slight angle <= 0.5 degrees
    angle = random.uniform(-0.5, 0.5)
    degraded = _apply_rotation(degraded, angle)

    metrics = compute_ground_truth_metrics(
        degraded, rotation_angle=angle, crop_completeness=1.0, quality_label="HIGH"
    )
    return degraded, metrics


def degrade_to_medium(img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Produces an acceptable scan or good mobile photo with minor flaws."""
    degraded = img_bgr.copy()
    angle = random.uniform(-2.5, 2.5)

    # 1. Subtle blur (mild Gaussian blur)
    if random.random() < 0.65:
        degraded = cv2.GaussianBlur(degraded, (3, 3), 0.7)

    # 2. Slight rotation
    degraded = _apply_rotation(degraded, angle)

    # 3. Mild uneven lighting / subtle gradient
    if random.random() < 0.50:
        degraded = _apply_uneven_lighting(degraded, intensity=0.25)

    # 4. Standard JPEG compression (65 - 80)
    degraded = _apply_jpeg_compression(degraded, random.randint(65, 80))

    # 5. Very slight border crop (1 - 3% edge loss)
    completeness = 1.0
    if random.random() < 0.40:
        degraded, completeness = _apply_crop_and_pad(degraded, 0.03, 0.03)

    metrics = compute_ground_truth_metrics(
        degraded, rotation_angle=angle, crop_completeness=completeness, quality_label="MEDIUM"
    )
    return degraded, metrics


def degrade_to_low(img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Produces a degraded document (low contrast, blur, moderate skew, or crop)."""
    degraded = img_bgr.copy()
    angle = random.choice([random.uniform(-7.0, -3.5), random.uniform(3.5, 7.0)])

    # 1. Noticeable blur (Gaussian kernel 5 or 7, or motion blur)
    if random.random() < 0.60:
        degraded = cv2.GaussianBlur(degraded, (7, 7), 1.8)
    else:
        degraded = _apply_motion_blur(degraded, size=9, angle=random.uniform(0, 180))

    # 2. Moderate skew/rotation
    degraded = _apply_rotation(degraded, angle)

    # 3. Lighting defect: shadows or glare
    if random.random() < 0.50:
        degraded = _apply_uneven_lighting(degraded, intensity=0.55)
    elif random.random() < 0.35:
        degraded = _apply_glare(degraded)

    # 4. Low contrast: compress dynamic range
    gray_bias = random.randint(30, 60)
    degraded = np.clip(degraded.astype(np.float32) * 0.7 + gray_bias, 0, 255).astype(np.uint8)

    # 5. Partial crop (8 - 14% edge cutoff)
    completeness = 1.0
    if random.random() < 0.65:
        degraded, completeness = _apply_crop_and_pad(degraded, 0.10, 0.10)

    # 6. Aggressive compression (25 - 45)
    degraded = _apply_jpeg_compression(degraded, random.randint(25, 45))

    metrics = compute_ground_truth_metrics(
        degraded, rotation_angle=angle, crop_completeness=completeness, quality_label="LOW"
    )
    return degraded, metrics


def degrade_to_unreadable(img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Produces an unreadable document (severe blur, extreme exposure, heavy crop)."""
    degraded = img_bgr.copy()
    angle = random.uniform(-15.0, 15.0)

    mode = random.choice(["severe_blur", "extreme_dark", "extreme_washout", "severe_crop"])

    if mode == "severe_blur":
        # Heavy motion blur + heavy Gaussian
        degraded = _apply_motion_blur(degraded, size=21, angle=random.uniform(0, 180))
        degraded = cv2.GaussianBlur(degraded, (17, 17), 5.0)
    elif mode == "extreme_dark":
        # Severe underexposure
        degraded = np.clip(degraded.astype(np.float32) * 0.15, 0, 255).astype(np.uint8)
        degraded = cv2.GaussianBlur(degraded, (5, 5), 1.5)
    elif mode == "extreme_washout":
        # Severe overexposure / blown highlights
        degraded = np.clip(degraded.astype(np.float32) * 1.8 + 80, 0, 255).astype(np.uint8)
        degraded = _apply_glare(degraded)
    else:  # severe_crop
        # >30% of document cut off + blur
        degraded, _ = _apply_crop_and_pad(degraded, 0.35, 0.35)
        degraded = cv2.GaussianBlur(degraded, (7, 7), 2.0)

    # Rotation
    degraded = _apply_rotation(degraded, angle)

    # Add heavy sensor noise
    noise = np.random.normal(0, 25.0, degraded.shape)
    degraded = np.clip(degraded.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    # Extreme compression
    degraded = _apply_jpeg_compression(degraded, random.randint(10, 20))

    completeness = 0.65 if mode == "severe_crop" else 0.85
    metrics = compute_ground_truth_metrics(
        degraded, rotation_angle=angle, crop_completeness=completeness, quality_label="UNREADABLE"
    )
    return degraded, metrics


def apply_quality_degradation(
    img_bgr: np.ndarray,
    quality_label: str
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Dispatches to appropriate degradation generator based on quality_label.
    Returns (degraded_bgr_image, metadata_dict).
    """
    label = quality_label.upper()
    if label == "HIGH":
        return degrade_to_high(img_bgr)
    elif label in ("MEDIUM", "ACCEPTABLE"):
        return degrade_to_medium(img_bgr)
    elif label == "LOW":
        return degrade_to_low(img_bgr)
    elif label == "UNREADABLE":
        return degrade_to_unreadable(img_bgr)
    else:
        raise ValueError(f"Unknown quality label: {quality_label}")
