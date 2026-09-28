"""
VeriCampus AI — Stage 4: Cross-Document Date of Birth (DOB) Consistency Checker
Compares extracted Date of Birth across Government ID, Marksheet, and Domicile Certificate.
Verifies date equivalence in ISO YYYY-MM-DD format.
Discrepancies in DOB are strong evidence of identity mismatch and require human officer review.
"""
from typing import Dict, Any, List, Optional, Tuple
from itertools import combinations

from ml.field_extraction.normalizers import normalize_date
from ..schemas import ConsistencyCheckResult, CheckStatus
from ..base import BaseConsistencyChecker


class DOBConsistencyChecker(BaseConsistencyChecker):
    """Evaluates cross-document DOB consistency across uploaded documents."""

    DOB_FIELD_KEYS = {
        "GOVERNMENT_ID": ["date_of_birth", "dob"],
        "MARKSHEET": ["date_of_birth", "dob"],
        "DOMICILE_CERTIFICATE": ["date_of_birth", "dob"],
        "INCOME_CERTIFICATE": ["date_of_birth", "dob"],
    }

    def check(
        self,
        extractions: Dict[str, Any],
        **kwargs: Any
    ) -> List[ConsistencyCheckResult]:
        results: List[ConsistencyCheckResult] = []

        # 1. Collect extracted DOBs per document
        extracted_dobs: Dict[str, Dict[str, Any]] = {}
        for doc_type, doc_res in extractions.items():
            dt_upper = doc_type.upper()
            fields = getattr(doc_res, "fields", {}) if hasattr(doc_res, "fields") else (doc_res.get("fields", {}) if isinstance(doc_res, dict) else {})

            cand_dob_raw = None
            cand_dob_norm = None
            conf = 0.0

            for k in self.DOB_FIELD_KEYS.get(dt_upper, ["date_of_birth", "dob"]):
                f_obj = fields.get(k)
                if f_obj:
                    raw = getattr(f_obj, "raw_value", None) if hasattr(f_obj, "raw_value") else (f_obj.get("raw_value") if isinstance(f_obj, dict) else None)
                    norm = getattr(f_obj, "normalized_value", None) if hasattr(f_obj, "normalized_value") else (f_obj.get("normalized_value") if isinstance(f_obj, dict) else None)
                    c = getattr(f_obj, "confidence", 0.0) if hasattr(f_obj, "confidence") else (f_obj.get("confidence", 0.0) if isinstance(f_obj, dict) else 0.0)

                    if norm:
                        cand_dob_raw = raw or norm
                        cand_dob_norm = str(norm)
                        conf = c
                        break
                    elif raw:
                        cand_dob_raw = raw
                        conf = c

            # If raw present but not normalized, try normalizing
            if cand_dob_raw and not cand_dob_norm:
                _, norm_out = normalize_date(str(cand_dob_raw))
                if norm_out:
                    cand_dob_norm = norm_out

            if cand_dob_norm:
                extracted_dobs[dt_upper] = {
                    "raw": cand_dob_raw or cand_dob_norm,
                    "norm": cand_dob_norm,
                    "confidence": conf,
                }

        # If fewer than 2 documents have extracted DOBs
        if len(extracted_dobs) < 2:
            return [
                ConsistencyCheckResult(
                    check_name="cross_document_dob_consistency",
                    category="CROSS_DOCUMENT_IDENTITY",
                    status=CheckStatus.NOT_AVAILABLE,
                    confidence=0.0,
                    documents_compared=list(extracted_dobs.keys()),
                    field_name="date_of_birth",
                    values_compared={dt: d["raw"] for dt, d in extracted_dobs.items()},
                    normalized_values={dt: d["norm"] for dt, d in extracted_dobs.items()},
                    match_type=None,
                    reason=(
                        f"DOB found only on {list(extracted_dobs.keys())[0]} (minimum 2 documents required for cross-comparison)."
                        if extracted_dobs
                        else "No Date of Birth extracted across any document for cross-document comparison."
                    ),
                    is_critical=False,
                )
            ]

        # 2. Pairwise comparison across all document pairs
        doc_pairs = list(combinations(sorted(extracted_dobs.keys()), 2))
        for dt1, dt2 in doc_pairs:
            dob_info1 = extracted_dobs[dt1]
            dob_info2 = extracted_dobs[dt2]

            d1 = dob_info1["norm"]
            d2 = dob_info2["norm"]

            if d1 == d2:
                status = CheckStatus.PASS
                match_type = "EXACT_DATE_MATCH"
                reason = f"Date of Birth on {dt1} and {dt2} match identically ({d1})."
                is_critical = False
            else:
                status = CheckStatus.NEEDS_REVIEW
                match_type = "DATE_MISMATCH"
                reason = f"Date of Birth mismatch between {dt1} ({d1}) and {dt2} ({d2}). Strong indicator of discrepancy."
                is_critical = True

            results.append(
                ConsistencyCheckResult(
                    check_name=f"dob_consistency_{dt1.lower()}_{dt2.lower()}",
                    category="CROSS_DOCUMENT_IDENTITY",
                    status=status,
                    confidence=round((dob_info1["confidence"] + dob_info2["confidence"]) / 2.0, 2),
                    documents_compared=[dt1, dt2],
                    field_name="date_of_birth",
                    values_compared={dt1: dob_info1["raw"], dt2: dob_info2["raw"]},
                    normalized_values={dt1: d1, dt2: d2},
                    match_type=match_type,
                    reason=reason,
                    is_critical=is_critical,
                )
            )

        return results
