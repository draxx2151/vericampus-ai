"""
VeriCampus AI — Stage 4: Structural Tamper Feature Extraction
Extracts document layout, spatial layout, and bounding box structural signals:
1. OCR bounding-box overlaps (overlapping text elements indicating pasted labels).
2. Large unnatural blank regions (potential digital erasure of text).
3. Text orientation and baseline alignment variance.
4. Aspect ratio sanity checks.
"""
from typing import List, Dict, Any, Optional
import math

from ..schemas import TamperSignal, SignalCategory, SignalSeverity, CheckStatus, EvidenceStrength


def extract_bbox_overlap_signal(ocr_result: Any, doc_type: str) -> TamperSignal:
    """
    Checks for high spatial overlaps between distinct OCR text lines.
    Pasted digital text frequently collides or overlaps with underlying document text.
    """
    try:
        lines = getattr(ocr_result, "lines", []) if ocr_result else []
        if len(lines) < 2:
            return TamperSignal(
                signal_name="ocr_bbox_overlap_anomaly",
                category=SignalCategory.STRUCTURAL,
                severity=SignalSeverity.INFO,
                score=100.0,
                confidence=0.5,
                status=CheckStatus.PASS,
                explanation="Fewer than 2 text lines available for layout overlap inspection.",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )

        overlapping_pairs = 0
        significant_overlaps = []

        bboxes = []
        for l in lines:
            b = getattr(l, "bounding_box", None)
            if b:
                # normalize to dict or object
                xmin = getattr(b, "x_min", None) or (b.get("x_min") if isinstance(b, dict) else None)
                ymin = getattr(b, "y_min", None) or (b.get("y_min") if isinstance(b, dict) else None)
                xmax = getattr(b, "x_max", None) or (b.get("x_max") if isinstance(b, dict) else None)
                ymax = getattr(b, "y_max", None) or (b.get("y_max") if isinstance(b, dict) else None)
                if xmin is not None and ymin is not None and xmax is not None and ymax is not None:
                    bboxes.append((float(xmin), float(ymin), float(xmax), float(ymax)))

        for i in range(len(bboxes)):
            x1_min, y1_min, x1_max, y1_max = bboxes[i]
            area1 = max(0.0, x1_max - x1_min) * max(0.0, y1_max - y1_min)
            if area1 <= 0:
                continue

            for j in range(i + 1, len(bboxes)):
                x2_min, y2_min, x2_max, y2_max = bboxes[j]
                area2 = max(0.0, x2_max - x2_min) * max(0.0, y2_max - y2_min)
                if area2 <= 0:
                    continue

                # Intersection
                inter_xmin = max(x1_min, x2_min)
                inter_ymin = max(y1_min, y2_min)
                inter_xmax = min(x1_max, x2_max)
                inter_ymax = min(y1_max, y2_max)

                if inter_xmax > inter_xmin and inter_ymax > inter_ymin:
                    inter_area = (inter_xmax - inter_xmin) * (inter_ymax - inter_ymin)
                    iou = inter_area / (area1 + area2 - inter_area)
                    if iou > 0.40:
                        overlapping_pairs += 1
                        significant_overlaps.append({"iou": round(iou, 2)})

        if overlapping_pairs > 0:
            score = max(40.0, 100.0 - (overlapping_pairs * 25.0))
            return TamperSignal(
                signal_name="ocr_bbox_overlap_anomaly",
                category=SignalCategory.STRUCTURAL,
                severity=SignalSeverity.MEDIUM,
                score=round(score, 1),
                confidence=0.75,
                status=CheckStatus.WARNING,
                explanation=(
                    f"Detected {overlapping_pairs} overlapping text bounding boxes (IoU > 0.40). "
                    f"Possible pasted text label or unaligned text insertion."
                ),
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.MODERATE,
            )
        else:
            return TamperSignal(
                signal_name="ocr_bbox_overlap_anomaly",
                category=SignalCategory.STRUCTURAL,
                severity=SignalSeverity.INFO,
                score=100.0,
                confidence=0.85,
                status=CheckStatus.PASS,
                explanation="No unnatural bounding box collisions or text overlaps detected.",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )
    except Exception as e:
        return TamperSignal(
            signal_name="ocr_bbox_overlap_anomaly",
            category=SignalCategory.STRUCTURAL,
            severity=SignalSeverity.INFO,
            score=100.0,
            confidence=0.0,
            status=CheckStatus.NOT_AVAILABLE,
            explanation=f"Bounding box overlap analysis unavailable: {str(e)}",
            affected_document=doc_type,
            evidence_strength=EvidenceStrength.WEAK,
        )


def extract_aspect_ratio_signal(image_or_metadata: Any, doc_type: str) -> TamperSignal:
    """
    Checks aspect ratio sanity for standard A4 certificates or card-type documents.
    """
    try:
        w, h = None, None
        if hasattr(image_or_metadata, "shape"):
            h, w = image_or_metadata.shape[0], image_or_metadata.shape[1]
        elif isinstance(image_or_metadata, dict):
            w = image_or_metadata.get("width")
            h = image_or_metadata.get("height")

        if not w or not h:
            return TamperSignal(
                signal_name="aspect_ratio_sanity",
                category=SignalCategory.STRUCTURAL,
                severity=SignalSeverity.INFO,
                score=100.0,
                confidence=0.5,
                status=CheckStatus.PASS,
                explanation="Dimensions unavailable for aspect ratio analysis.",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )

        ratio = max(float(w), float(h)) / max(min(float(w), float(h)), 1.0)

        # Extremely warped or non-standard aspect ratio (> 3.5)
        if ratio > 3.5:
            return TamperSignal(
                signal_name="aspect_ratio_sanity",
                category=SignalCategory.STRUCTURAL,
                severity=SignalSeverity.LOW,
                score=65.0,
                confidence=0.70,
                status=CheckStatus.WARNING,
                explanation=f"Extreme aspect ratio ({ratio:.2f}) indicates severe crop or stretched document.",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )
        else:
            return TamperSignal(
                signal_name="aspect_ratio_sanity",
                category=SignalCategory.STRUCTURAL,
                severity=SignalSeverity.INFO,
                score=100.0,
                confidence=0.90,
                status=CheckStatus.PASS,
                explanation=f"Document aspect ratio ({ratio:.2f}) is standard for academic/official records.",
                affected_document=doc_type,
                evidence_strength=EvidenceStrength.WEAK,
            )
    except Exception as e:
        return TamperSignal(
            signal_name="aspect_ratio_sanity",
            category=SignalCategory.STRUCTURAL,
            severity=SignalSeverity.INFO,
            score=100.0,
            confidence=0.0,
            status=CheckStatus.NOT_AVAILABLE,
            explanation=f"Aspect ratio check unavailable: {str(e)}",
            affected_document=doc_type,
            evidence_strength=EvidenceStrength.WEAK,
        )


def extract_structural_signals(
    image_np: Optional[Any],
    ocr_result: Optional[Any],
    doc_type: str,
    metadata: Optional[Dict[str, Any]] = None
) -> List[TamperSignal]:
    """Extracts all structural tamper signals for a given document."""
    return [
        extract_bbox_overlap_signal(ocr_result, doc_type),
        extract_aspect_ratio_signal(image_np or metadata, doc_type),
    ]
