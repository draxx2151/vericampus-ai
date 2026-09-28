"""
VeriCampus AI — Stage 3 Base Field Extractor Interface
ML-ready abstraction allowing Rule-Based, Learned (NER/LayoutLM), or Hybrid providers
to be plugged in seamlessly without changing the API contract.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
from .schemas import DocumentFieldExtractionResult, FieldExtractionResult, ExtractionStatus


class BaseFieldExtractor(ABC):
    """
    Abstract contract for document field extractors.
    Consumes OCR lines, bounding boxes, and metadata to extract typed fields.
    """

    @abstractmethod
    def extract(
        self,
        ocr_result: Any,
        expected_type: Optional[str] = None,
        **kwargs: Any
    ) -> DocumentFieldExtractionResult:
        """
        Extract structured, normalized fields from OCR text lines and bounding boxes.
        """
        pass

    @staticmethod
    def find_nearest_value_on_right(
        label_bbox: Dict[str, float],
        lines: List[Any],
        y_tolerance: float = 20.0,
        max_x_distance: float = 400.0,
    ) -> Optional[Any]:
        """
        Layout-aware geometry utility: locates the closest OCR line situated to the right
        of a detected field label bounding box on approximately the same horizontal row.
        """
        best_candidate = None
        min_dist = float('inf')

        l_x_max = label_bbox.get("x_max", 0.0)
        l_y_mid = (label_bbox.get("y_min", 0.0) + label_bbox.get("y_max", 0.0)) / 2.0

        for line in lines:
            bbox = getattr(line, "bounding_box", None)
            if bbox is None:
                continue

            c_x_min = getattr(bbox, "x_min", 0.0) if hasattr(bbox, "x_min") else bbox.get("x_min", 0.0)
            c_y_min = getattr(bbox, "y_min", 0.0) if hasattr(bbox, "y_min") else bbox.get("y_min", 0.0)
            c_y_max = getattr(bbox, "y_max", 0.0) if hasattr(bbox, "y_max") else bbox.get("y_max", 0.0)
            c_y_mid = (c_y_min + c_y_max) / 2.0

            # Candidate must be to the right
            if c_x_min > l_x_max and (c_x_min - l_x_max) <= max_x_distance:
                # Vertical alignment check
                if abs(c_y_mid - l_y_mid) <= y_tolerance:
                    dist = c_x_min - l_x_max
                    if dist < min_dist:
                        min_dist = dist
                        best_candidate = line

        return best_candidate

    @staticmethod
    def find_nearest_value_below(
        label_bbox: Dict[str, float],
        lines: List[Any],
        x_tolerance: float = 60.0,
        max_y_distance: float = 80.0,
    ) -> Optional[Any]:
        """
        Layout-aware geometry utility: locates the closest OCR line situated directly below
        a detected field label bounding box.
        """
        best_candidate = None
        min_dist = float('inf')

        l_x_min = label_bbox.get("x_min", 0.0)
        l_y_max = label_bbox.get("y_max", 0.0)

        for line in lines:
            bbox = getattr(line, "bounding_box", None)
            if bbox is None:
                continue

            c_x_min = getattr(bbox, "x_min", 0.0) if hasattr(bbox, "x_min") else bbox.get("x_min", 0.0)
            c_y_min = getattr(bbox, "y_min", 0.0) if hasattr(bbox, "y_min") else bbox.get("y_min", 0.0)

            # Candidate must be below
            if c_y_min >= l_y_max and (c_y_min - l_y_max) <= max_y_distance:
                if abs(c_x_min - l_x_min) <= x_tolerance:
                    dist = c_y_min - l_y_max
                    if dist < min_dist:
                        min_dist = dist
                        best_candidate = line

        return best_candidate
