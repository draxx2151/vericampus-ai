"""
VeriCampus AI — Stage 6: Base Evidence Engine Interface
Abstract contract for transforming technical stage outputs into assistive evidence summaries.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from .schemas import EvidenceSummary


class BaseEvidenceEngine(ABC):
    """
    Abstract contract for decision-support evidence aggregation.
    """

    @abstractmethod
    def evaluate(
        self,
        application_id: Optional[str] = None,
        quality_results: Optional[Dict[str, Any]] = None,
        classification_results: Optional[Dict[str, Any]] = None,
        extractions: Optional[Dict[str, Any]] = None,
        tamper_results: Optional[Dict[str, Any]] = None,
        authority_results: Optional[Dict[str, Any]] = None,
        rules_evaluation: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> EvidenceSummary:
        """
        Synthesizes verification outputs across Stages 1-5 into an explainable EvidenceSummary.
        """
        pass
