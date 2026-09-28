"""
VeriCampus AI — Stage 4: Visual Tamper Feature Extraction
Extracts physical and optical manipulation signals:
1. Error Level Analysis (ELA) for localized recompression artifacts.
2. Localized blur / sharpness variance inconsistency across tiles.
3. High-frequency noise variance distribution across document regions.
4. Copy-move block duplication heuristics.
NOTE: All visual signals are advisory evidence (WEAK/MODERATE strength).
They never prove forgery on their own.
"""
from io import BytesIO
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import numpy as np
from PIL import Image
import cv2

from ..schemas import TamperSignal, SignalCategory, SignalSeverity, CheckStatus, EvidenceStrength
from ..config import (
    ELA_RESCALE,
    ELA_QUALITY,
    ELA_ANOMALY_THRESHOLD,
    TILE_SIZE,
    MIN_TILES_FOR_ANALYSIS,
    BLUR_VARIANCE_RATIO_THRESHOLD,
    NOISE_INCONSISTENCY_THRESHOLD,
    COPY_MOVE_SIMILARITY_THRESHOLD,
    COPY_MOVE_MIN_DISTANCE_PIXELS,
)


def load_image_as_rgb(image_or_path: Any) -> Optional[np.ndarray]:
    """
    Safely loads input into a uint8 RGB numpy array.
    Supports file paths, Path objects, bytes, BytesIO, or PIL Images.
    """
    if image_or_path is None:
        return None

    try:
        if isinstance(image_or_path, np.ndarray):
            if len(image_or_path.shape) == 2:
                return cv2.cvtColor(image_or_path, cv2.COLOR_GRAY2RGB)
            elif image_or_path.shape[2] == 4:
                return cv2.cvtColor(image_or_path, cv2.COLOR_RGBA2RGB)
            elif image_or_path.shape[2] == 3:
                return image_or_path
            return None

        if isinstance(image_or_path, Image.Image):
            rgb_img = image_or_path.convert("RGB")
            return np.array(rgb_img, dtype=np.uint8)

        if isinstance(image_or_path, (str, Path)):
            p = Path(image_or_path)
            if not p.exists() or p.is_dir():
                return None
            with Image.open(p) as img:
                return np.array(img.convert("RGB"), dtype=np.uint8)

        if isinstance(image_or_path, (bytes, bytearray)):
            with Image.open(BytesIO(image_or_path)) as img:
                return np.array(img.convert("RGB"), dtype=np.uint8)

        if hasattr(image_or_path, "read"):
            pos = image_or_path.tell() if hasattr(image_or_path, "tell") else None
            data = image_or_path.read()
            if pos is not None:
                image_or_path.seek(pos)
            with Image.open(BytesIO(data)) as img:
                return np.array(img.convert("RGB"), dtype=np.uint8)
    except Exception:
        return None

    return None


def extract_ela_signal(image_np: np.ndarray, doc_type: str) -> TamperSignal:
    """
    Performs Error Level Analysis (ELA) by re-compressing the image at JPEG quality 90
    and measuring the pixel-level difference distribution.
    """
    try:
        pil_img = Image.fromarray(image_np)
        buffer = BytesIO()
        pil_img.save(buffer, format="JPEG", quality=ELA_QUALITY)
        buffer.seek(0)
        recompressed = Image.open(buffer).convert("RGB")
        recompressed_np = np.array(recompressed, dtype=np.float32)

        orig_float = image_np.astype(np.float32)
        diff = np.abs(orig_float - recompressed_np)
        rescaled_diff = diff * (ELA_RESCALE / 255.0) * 100.0

        mean_diff = float(np.mean(rescaled_diff))
        std_diff = float(np.std(rescaled_diff))
        max_diff = float(np.max(rescaled_diff))

        # Clean document: low standard deviation in error rates across regions
        # Manipulated document: localized patches with sharply differing compression histories
        anomaly_metric = (std_diff * 2.0) + (mean_diff * 0.5)

        if anomaly_metric > ELA_ANOMALY_THRESHOLD:
            score = max(0.0, 100.0 - (anomaly_metric * 1.8))
            return TamperSignal(
                signal_name="ela_compression_anomaly",
                category=SignalCategory.VISUAL,
                severity=SignalSeverity.LOW,
                score=round(score, 1),
                confidence=0.75,
                status=CheckStatus.WARNING,
                explanation=(
                    f"Error Level Analysis identified localized compression rate variations "
                    f"(anomaly index {anomaly_metric:.1f} > {ELA_ANOMALY_THRESHOLD}). "
                    f"This may reflect multi-generation compression or digital editing."
                ),
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )
        else:
            clean_score = min(100.0, max(85.0, 100.0 - anomaly_metric))
            return TamperSignal(
                signal_name="ela_compression_anomaly",
                category=SignalCategory.VISUAL,
                severity=SignalSeverity.INFO,
                score=round(clean_score, 1),
                confidence=0.85,
                status=CheckStatus.PASS,
                explanation=f"Error Level Analysis is uniform across image regions (anomaly index {anomaly_metric:.1f}).",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )
    except Exception as e:
        return TamperSignal(
            signal_name="ela_compression_anomaly",
            category=SignalCategory.VISUAL,
            severity=SignalSeverity.INFO,
            score=100.0,
            confidence=0.0,
            status=CheckStatus.NOT_AVAILABLE,
            explanation=f"Error Level Analysis could not be computed: {str(e)}",
            affected_document=doc_type,
            evidence_strength=EvidenceStrength.WEAK,
        )


def extract_local_blur_signal(image_np: np.ndarray, doc_type: str) -> TamperSignal:
    """
    Divides document into tiles and computes Laplacian variance (sharpness) per tile.
    Identifies unnatural sharpness discrepancies (e.g. sharp digital text pasted on blurry scan).
    """
    try:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape

        if h < TILE_SIZE * 2 or w < TILE_SIZE * 2:
            return TamperSignal(
                signal_name="local_blur_inconsistency",
                category=SignalCategory.VISUAL,
                severity=SignalSeverity.INFO,
                score=100.0,
                confidence=0.5,
                status=CheckStatus.PASS,
                explanation="Document dimensions too small for multi-tile sharpness analysis.",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )

        tile_variances: List[float] = []
        for y in range(0, h - TILE_SIZE, TILE_SIZE):
            for x in range(0, w - TILE_SIZE, TILE_SIZE):
                tile = gray[y : y + TILE_SIZE, x : x + TILE_SIZE]
                # Filter out solid background / blank tiles
                if np.std(tile) > 12.0:
                    lap_var = float(cv2.Laplacian(tile, cv2.CV_64F).var())
                    tile_variances.append(lap_var)

        if len(tile_variances) < MIN_TILES_FOR_ANALYSIS:
            return TamperSignal(
                signal_name="local_blur_inconsistency",
                category=SignalCategory.VISUAL,
                severity=SignalSeverity.INFO,
                score=100.0,
                confidence=0.5,
                status=CheckStatus.PASS,
                explanation="Insufficient content tiles for sharpness variance analysis.",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )

        p95 = float(np.percentile(tile_variances, 95))
        p25 = float(np.percentile(tile_variances, 25))
        ratio = p95 / max(p25, 1.0)

        if ratio > BLUR_VARIANCE_RATIO_THRESHOLD:
            score = max(30.0, 100.0 - (ratio * 12.0))
            return TamperSignal(
                signal_name="local_blur_inconsistency",
                category=SignalCategory.VISUAL,
                severity=SignalSeverity.LOW,
                score=round(score, 1),
                confidence=0.70,
                status=CheckStatus.WARNING,
                explanation=(
                    f"Sharpness disparity detected across content regions (ratio {ratio:.1f} > {BLUR_VARIANCE_RATIO_THRESHOLD}). "
                    f"Portions of the document are significantly sharper than the background field."
                ),
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )
        else:
            return TamperSignal(
                signal_name="local_blur_inconsistency",
                category=SignalCategory.VISUAL,
                severity=SignalSeverity.INFO,
                score=95.0,
                confidence=0.85,
                status=CheckStatus.PASS,
                explanation=f"Sharpness distribution is consistent across content regions (ratio {ratio:.1f}).",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )
    except Exception as e:
        return TamperSignal(
            signal_name="local_blur_inconsistency",
            category=SignalCategory.VISUAL,
            severity=SignalSeverity.INFO,
            score=100.0,
            confidence=0.0,
            status=CheckStatus.NOT_AVAILABLE,
            explanation=f"Sharpness analysis unavailable: {str(e)}",
            affected_document=doc_type,
            evidence_strength=EvidenceStrength.WEAK,
        )


def extract_noise_variance_signal(image_np: np.ndarray, doc_type: str) -> TamperSignal:
    """
    Extracts high-frequency noise residual and checks for noise variance consistency.
    Digital insertions often exhibit zero noise or incompatible noise grain.
    """
    try:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape

        if h < TILE_SIZE * 2 or w < TILE_SIZE * 2:
            return TamperSignal(
                signal_name="noise_variance_anomaly",
                category=SignalCategory.VISUAL,
                severity=SignalSeverity.INFO,
                score=100.0,
                confidence=0.5,
                status=CheckStatus.PASS,
                explanation="Image dimensions too small for tile noise analysis.",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )

        # High-pass noise residual via median filter subtraction
        med = cv2.medianBlur(gray, 3)
        residual = cv2.absdiff(gray, med)

        noise_variances = []
        for y in range(0, h - TILE_SIZE, TILE_SIZE):
            for x in range(0, w - TILE_SIZE, TILE_SIZE):
                tile_orig = gray[y : y + TILE_SIZE, x : x + TILE_SIZE]
                if np.std(tile_orig) > 10.0:
                    tile_res = residual[y : y + TILE_SIZE, x : x + TILE_SIZE]
                    noise_variances.append(float(np.var(tile_res)))

        if len(noise_variances) < MIN_TILES_FOR_ANALYSIS:
            return TamperSignal(
                signal_name="noise_variance_anomaly",
                category=SignalCategory.VISUAL,
                severity=SignalSeverity.INFO,
                score=100.0,
                confidence=0.5,
                status=CheckStatus.PASS,
                explanation="Insufficient content tiles for noise variance analysis.",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )

        p90 = float(np.percentile(noise_variances, 90))
        med_noise = float(np.median(noise_variances))
        noise_ratio = p90 / max(med_noise, 0.5)

        if noise_ratio > NOISE_INCONSISTENCY_THRESHOLD:
            score = max(35.0, 100.0 - (noise_ratio * 15.0))
            return TamperSignal(
                signal_name="noise_variance_anomaly",
                category=SignalCategory.VISUAL,
                severity=SignalSeverity.LOW,
                score=round(score, 1),
                confidence=0.68,
                status=CheckStatus.WARNING,
                explanation=(
                    f"High-frequency noise pattern is non-uniform (variance ratio {noise_ratio:.1f} > {NOISE_INCONSISTENCY_THRESHOLD}). "
                    f"Potential visual artifact or multi-source composition."
                ),
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )
        else:
            return TamperSignal(
                signal_name="noise_variance_anomaly",
                category=SignalCategory.VISUAL,
                severity=SignalSeverity.INFO,
                score=96.0,
                confidence=0.85,
                status=CheckStatus.PASS,
                explanation=f"Noise grain distribution is uniform across content areas (ratio {noise_ratio:.1f}).",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )
    except Exception as e:
        return TamperSignal(
            signal_name="noise_variance_anomaly",
            category=SignalCategory.VISUAL,
            severity=SignalSeverity.INFO,
            score=100.0,
            confidence=0.0,
            status=CheckStatus.NOT_AVAILABLE,
            explanation=f"Noise analysis unavailable: {str(e)}",
            affected_document=doc_type,
            evidence_strength=EvidenceStrength.WEAK,
        )


def extract_copy_move_signal(image_np: np.ndarray, doc_type: str) -> TamperSignal:
    """
    Fast block-matching heuristic for detecting duplicate text or stamp regions.
    Downscales image to keep runtime fast and robust.
    """
    try:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        # Downscale if large
        target_w = 400
        if gray.shape[1] > target_w:
            scale = target_w / float(gray.shape[1])
            target_h = int(gray.shape[0] * scale)
            small = cv2.resize(gray, (target_w, target_h), interpolation=cv2.INTER_AREA)
        else:
            small = gray

        bsize = 16
        step = 8
        blocks: List[Tuple[int, int, np.ndarray]] = []
        sh, sw = small.shape

        for y in range(0, sh - bsize, step):
            for x in range(0, sw - bsize, step):
                blk = small[y : y + bsize, x : x + bsize]
                # Filter out blank/solid blocks
                if np.std(blk) > 18.0:
                    blocks.append((x, y, blk))

        duplicate_detected = False
        duplicate_coords = None

        # Sample comparison if reasonable block count
        if len(blocks) > 10 and len(blocks) < 500:
            for i in range(len(blocks)):
                x1, y1, b1 = blocks[i]
                b1_norm = (b1 - np.mean(b1)) / (np.std(b1) + 1e-5)
                for j in range(i + 1, min(i + 40, len(blocks))):
                    x2, y2, b2 = blocks[j]
                    dist = np.hypot(x1 - x2, y1 - y2)
                    if dist >= COPY_MOVE_MIN_DISTANCE_PIXELS:
                        b2_norm = (b2 - np.mean(b2)) / (np.std(b2) + 1e-5)
                        corr = np.mean(b1_norm * b2_norm)
                        if corr > COPY_MOVE_SIMILARITY_THRESHOLD:
                            duplicate_detected = True
                            duplicate_coords = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                            break
                if duplicate_detected:
                    break

        if duplicate_detected:
            return TamperSignal(
                signal_name="copy_move_duplicate_blocks",
                category=SignalCategory.VISUAL,
                severity=SignalSeverity.MEDIUM,
                score=55.0,
                confidence=0.72,
                status=CheckStatus.WARNING,
                explanation="Suspicious duplicate textural patterns detected in distant regions of the document.",
                affected_region=duplicate_coords,
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.MODERATE,
            )
        else:
            return TamperSignal(
                signal_name="copy_move_duplicate_blocks",
                category=SignalCategory.VISUAL,
                severity=SignalSeverity.INFO,
                score=100.0,
                confidence=0.80,
                status=CheckStatus.PASS,
                explanation="No duplicate copy-move texture patterns detected.",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )
    except Exception as e:
        return TamperSignal(
            signal_name="copy_move_duplicate_blocks",
            category=SignalCategory.VISUAL,
            severity=SignalSeverity.INFO,
            score=100.0,
            confidence=0.0,
            status=CheckStatus.NOT_AVAILABLE,
            explanation=f"Copy-move analysis unavailable: {str(e)}",
            affected_document=doc_type,
            evidence_strength=EvidenceStrength.WEAK,
        )


def extract_visual_signals(image_or_path: Any, doc_type: str) -> List[TamperSignal]:
    """Extracts all visual tamper signals for a given document."""
    image_np = load_image_as_rgb(image_or_path)
    if image_np is None:
        return [
            TamperSignal(
                signal_name="visual_analysis_skipped",
                category=SignalCategory.VISUAL,
                severity=SignalSeverity.INFO,
                score=100.0,
                confidence=0.0,
                status=CheckStatus.NOT_AVAILABLE,
                explanation=f"Visual tamper analysis skipped: Image file not available or unreadable for {doc_type}.",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )
        ]

    return [
        extract_ela_signal(image_np, doc_type),
        extract_local_blur_signal(image_np, doc_type),
        extract_noise_variance_signal(image_np, doc_type),
        extract_copy_move_signal(image_np, doc_type),
    ]
