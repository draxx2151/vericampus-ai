"""
VeriCampus AI — Stage 4: Base Abstract Contracts
Provides ML-ready provider abstractions for Tamper Detection and Cross-Document Consistency.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path

from .schemas import TamperSignal, ConsistencyCheckResult


class BaseTamperDetector(ABC):
    """
    Abstract base interface for document tamper and manipulation detection.
    Enables future drop-in replacement by machine learning classifiers (e.g. CNNs or GBDTs)
    without touching the orchestration pipeline.
    """

    @abstractmethod
    def detect(
        self,
        doc_type: str,
        image_or_path: Optional[Any] = None,
        ocr_result: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> List[TamperSignal]:
        """
        Analyzes an image, OCR result, and metadata for manipulation indicators.
        Returns a list of TamperSignal findings.
        """
        pass


class BaseConsistencyChecker(ABC):
    """
    Abstract base interface for cross-document consistency verification.
    """

    @abstractmethod
    def check(
        self,
        extractions: Dict[str, Any],
        **kwargs: Any
    ) -> List[ConsistencyCheckResult]:
        """
        Compares structured extractions across documents.
        Returns a list of ConsistencyCheckResult findings.
        """
        pass
