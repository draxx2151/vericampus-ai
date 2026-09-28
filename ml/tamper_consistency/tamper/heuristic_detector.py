"""
VeriCampus AI — Stage 4: Heuristic Tamper Detector
Implements BaseTamperDetector combining Visual, Structural, and Metadata feature extractors.
Provides modular, explainable manipulation signals per document.
"""
from typing import Dict, Any, List, Optional

from ..base import BaseTamperDetector
from ..schemas import TamperSignal
from .visual_features import extract_visual_signals, load_image_as_rgb
from .structural_features import extract_structural_signals
from .metadata_features import extract_metadata_signals


class HeuristicTamperDetector(BaseTamperDetector):
    """
    Modular heuristic detector analyzing visual artifacts, structural text collisions,
    and metadata properties for document manipulation indicators.
    """

    def detect(
        self,
        doc_type: str,
        image_or_path: Optional[Any] = None,
        ocr_result: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> List[TamperSignal]:
        signals: List[TamperSignal] = []

        # 1. Visual Signals (ELA, Sharpness, Noise, Copy-Move)
        visual_sigs = extract_visual_signals(image_or_path, doc_type)
        signals.extend(visual_sigs)

        # 2. Structural Signals (BBox Overlap, Aspect Ratio)
        image_np = load_image_as_rgb(image_or_path)
        struct_sigs = extract_structural_signals(image_np, ocr_result, doc_type, metadata)
        signals.extend(struct_sigs)

        # 3. Metadata Signals (Editing Software, DPI)
        meta_sigs = extract_metadata_signals(image_or_path, doc_type, metadata)
        signals.extend(meta_sigs)

        return signals
