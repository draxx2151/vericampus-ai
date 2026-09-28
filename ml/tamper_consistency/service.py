"""
VeriCampus AI — Stage 4: Tamper Detection & Cross-Document Consistency Service
Central orchestrator integrating HeuristicTamperDetector and modular consistency checkers.
Coordinates evaluation of Stage 3 extractions, OCR layouts, and document files.
"""
from typing import Dict, Any, List, Optional

from .schemas import (
    Stage4VerificationResult,
    TamperAssessment,
    ConsistencyAssessment,
    TamperSignal,
    ConsistencyCheckResult,
    CheckStatus,
)
from .base import BaseTamperDetector, BaseConsistencyChecker
from .tamper.heuristic_detector import HeuristicTamperDetector
from .consistency.name_consistency import NameConsistencyChecker
from .consistency.dob_consistency import DOBConsistencyChecker
from .consistency.id_consistency import IDConsistencyChecker
from .consistency.date_consistency import DateConsistencyChecker
from .consistency.marks_consistency import MarksConsistencyChecker
from .scorer import (
    score_tamper_signals,
    score_consistency_checks,
    score_stage4_overall,
)
from .config import STAGE4_VERSION


class TamperConsistencyService:
    """
    Orchestration service for Stage 4 verification:
    Evaluates visual/structural tamper indicators and cross-document semantic consistency.
    """

    def __init__(
        self,
        tamper_detector: Optional[BaseTamperDetector] = None,
        consistency_checkers: Optional[List[BaseConsistencyChecker]] = None,
    ):
        self.tamper_detector = tamper_detector or HeuristicTamperDetector()
        self.consistency_checkers = consistency_checkers or [
            NameConsistencyChecker(),
            DOBConsistencyChecker(),
            IDConsistencyChecker(),
            DateConsistencyChecker(),
            MarksConsistencyChecker(),
        ]

    def evaluate(
        self,
        extractions: Dict[str, Any],
        documents: Optional[Dict[str, Any]] = None,
        ocr_results: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        quality_results: Optional[Dict[str, Any]] = None,
        classifications: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Stage4VerificationResult:
        """
        Executes Stage 4 analysis.
        Args:
            extractions: Dict of doc_type -> DocumentFieldExtractionResult (from Stage 3)
            documents: Optional Dict of doc_type -> file_path / bytes / PIL Image
            ocr_results: Optional Dict of doc_type -> OCR result object
            metadata: Optional Dict of doc_type -> metadata dict
            quality_results: Optional Dict of doc_type -> Stage 1 quality result
            classifications: Optional Dict of doc_type -> Stage 2 classification result
        """
        all_tamper_signals: List[TamperSignal] = []
        all_consistency_checks: List[ConsistencyCheckResult] = []

        # 1. Run Tamper Detection on all available documents
        docs_to_inspect = documents or {}
        # If documents not directly passed, check if file paths exist in extractions or metadata
        if not docs_to_inspect and extractions:
            for dt, ext in extractions.items():
                meta_item = (metadata or {}).get(dt, {})
                file_path = meta_item.get("file_path") or meta_item.get("path")
                if file_path:
                    docs_to_inspect[dt] = file_path

        for doc_type, doc_input in docs_to_inspect.items():
            ocr_res = (ocr_results or {}).get(doc_type)
            doc_meta = (metadata or {}).get(doc_type, {})
            signals = self.tamper_detector.detect(
                doc_type=doc_type,
                image_or_path=doc_input,
                ocr_result=ocr_res,
                metadata=doc_meta,
            )
            all_tamper_signals.extend(signals)

        # 2. Run Modular Consistency Checkers
        for checker in self.consistency_checkers:
            try:
                chk_results = checker.check(extractions, **kwargs)
                all_consistency_checks.extend(chk_results)
            except Exception as e:
                all_consistency_checks.append(
                    ConsistencyCheckResult(
                        check_name=f"{checker.__class__.__name__}_error",
                        category="SYSTEM_WARNING",
                        status=CheckStatus.WARNING,
                        confidence=0.0,
                        documents_compared=[],
                        field_name="consistency",
                        reason=f"Checker failed during execution: {str(e)}",
                        is_critical=False,
                    )
                )

        # 3. Score Tamper Assessment
        t_score, t_status, t_warnings, t_reasons = score_tamper_signals(all_tamper_signals)
        tamper_assessment = TamperAssessment(
            status=t_status,
            overall_score=t_score,
            confidence=0.88 if all_tamper_signals else 0.0,
            signals=all_tamper_signals,
            warnings=t_warnings,
            reasons=t_reasons,
            detector_version=STAGE4_VERSION,
        )

        # 4. Score Consistency Assessment
        c_score, c_status, c_warnings, c_criticals, c_explanations = score_consistency_checks(all_consistency_checks)
        consistency_assessment = ConsistencyAssessment(
            status=c_status,
            overall_score=c_score,
            checks=all_consistency_checks,
            warnings=c_warnings,
            critical_inconsistencies=c_criticals,
            explanation=c_explanations,
        )

        # 5. Composite Stage 4 Assessment
        overall_score, overall_status, review_required, reasons = score_stage4_overall(
            tamper_score=t_score,
            tamper_status=t_status,
            consistency_score=c_score,
            consistency_status=c_status,
            critical_inconsistencies=c_criticals,
            warnings=t_warnings + c_warnings,
        )

        all_warnings = t_warnings + c_warnings
        confidence = round((tamper_assessment.confidence * 0.30) + (0.90 * 0.70), 2) if all_consistency_checks else tamper_assessment.confidence

        return Stage4VerificationResult(
            stage_version=STAGE4_VERSION,
            tamper_assessment=tamper_assessment,
            consistency_assessment=consistency_assessment,
            overall_status=overall_status,
            overall_score=overall_score,
            confidence=confidence,
            reasons=reasons,
            warnings=all_warnings,
            review_required=review_required,
            model_metadata={
                "checkers_executed": [c.__class__.__name__ for c in self.consistency_checkers],
                "tamper_detector": self.tamper_detector.__class__.__name__,
                "critical_inconsistency_count": len(c_criticals),
                "total_signals_count": len(all_tamper_signals),
                "total_checks_count": len(all_consistency_checks),
            },
        )
