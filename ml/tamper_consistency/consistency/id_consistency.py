"""
VeriCampus AI — Stage 4: Cross-Document ID Consistency Checker
Compares Government ID numbers cited across documents with mandatory PII masking.
NEVER exposes raw Aadhaar / PAN numbers in values_compared, reasons, or logs.
"""
from typing import Dict, Any, List, Optional
from itertools import combinations

from ml.field_extraction.normalizers import normalize_id_number, mask_sensitive_id
from ..schemas import ConsistencyCheckResult, CheckStatus
from ..base import BaseConsistencyChecker


class IDConsistencyChecker(BaseConsistencyChecker):
    """Evaluates cross-document identification number consistency with mandatory masking."""

    ID_FIELD_KEYS = {
        "GOVERNMENT_ID": ["id_number", "aadhaar_number", "pan_number", "voter_id", "driving_license"],
        "DOMICILE_CERTIFICATE": ["aadhaar_number", "government_id_number", "gov_id_number", "id_number"],
        "INCOME_CERTIFICATE": ["aadhaar_number", "pan_number", "government_id_number", "id_number"],
        "MARKSHEET": ["aadhaar_number", "government_id_number", "id_number"],
    }

    def check(
        self,
        extractions: Dict[str, Any],
        **kwargs: Any
    ) -> List[ConsistencyCheckResult]:
        results: List[ConsistencyCheckResult] = []

        # 1. Collect extracted IDs per document
        extracted_ids: Dict[str, Dict[str, Any]] = {}
        for doc_type, doc_res in extractions.items():
            dt_upper = doc_type.upper()
            fields = getattr(doc_res, "fields", {}) if hasattr(doc_res, "fields") else (doc_res.get("fields", {}) if isinstance(doc_res, dict) else {})

            cand_id_raw = None
            cand_id_norm = None
            conf = 0.0

            for k in self.ID_FIELD_KEYS.get(dt_upper, ["id_number"]):
                f_obj = fields.get(k)
                if f_obj:
                    raw = getattr(f_obj, "raw_value", None) if hasattr(f_obj, "raw_value") else (f_obj.get("raw_value") if isinstance(f_obj, dict) else None)
                    norm = getattr(f_obj, "normalized_value", None) if hasattr(f_obj, "normalized_value") else (f_obj.get("normalized_value") if isinstance(f_obj, dict) else None)
                    c = getattr(f_obj, "confidence", 0.0) if hasattr(f_obj, "confidence") else (f_obj.get("confidence", 0.0) if isinstance(f_obj, dict) else 0.0)

                    if norm:
                        cand_id_raw = raw or norm
                        cand_id_norm = str(norm)
                        conf = c
                        break
                    elif raw:
                        cand_id_raw = raw
                        conf = c

            if cand_id_raw and not cand_id_norm:
                _, norm_out = normalize_id_number(str(cand_id_raw))
                if norm_out:
                    cand_id_norm = norm_out

            if cand_id_norm:
                extracted_ids[dt_upper] = {
                    "raw_masked": mask_sensitive_id(str(cand_id_raw or cand_id_norm)),
                    "norm": cand_id_norm,
                    "confidence": conf,
                }

        # Check if we have government ID and another document citing ID
        gov_id_entry = extracted_ids.get("GOVERNMENT_ID")
        other_ids = {dt: info for dt, info in extracted_ids.items() if dt != "GOVERNMENT_ID"}

        if not gov_id_entry or not other_ids:
            return [
                ConsistencyCheckResult(
                    check_name="cross_document_id_consistency",
                    category="CROSS_DOCUMENT_IDENTITY",
                    status=CheckStatus.NOT_AVAILABLE,
                    confidence=gov_id_entry["confidence"] if gov_id_entry else 0.0,
                    documents_compared=list(extracted_ids.keys()),
                    field_name="id_number",
                    values_compared={dt: info["raw_masked"] for dt, info in extracted_ids.items()},
                    normalized_values={dt: mask_sensitive_id(info["norm"]) for dt, info in extracted_ids.items()},
                    match_type=None,
                    reason=(
                        f"Government ID present (masked: {gov_id_entry['raw_masked']}); no secondary document references an ID number for cross-comparison."
                        if gov_id_entry
                        else "No Government ID number extracted across uploaded documents."
                    ),
                    is_critical=False,
                )
            ]

        # Compare Government ID against each secondary document citing an ID
        for dt, info in other_ids.items():
            norm_gov = gov_id_entry["norm"]
            norm_other = info["norm"]

            # Check for exact match or suffix match (e.g. last 4 digits)
            if norm_gov == norm_other:
                status = CheckStatus.PASS
                match_type = "EXACT_ID_MATCH"
                reason = f"Identity number on GOVERNMENT_ID and {dt} match identically ({gov_id_entry['raw_masked']})."
                is_critical = False
            elif len(norm_gov) >= 4 and len(norm_other) >= 4 and norm_gov[-4:] == norm_other[-4:]:
                status = CheckStatus.PASS
                match_type = "PARTIAL_ID_MATCH"
                reason = f"Identity numbers on GOVERNMENT_ID and {dt} share identical trailing digits ({gov_id_entry['raw_masked']})."
                is_critical = False
            else:
                status = CheckStatus.NEEDS_REVIEW
                match_type = "ID_MISMATCH"
                reason = f"Identity number mismatch between GOVERNMENT_ID ({gov_id_entry['raw_masked']}) and {dt} ({info['raw_masked']}). Manual review required."
                is_critical = True

            results.append(
                ConsistencyCheckResult(
                    check_name=f"id_consistency_government_id_{dt.lower()}",
                    category="CROSS_DOCUMENT_IDENTITY",
                    status=status,
                    confidence=round((gov_id_entry["confidence"] + info["confidence"]) / 2.0, 2),
                    documents_compared=["GOVERNMENT_ID", dt],
                    field_name="id_number",
                    values_compared={"GOVERNMENT_ID": gov_id_entry["raw_masked"], dt: info["raw_masked"]},
                    normalized_values={"GOVERNMENT_ID": mask_sensitive_id(norm_gov), dt: mask_sensitive_id(norm_other)},
                    match_type=match_type,
                    reason=reason,
                    is_critical=is_critical,
                )
            )

        return results
