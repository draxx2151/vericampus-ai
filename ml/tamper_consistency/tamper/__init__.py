"""
VeriCampus AI — Stage 4: Tamper Detection Package
Exports HeuristicTamperDetector and visual, structural, and metadata feature extractors.
"""
from .heuristic_detector import HeuristicTamperDetector
from .visual_features import extract_visual_signals
from .structural_features import extract_structural_signals
from .metadata_features import extract_metadata_signals

__all__ = [
    "HeuristicTamperDetector",
    "extract_visual_signals",
    "extract_structural_signals",
    "extract_metadata_signals",
]
