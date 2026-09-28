"""
VeriCampus AI — Stage 4: Cross-Document Name Consistency Checker
Compares applicant names across Government ID, Marksheet, Income Certificate, and Domicile Certificate.
Reuses Stage 3 normalize_name to ensure non-destructive and title-case independent normalization.
Categorizes matches into: EXACT_MATCH, NORMALIZED_MATCH, MINOR_VARIATION, POSSIBLE_MISMATCH, MISMATCH.
"""
from typing import Dict, Any, List, Optional, Tuple
from itertools import combinations
import re

from ml.field_extraction.normalizers import normalize_name, normalize_whitespace
from ..schemas import ConsistencyCheckResult, CheckStatus, NameMatchCategory
from ..base import BaseConsistencyChecker


class NameConsistencyChecker(BaseConsistencyChecker):
    """Evaluates cross-document name consistency across all uploaded documents."""

    # Document field mappings for candidate names
    NAME_FIELD_KEYS = {
        "GOVERNMENT_ID": ["full_name", "student_name"],
        "MARKSHEET": ["student_name", "candidate_name"],
        "INCOME_CERTIFICATE": ["applicant_name", "student_name"],
        "DOMICILE_CERTIFICATE": ["applicant_name", "student_name"],
    }

    def check(
        self,
        extractions: Dict[str, Any],
        **kwargs: Any
    ) -> List[ConsistencyCheckResult]:
        results: List[ConsistencyCheckResult] = []

        # 1. Collect extracted names per document
        extracted_names: Dict[str, Dict[str, Any]] = {}
        for doc_type, doc_res in extractions.items():
            dt_upper = doc_type.upper()
            fields = getattr(doc_res, "fields", {}) if hasattr(doc_res, "fields") else (doc_res.get("fields", {}) if isinstance(doc_res, dict) else {})
            
            cand_name_raw = None
            cand_name_norm = None
            conf = 0.0

            # Search priority field keys
            for k in self.NAME_FIELD_KEYS.get(dt_upper, ["student_name", "full_name", "applicant_name"]):
                f_obj = fields.get(k)
                if f_obj:
                    raw = getattr(f_obj, "raw_value", None) if hasattr(f_obj, "raw_value") else (f_obj.get("raw_value") if isinstance(f_obj, dict) else None)
                    norm = getattr(f_obj, "normalized_value", None) if hasattr(f_obj, "normalized_value") else (f_obj.get("normalized_value") if isinstance(f_obj, dict) else None)
                    c = getattr(f_obj, "confidence", 0.0) if hasattr(f_obj, "confidence") else (f_obj.get("confidence", 0.0) if isinstance(f_obj, dict) else 0.0)
                    
                    if norm:
                        cand_name_raw = raw or norm
                        cand_name_norm = norm
                        conf = c
                        break

            # If not yet normalized, run through Stage 3 normalizer
            if cand_name_raw and not cand_name_norm:
                raw_out, norm_out = normalize_name(cand_name_raw)
                cand_name_norm = norm_out

            if cand_name_norm:
                extracted_names[dt_upper] = {
                    "raw": cand_name_raw,
                    "norm": cand_name_norm,
                    "confidence": conf,
                }

        # If fewer than 2 documents have extracted names, comparison is not available
        if len(extracted_names) < 2:
            return [
                ConsistencyCheckResult(
                    check_name="cross_document_name_consistency",
                    category="CROSS_DOCUMENT_IDENTITY",
                    status=CheckStatus.NOT_AVAILABLE,
                    confidence=0.0,
                    documents_compared=list(extracted_names.keys()),
                    field_name="student_name",
                    values_compared={dt: d["raw"] for dt, d in extracted_names.items()},
                    normalized_values={dt: d["norm"] for dt, d in extracted_names.items()},
                    match_type=None,
                    reason="Insufficient extracted names across documents for cross-comparison (minimum 2 required).",
                    is_critical=False,
                )
            ]

        # 2. Pairwise comparison across all pairs
        doc_pairs = list(combinations(sorted(extracted_names.keys()), 2))
        for dt1, dt2 in doc_pairs:
            name_info1 = extracted_names[dt1]
            name_info2 = extracted_names[dt2]

            status, match_cat, reason, score = self.compare_name_pair(
                name_info1["norm"],
                name_info2["norm"],
                dt1,
                dt2
            )

            results.append(
                ConsistencyCheckResult(
                    check_name=f"name_consistency_{dt1.lower()}_{dt2.lower()}",
                    category="CROSS_DOCUMENT_IDENTITY",
                    status=status,
                    confidence=round((name_info1["confidence"] + name_info2["confidence"]) / 2.0, 2),
                    documents_compared=[dt1, dt2],
                    field_name="student_name",
                    values_compared={dt1: name_info1["raw"], dt2: name_info2["raw"]},
                    normalized_values={dt1: name_info1["norm"], dt2: name_info2["norm"]},
                    match_type=match_cat.value,
                    reason=reason,
                    is_critical=(status == CheckStatus.NEEDS_REVIEW),
                )
            )

        return results

    @classmethod
    def compare_name_pair(
        cls,
        norm1: str,
        norm2: str,
        doc1: str = "Doc 1",
        doc2: str = "Doc 2"
    ) -> Tuple[CheckStatus, NameMatchCategory, str, float]:
        """
        Compares two normalized name strings using explainable token logic.
        """
        if not norm1 or not norm2:
            return CheckStatus.NOT_AVAILABLE, NameMatchCategory.POSSIBLE_MISMATCH, "Missing name string", 0.0

        n1 = normalize_whitespace(norm1)
        n2 = normalize_whitespace(norm2)

        # 1. Exact match on normalized strings
        if n1 == n2:
            return CheckStatus.PASS, NameMatchCategory.NORMALIZED_MATCH, f"Names on {doc1} and {doc2} match identically.", 100.0

        tokens1 = n1.split()
        tokens2 = n2.split()

        # 2. Token sort match (e.g. "Patil Rahul" vs "Rahul Patil")
        if sorted(tokens1) == sorted(tokens2):
            return CheckStatus.PASS, NameMatchCategory.MINOR_VARIATION, f"Names match with reordered tokens ('{n1}' vs '{n2}').", 95.0

        set1 = set(tokens1)
        set2 = set(tokens2)
        common = set1.intersection(set2)

        # 3. Substring subset (e.g. "Rahul Patil" is subset of "Rahul Kumar Patil")
        if set1.issubset(set2) or set2.issubset(set1):
            return CheckStatus.PASS, NameMatchCategory.MINOR_VARIATION, f"One name is a direct subset or expansion of the other ('{n1}' vs '{n2}').", 90.0

        # 4. Check for initials match (e.g. "Rahul K Patil" vs "Rahul Kumar Patil")
        rem1 = [t for t in tokens1 if t not in common]
        rem2 = [t for t in tokens2 if t not in common]

        if len(common) >= 1:
            # Check if any remaining single-letter tokens match the first letter of remaining full tokens
            initials_matched = False
            if len(rem1) == 1 and len(rem2) == 1:
                t_short = rem1[0] if len(rem1[0]) == 1 else (rem2[0] if len(rem2[0]) == 1 else None)
                t_long = rem2[0] if len(rem1[0]) == 1 else (rem1[0] if len(rem2[0]) == 1 else None)
                if t_short and t_long and t_long.startswith(t_short):
                    initials_matched = True

            if initials_matched:
                return CheckStatus.PASS, NameMatchCategory.MINOR_VARIATION, f"Names match with single-letter initial abbreviation ('{n1}' vs '{n2}').", 88.0

            # If at least 2 tokens match or >50% overlap, flag minor variation / warning
            overlap_ratio = len(common) / max(len(tokens1), len(tokens2))
            if overlap_ratio >= 0.5:
                return CheckStatus.WARNING, NameMatchCategory.POSSIBLE_MISMATCH, f"Partial name overlap ({len(common)} token(s) shared: {', '.join(common)}). Review recommended.", 65.0

        # 5. Complete or significant mismatch (e.g. "Rahul Patil" vs "Ajay Sharma")
        return CheckStatus.NEEDS_REVIEW, NameMatchCategory.MISMATCH, f"Significant name discrepancy between {doc1} ('{n1}') and {doc2} ('{n2}'). Manual verification required.", 20.0
