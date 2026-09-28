"""
VeriCampus AI — Stage 4: Marksheet Arithmetic & Percentage Consistency Checker
Validates internal mathematical and arithmetic coherence of Marksheet transcripts:
1. Sum of individual subject marks matches reported Total Marks (within +/- 2 grace/rounding tolerance).
2. Total Marks does not exceed Maximum Marks.
3. Extracted Percentage matches mathematically calculated percentage (Total / Max * 100) within tolerance.
"""
from typing import Dict, Any, List, Optional
import re

from ..schemas import ConsistencyCheckResult, CheckStatus
from ..base import BaseConsistencyChecker


class MarksConsistencyChecker(BaseConsistencyChecker):
    """Evaluates mathematical coherence and arithmetic accuracy of marksheet grades."""

    def check(
        self,
        extractions: Dict[str, Any],
        **kwargs: Any
    ) -> List[ConsistencyCheckResult]:
        results: List[ConsistencyCheckResult] = []

        marksheet_res = extractions.get("MARKSHEET")
        if not marksheet_res:
            return [
                ConsistencyCheckResult(
                    check_name="marksheet_math_consistency",
                    category="CROSS_DOCUMENT_ELIGIBILITY",
                    status=CheckStatus.NOT_AVAILABLE,
                    confidence=0.0,
                    documents_compared=[],
                    field_name="marksheet_math",
                    values_compared={},
                    normalized_values={},
                    match_type=None,
                    reason="MARKSHEET document not present in verification payload.",
                    is_critical=False,
                )
            ]

        fields = getattr(marksheet_res, "fields", {}) if hasattr(marksheet_res, "fields") else (marksheet_res.get("fields", {}) if isinstance(marksheet_res, dict) else {})

        # Extract total marks, max marks, percentage, subjects
        total_obj = fields.get("total_marks")
        total_val = None
        total_raw = None
        total_conf = 0.0
        if total_obj:
            total_val = getattr(total_obj, "normalized_value", None) if hasattr(total_obj, "normalized_value") else (total_obj.get("normalized_value") if isinstance(total_obj, dict) else None)
            total_raw = getattr(total_obj, "raw_value", None) if hasattr(total_obj, "raw_value") else (total_obj.get("raw_value") if isinstance(total_obj, dict) else None)
            total_conf = getattr(total_obj, "confidence", 0.0) if hasattr(total_obj, "confidence") else (total_obj.get("confidence", 0.0) if isinstance(total_obj, dict) else 0.0)

        # Check for max marks in total_marks raw or source_text (e.g. "450 / 600")
        max_val = None
        source_txt = getattr(total_obj, "source_text", "") if hasattr(total_obj, "source_text") else (total_obj.get("source_text", "") if isinstance(total_obj, dict) else "")
        cand_str = f"{total_raw or ''} {source_txt or ''}"
        max_m = re.search(r'/\s*(\d+(?:\.\d+)?)', cand_str)
        if max_m:
            try:
                max_val = float(max_m.group(1))
            except ValueError:
                pass

        pct_obj = fields.get("percentage")
        pct_val = None
        pct_raw = None
        pct_conf = 0.0
        if pct_obj:
            pct_val = getattr(pct_obj, "normalized_value", None) if hasattr(pct_obj, "normalized_value") else (pct_obj.get("normalized_value") if isinstance(pct_obj, dict) else None)
            pct_raw = getattr(pct_obj, "raw_value", None) if hasattr(pct_obj, "raw_value") else (pct_obj.get("raw_value") if isinstance(pct_obj, dict) else None)
            pct_conf = getattr(pct_obj, "confidence", 0.0) if hasattr(pct_obj, "confidence") else (pct_obj.get("confidence", 0.0) if isinstance(pct_obj, dict) else 0.0)

        subj_obj = fields.get("subjects")
        subj_list = []
        if subj_obj:
            subj_val = getattr(subj_obj, "normalized_value", None) if hasattr(subj_obj, "normalized_value") else (subj_obj.get("normalized_value") if isinstance(subj_obj, dict) else None)
            if isinstance(subj_val, list):
                subj_list = subj_val

        # Infer max_val from subjects if not directly parsed
        if not max_val and subj_list:
            subj_maxes = [s.get("max_marks") for s in subj_list if isinstance(s, dict) and s.get("max_marks") is not None]
            if len(subj_maxes) == len(subj_list) and len(subj_maxes) > 0:
                max_val = sum(subj_maxes)

        # 1. Subject sum arithmetic check
        if subj_list and total_val is not None:
            marks_obtained_list = [s.get("marks_obtained") for s in subj_list if isinstance(s, dict) and s.get("marks_obtained") is not None]
            if len(marks_obtained_list) == len(subj_list) and len(marks_obtained_list) >= 2:
                calc_total = sum(marks_obtained_list)
                diff = abs(calc_total - float(total_val))
                if diff <= 2.0:
                    results.append(
                        ConsistencyCheckResult(
                            check_name="marksheet_subject_sum_check",
                            category="CROSS_DOCUMENT_ELIGIBILITY",
                            status=CheckStatus.PASS,
                            confidence=total_conf,
                            documents_compared=["MARKSHEET"],
                            field_name="total_marks_vs_subject_sum",
                            values_compared={"MARKSHEET": f"Extracted Total: {total_val}, Subject Sum: {calc_total}"},
                            normalized_values={"extracted_total": float(total_val), "calculated_sum": calc_total},
                            match_type="ARITHMETIC_MATCH",
                            reason=f"Sum of individual subject marks ({calc_total}) matches reported total marks ({total_val}).",
                            is_critical=False,
                        )
                    )
                else:
                    results.append(
                        ConsistencyCheckResult(
                            check_name="marksheet_subject_sum_check",
                            category="CROSS_DOCUMENT_ELIGIBILITY",
                            status=CheckStatus.NEEDS_REVIEW,
                            confidence=total_conf,
                            documents_compared=["MARKSHEET"],
                            field_name="total_marks_vs_subject_sum",
                            values_compared={"MARKSHEET": f"Extracted Total: {total_val}, Subject Sum: {calc_total}"},
                            normalized_values={"extracted_total": float(total_val), "calculated_sum": calc_total},
                            match_type="ARITHMETIC_CONTRADICTION",
                            reason=f"Sum of subject marks ({calc_total}) contradicts reported total marks ({total_val}) by {diff:.1f} marks.",
                            is_critical=True,
                        )
                    )

        # 2. Total vs Maximum Marks Bounds check
        if total_val is not None and max_val is not None:
            t_f = float(total_val)
            m_f = float(max_val)
            if m_f > 0:
                if t_f > m_f:
                    results.append(
                        ConsistencyCheckResult(
                            check_name="marksheet_bounds_check",
                            category="CROSS_DOCUMENT_ELIGIBILITY",
                            status=CheckStatus.NEEDS_REVIEW,
                            confidence=total_conf,
                            documents_compared=["MARKSHEET"],
                            field_name="total_marks_vs_max_marks",
                            values_compared={"MARKSHEET": f"Total: {t_f} / Max: {m_f}"},
                            normalized_values={"total_marks": t_f, "max_marks": m_f},
                            match_type="INVALID_MARKS_BOUNDS",
                            reason=f"Marksheet total secured marks ({t_f}) exceeds maximum possible marks ({m_f}).",
                            is_critical=True,
                        )
                    )
                else:
                    results.append(
                        ConsistencyCheckResult(
                            check_name="marksheet_bounds_check",
                            category="CROSS_DOCUMENT_ELIGIBILITY",
                            status=CheckStatus.PASS,
                            confidence=total_conf,
                            documents_compared=["MARKSHEET"],
                            field_name="total_marks_vs_max_marks",
                            values_compared={"MARKSHEET": f"Total: {t_f} / Max: {m_f}"},
                            normalized_values={"total_marks": t_f, "max_marks": m_f},
                            match_type="VALID_MARKS_BOUNDS",
                            reason=f"Total secured marks ({t_f}) is bounded within maximum marks ({m_f}).",
                            is_critical=False,
                        )
                    )

        # 3. Percentage calculation check
        if total_val is not None and max_val is not None and pct_val is not None:
            try:
                t_f = float(total_val)
                m_f = float(max_val)
                p_f = float(pct_val)
                if m_f > 0:
                    calc_pct = round((t_f / m_f) * 100.0, 2)
                    pct_diff = abs(calc_pct - p_f)

                    if pct_diff <= 1.0:
                        results.append(
                            ConsistencyCheckResult(
                                check_name="marksheet_percentage_calculation_check",
                                category="CROSS_DOCUMENT_ELIGIBILITY",
                                status=CheckStatus.PASS,
                                confidence=pct_conf,
                                documents_compared=["MARKSHEET"],
                                field_name="percentage_calculation",
                                values_compared={"MARKSHEET": f"Reported: {p_f}%, Calculated: {calc_pct}%"},
                                normalized_values={"reported_percentage": p_f, "calculated_percentage": calc_pct},
                                match_type="PERCENTAGE_CONSISTENT",
                                reason=f"Extracted percentage ({p_f}%) matches arithmetic calculation ({t_f}/{m_f} = {calc_pct}%).",
                                is_critical=False,
                            )
                        )
                    elif pct_diff <= 2.5:
                        results.append(
                            ConsistencyCheckResult(
                                check_name="marksheet_percentage_calculation_check",
                                category="CROSS_DOCUMENT_ELIGIBILITY",
                                status=CheckStatus.WARNING,
                                confidence=pct_conf,
                                documents_compared=["MARKSHEET"],
                                field_name="percentage_calculation",
                                values_compared={"MARKSHEET": f"Reported: {p_f}%, Calculated: {calc_pct}%"},
                                normalized_values={"reported_percentage": p_f, "calculated_percentage": calc_pct},
                                match_type="PERCENTAGE_MINOR_DISCREPANCY",
                                reason=f"Minor divergence between reported percentage ({p_f}%) and calculated percentage ({calc_pct}%).",
                                is_critical=False,
                            )
                        )
                    else:
                        results.append(
                            ConsistencyCheckResult(
                                check_name="marksheet_percentage_calculation_check",
                                category="CROSS_DOCUMENT_ELIGIBILITY",
                                status=CheckStatus.NEEDS_REVIEW,
                                confidence=pct_conf,
                                documents_compared=["MARKSHEET"],
                                field_name="percentage_calculation",
                                values_compared={"MARKSHEET": f"Reported: {p_f}%, Calculated: {calc_pct}%"},
                                normalized_values={"reported_percentage": p_f, "calculated_percentage": calc_pct},
                                match_type="PERCENTAGE_CONTRADICTION",
                                reason=f"Reported percentage ({p_f}%) contradicts calculated percentage ({calc_pct}%) by {pct_diff:.2f}%.",
                                is_critical=True,
                            )
                        )
            except Exception:
                pass

        if not results:
            results.append(
                ConsistencyCheckResult(
                    check_name="marksheet_math_consistency",
                    category="CROSS_DOCUMENT_ELIGIBILITY",
                    status=CheckStatus.NOT_AVAILABLE,
                    confidence=0.0,
                    documents_compared=["MARKSHEET"],
                    field_name="marksheet_math",
                    values_compared={},
                    normalized_values={},
                    match_type=None,
                    reason="Insufficient numeric mark totals or subjects extracted to perform arithmetic verification.",
                    is_critical=False,
                )
            )

        return results
