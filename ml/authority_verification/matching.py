"""
VeriCampus AI — Stage 5: Field Matching Engine
Document-specific field comparison logic with non-destructive normalization,
strict Government ID last-4 safety, and missing-field tolerance.
"""
import re
from typing import Dict, Any, Optional, Tuple, List

from ml.field_extraction.normalizers import (
    normalize_name,
    normalize_date,
    normalize_currency,
    normalize_percentage,
    mask_sensitive_id,
    normalize_whitespace,
)
from .schemas import (
    FieldMatchStatus,
    FieldComparisonResult,
    EvidenceStrength,
    AuthorityStatus,
)
from .config import (
    NAME_SIMILARITY_THRESHOLD,
    MARKS_SUM_TOLERANCE,
    PERCENTAGE_TOLERANCE,
    INCOME_TOLERANCE_INR,
)


def compute_string_similarity(s1: str, s2: str) -> float:
    """Computes basic normalized token overlap & character similarity."""
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    # Token overlap (Jaccard)
    tokens1 = set(s1.split())
    tokens2 = set(s2.split())
    if tokens1 and tokens2:
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        token_sim = intersection / union if union > 0 else 0.0
    else:
        token_sim = 0.0

    # Character bigram similarity
    def get_bigrams(s: str) -> set:
        return {s[i:i+2] for i in range(len(s) - 1)} if len(s) > 1 else {s}

    b1, b2 = get_bigrams(s1), get_bigrams(s2)
    bigram_sim = (2.0 * len(b1.intersection(b2))) / (len(b1) + len(b2)) if (len(b1) + len(b2)) > 0 else 0.0

    return round(max(token_sim, bigram_sim), 3)


def compare_names(extracted_name: Optional[str], authority_name: Optional[str]) -> FieldComparisonResult:
    """
    Compares applicant names using Stage 3 non-destructive normalizer.
    """
    if not authority_name:
        return FieldComparisonResult(
            field_name="name",
            extracted_value=extracted_name,
            authority_value=None,
            status=FieldMatchStatus.NOT_AVAILABLE,
            reason="Name not provided by authority record.",
        )
    if not extracted_name:
        return FieldComparisonResult(
            field_name="name",
            extracted_value=None,
            authority_value=authority_name,
            status=FieldMatchStatus.SKIPPED,
            reason="Name was not extracted from uploaded document.",
        )

    _, norm_ext = normalize_name(extracted_name)
    _, norm_auth = normalize_name(authority_name)

    if not norm_ext or not norm_auth:
        return FieldComparisonResult(
            field_name="name",
            extracted_value=extracted_name,
            authority_value=authority_name,
            status=FieldMatchStatus.NOT_AVAILABLE,
            reason="Name string could not be normalized for comparison.",
        )

    if norm_ext == norm_auth:
        return FieldComparisonResult(
            field_name="name",
            extracted_value=extracted_name,
            authority_value=authority_name,
            status=FieldMatchStatus.MATCH,
            confidence=1.0,
            reason="Exact normalized name match.",
        )

    # Token permutation check (e.g. "Patil Amit" vs "Amit Patil")
    if set(norm_ext.split()) == set(norm_auth.split()):
        return FieldComparisonResult(
            field_name="name",
            extracted_value=extracted_name,
            authority_value=authority_name,
            status=FieldMatchStatus.MATCH,
            confidence=0.95,
            reason="Normalized name token permutation match.",
        )

    sim = compute_string_similarity(norm_ext, norm_auth)
    if sim >= NAME_SIMILARITY_THRESHOLD:
        return FieldComparisonResult(
            field_name="name",
            extracted_value=extracted_name,
            authority_value=authority_name,
            status=FieldMatchStatus.MATCH,
            confidence=sim,
            reason=f"Close phonetic/token name match (similarity: {sim:.2f}).",
        )

    return FieldComparisonResult(
        field_name="name",
        extracted_value=extracted_name,
        authority_value=authority_name,
        status=FieldMatchStatus.MISMATCH,
        confidence=sim,
        reason=f"Name discrepancy between document ('{extracted_name}') and authority ('{authority_name}').",
    )


def compare_dates(field_name: str, extracted_date: Optional[str], authority_date: Optional[str]) -> FieldComparisonResult:
    """
    Compares dates standardized via Stage 3 ISO normalizer.
    """
    if not authority_date:
        return FieldComparisonResult(
            field_name=field_name,
            extracted_value=extracted_date,
            authority_value=None,
            status=FieldMatchStatus.NOT_AVAILABLE,
            reason=f"{field_name} not supplied in authority record.",
        )
    if not extracted_date:
        return FieldComparisonResult(
            field_name=field_name,
            extracted_value=None,
            authority_value=authority_date,
            status=FieldMatchStatus.SKIPPED,
            reason=f"{field_name} missing from document extractions.",
        )

    _, iso_ext = normalize_date(extracted_date)
    _, iso_auth = normalize_date(authority_date)

    if not iso_ext or not iso_auth:
        return FieldComparisonResult(
            field_name=field_name,
            extracted_value=extracted_date,
            authority_value=authority_date,
            status=FieldMatchStatus.NOT_AVAILABLE,
            reason="Date could not be parsed to standard ISO calendar date.",
        )

    if iso_ext == iso_auth:
        return FieldComparisonResult(
            field_name=field_name,
            extracted_value=iso_ext,
            authority_value=iso_auth,
            status=FieldMatchStatus.MATCH,
            confidence=1.0,
            reason="Exact date match.",
        )

    return FieldComparisonResult(
        field_name=field_name,
        extracted_value=iso_ext,
        authority_value=iso_auth,
        status=FieldMatchStatus.MISMATCH,
        confidence=0.0,
        reason=f"Date discrepancy: document has {iso_ext}, authority has {iso_auth}.",
    )


def compare_identifiers(
    field_name: str,
    extracted_id: Optional[str],
    authority_id: Optional[str],
    is_full_authorized_match_supported: bool = False,
) -> Tuple[FieldComparisonResult, EvidenceStrength]:
    """
    Compares government or certificate identifiers with strict PII masking.
    
    SAFETY MANDATE:
    - Full authorized identifier match -> STRONG evidence (when is_full_authorized_match_supported=True)
    - Last-4 match -> MODERATE evidence (if other fields match) or WEAK (if isolated)
    - Last-4 conflict -> MISMATCH
    - Last four digits ALONE must never produce STRONG authority match evidence.
    """
    if not authority_id:
        return FieldComparisonResult(
            field_name=field_name,
            extracted_value=mask_sensitive_id(extracted_id) if extracted_id else None,
            authority_value=None,
            status=FieldMatchStatus.NOT_AVAILABLE,
            reason=f"{field_name} not available in authority record.",
        ), EvidenceStrength.NONE

    if not extracted_id:
        return FieldComparisonResult(
            field_name=field_name,
            extracted_value=None,
            authority_value=mask_sensitive_id(authority_id),
            status=FieldMatchStatus.SKIPPED,
            reason=f"{field_name} not extracted from document.",
        ), EvidenceStrength.NONE

    # Clean non-alphanumeric noise
    clean_ext = re.sub(r'[^a-zA-Z0-9]', '', str(extracted_id)).upper()
    clean_auth = re.sub(r'[^a-zA-Z0-9]', '', str(authority_id)).upper()

    masked_ext = mask_sensitive_id(clean_ext)
    masked_auth = mask_sensitive_id(clean_auth)

    # Check for complete exact match if supported and length >= 8
    if clean_ext == clean_auth:
        strength = EvidenceStrength.STRONG if is_full_authorized_match_supported else EvidenceStrength.MODERATE
        return FieldComparisonResult(
            field_name=field_name,
            extracted_value=masked_ext,
            authority_value=masked_auth,
            status=FieldMatchStatus.MATCH,
            confidence=1.0,
            reason="Identifier matches authoritative record.",
        ), strength

    # Check last 4 digits
    last4_ext = clean_ext[-4:] if len(clean_ext) >= 4 else clean_ext
    last4_auth = clean_auth[-4:] if len(clean_auth) >= 4 else clean_auth

    if last4_ext == last4_auth:
        # Last-4 alone is strictly capped at MODERATE or WEAK
        return FieldComparisonResult(
            field_name=field_name,
            extracted_value=masked_ext,
            authority_value=masked_auth,
            status=FieldMatchStatus.MATCH,
            confidence=0.85,
            reason=f"Identifier trailing digits match (****{last4_ext}).",
        ), EvidenceStrength.MODERATE

    # Conflict on last-4
    return FieldComparisonResult(
        field_name=field_name,
        extracted_value=masked_ext,
        authority_value=masked_auth,
        status=FieldMatchStatus.MISMATCH,
        confidence=0.0,
        reason=f"Identifier discrepancy: document ends with {last4_ext}, authority ends with {last4_auth}.",
    ), EvidenceStrength.NONE


def match_government_id_fields(
    extracted: Dict[str, Any],
    authority: Dict[str, Any],
    is_full_authorized_match: bool = False,
) -> Tuple[Dict[str, FieldComparisonResult], EvidenceStrength, AuthorityStatus]:
    """
    Evaluates Government ID fields against authoritative record.
    """
    comparisons: Dict[str, FieldComparisonResult] = {}
    
    # 1. ID Number
    ext_id = extracted.get("id_number") or extracted.get("aadhaar_number") or extracted.get("pan_number")
    auth_id = authority.get("id_number") or authority.get("aadhaar_number") or authority.get("pan_number")
    id_res, id_strength = compare_identifiers(
        "id_number", ext_id, auth_id, is_full_authorized_match_supported=is_full_authorized_match
    )
    comparisons["id_number"] = id_res

    # 2. Name
    name_res = compare_names(extracted.get("name") or extracted.get("applicant_name"), authority.get("name"))
    comparisons["name"] = name_res

    # 3. DOB
    dob_res = compare_dates("date_of_birth", extracted.get("date_of_birth") or extracted.get("dob"), authority.get("date_of_birth") or authority.get("dob"))
    comparisons["date_of_birth"] = dob_res

    # Overall evaluation
    has_mismatch = any(c.status == FieldMatchStatus.MISMATCH for c in comparisons.values())
    if has_mismatch:
        return comparisons, EvidenceStrength.NONE, AuthorityStatus.MISMATCH

    matched_count = sum(1 for c in comparisons.values() if c.status == FieldMatchStatus.MATCH)
    if matched_count == 0:
        return comparisons, EvidenceStrength.NONE, AuthorityStatus.NOT_AVAILABLE

    # Check Government ID safety rule:
    # Last 4 alone must NEVER produce STRONG evidence.
    if id_res.status == FieldMatchStatus.MATCH and name_res.status == FieldMatchStatus.MATCH and dob_res.status == FieldMatchStatus.MATCH:
        evidence = EvidenceStrength.STRONG if is_full_authorized_match else EvidenceStrength.MODERATE
    elif id_res.status == FieldMatchStatus.MATCH and (name_res.status == FieldMatchStatus.MATCH or dob_res.status == FieldMatchStatus.MATCH):
        evidence = EvidenceStrength.MODERATE
    elif id_res.status == FieldMatchStatus.MATCH and name_res.status != FieldMatchStatus.MATCH and dob_res.status != FieldMatchStatus.MATCH:
        # Isolated last-4 match alone
        evidence = EvidenceStrength.WEAK
    else:
        evidence = EvidenceStrength.MODERATE if matched_count >= 2 else EvidenceStrength.WEAK

    return comparisons, evidence, AuthorityStatus.MATCH


def match_marksheet_fields(
    extracted: Dict[str, Any],
    authority: Dict[str, Any],
) -> Tuple[Dict[str, FieldComparisonResult], EvidenceStrength, AuthorityStatus]:
    """
    Evaluates Marksheet fields against authoritative educational record.
    """
    comparisons: Dict[str, FieldComparisonResult] = {}

    # 1. Student Name
    name_res = compare_names(extracted.get("student_name") or extracted.get("name"), authority.get("student_name") or authority.get("name"))
    comparisons["student_name"] = name_res

    # 2. Roll Number
    roll_res, _ = compare_identifiers("roll_number", extracted.get("roll_number"), authority.get("roll_number"), is_full_authorized_match_supported=True)
    comparisons["roll_number"] = roll_res

    # 3. Passing Year
    ext_yr = str(extracted.get("passing_year") or "").strip()
    auth_yr = str(authority.get("passing_year") or "").strip()
    if auth_yr and ext_yr:
        if ext_yr == auth_yr:
            comparisons["passing_year"] = FieldComparisonResult(
                field_name="passing_year", extracted_value=ext_yr, authority_value=auth_yr,
                status=FieldMatchStatus.MATCH, reason="Passing year matches authoritative record."
            )
        else:
            comparisons["passing_year"] = FieldComparisonResult(
                field_name="passing_year", extracted_value=ext_yr, authority_value=auth_yr,
                status=FieldMatchStatus.MISMATCH, reason=f"Passing year mismatch: doc={ext_yr}, auth={auth_yr}."
            )
    else:
        comparisons["passing_year"] = FieldComparisonResult(
            field_name="passing_year", extracted_value=ext_yr or None, authority_value=auth_yr or None,
            status=FieldMatchStatus.NOT_AVAILABLE, reason="Passing year not supplied in authority record."
        )

    # 4. Total Marks
    ext_tm = extracted.get("total_marks")
    auth_tm = authority.get("total_marks")
    if auth_tm is not None and ext_tm is not None:
        try:
            diff = abs(float(ext_tm) - float(auth_tm))
            if diff <= MARKS_SUM_TOLERANCE:
                comparisons["total_marks"] = FieldComparisonResult(
                    field_name="total_marks", extracted_value=str(ext_tm), authority_value=str(auth_tm),
                    status=FieldMatchStatus.MATCH, reason="Total marks verified within tolerance."
                )
            else:
                comparisons["total_marks"] = FieldComparisonResult(
                    field_name="total_marks", extracted_value=str(ext_tm), authority_value=str(auth_tm),
                    status=FieldMatchStatus.MISMATCH, reason=f"Total marks discrepancy: doc={ext_tm}, auth={auth_tm}."
                )
        except (ValueError, TypeError):
            comparisons["total_marks"] = FieldComparisonResult(
                field_name="total_marks", extracted_value=str(ext_tm), authority_value=str(auth_tm),
                status=FieldMatchStatus.NOT_AVAILABLE, reason="Could not parse marks to numeric float."
            )
    else:
        comparisons["total_marks"] = FieldComparisonResult(
            field_name="total_marks", extracted_value=str(ext_tm) if ext_tm is not None else None,
            authority_value=str(auth_tm) if auth_tm is not None else None,
            status=FieldMatchStatus.NOT_AVAILABLE, reason="Total marks not supplied in authority record."
        )

    # Overall evaluation
    has_mismatch = any(c.status == FieldMatchStatus.MISMATCH for c in comparisons.values())
    if has_mismatch:
        return comparisons, EvidenceStrength.NONE, AuthorityStatus.MISMATCH

    matched_count = sum(1 for c in comparisons.values() if c.status == FieldMatchStatus.MATCH)
    if matched_count == 0:
        return comparisons, EvidenceStrength.NONE, AuthorityStatus.NOT_AVAILABLE

    evidence = EvidenceStrength.STRONG if matched_count >= 3 else EvidenceStrength.MODERATE
    return comparisons, evidence, AuthorityStatus.MATCH


def match_income_certificate_fields(
    extracted: Dict[str, Any],
    authority: Dict[str, Any],
) -> Tuple[Dict[str, FieldComparisonResult], EvidenceStrength, AuthorityStatus]:
    """
    Evaluates Income Certificate fields against authoritative revenue record.
    """
    comparisons: Dict[str, FieldComparisonResult] = {}

    # 1. Applicant Name
    name_res = compare_names(extracted.get("applicant_name") or extracted.get("name"), authority.get("applicant_name") or authority.get("name"))
    comparisons["applicant_name"] = name_res

    # 2. Certificate Number
    cert_res, _ = compare_identifiers("certificate_number", extracted.get("certificate_number"), authority.get("certificate_number"), is_full_authorized_match_supported=True)
    comparisons["certificate_number"] = cert_res

    # 3. Annual Income
    ext_inc = extracted.get("annual_income")
    auth_inc = authority.get("annual_income")
    if auth_inc is not None and ext_inc is not None:
        try:
            _, ext_inc_val = normalize_currency(ext_inc)
            _, auth_inc_val = normalize_currency(auth_inc)
            if ext_inc_val is not None and auth_inc_val is not None:
                diff = abs(ext_inc_val - auth_inc_val)
                if diff <= INCOME_TOLERANCE_INR:
                    comparisons["annual_income"] = FieldComparisonResult(
                        field_name="annual_income", extracted_value=f"Rs. {ext_inc_val:,.2f}", authority_value=f"Rs. {auth_inc_val:,.2f}",
                        status=FieldMatchStatus.MATCH, reason="Income verified within tolerance."
                    )
                else:
                    comparisons["annual_income"] = FieldComparisonResult(
                        field_name="annual_income", extracted_value=f"Rs. {ext_inc_val:,.2f}", authority_value=f"Rs. {auth_inc_val:,.2f}",
                        status=FieldMatchStatus.MISMATCH, reason=f"Income discrepancy: doc=Rs. {ext_inc_val:,.2f}, auth=Rs. {auth_inc_val:,.2f}."
                    )
            else:
                comparisons["annual_income"] = FieldComparisonResult(
                    field_name="annual_income", extracted_value=str(ext_inc), authority_value=str(auth_inc),
                    status=FieldMatchStatus.NOT_AVAILABLE, reason="Could not parse income values to numeric currency."
                )
        except Exception:
            comparisons["annual_income"] = FieldComparisonResult(
                field_name="annual_income", extracted_value=str(ext_inc), authority_value=str(auth_inc),
                status=FieldMatchStatus.NOT_AVAILABLE, reason="Error comparing income currency values."
            )
    else:
        comparisons["annual_income"] = FieldComparisonResult(
            field_name="annual_income", extracted_value=str(ext_inc) if ext_inc is not None else None,
            authority_value=str(auth_inc) if auth_inc is not None else None,
            status=FieldMatchStatus.NOT_AVAILABLE, reason="Annual income not available in authority record."
        )

    # Overall evaluation
    has_mismatch = any(c.status == FieldMatchStatus.MISMATCH for c in comparisons.values())
    if has_mismatch:
        return comparisons, EvidenceStrength.NONE, AuthorityStatus.MISMATCH

    matched_count = sum(1 for c in comparisons.values() if c.status == FieldMatchStatus.MATCH)
    if matched_count == 0:
        return comparisons, EvidenceStrength.NONE, AuthorityStatus.NOT_AVAILABLE

    evidence = EvidenceStrength.STRONG if matched_count >= 2 else EvidenceStrength.MODERATE
    return comparisons, evidence, AuthorityStatus.MATCH


def match_domicile_certificate_fields(
    extracted: Dict[str, Any],
    authority: Dict[str, Any],
) -> Tuple[Dict[str, FieldComparisonResult], EvidenceStrength, AuthorityStatus]:
    """
    Evaluates Domicile Certificate fields against authoritative domicile record.
    """
    comparisons: Dict[str, FieldComparisonResult] = {}

    # 1. Applicant Name
    name_res = compare_names(extracted.get("applicant_name") or extracted.get("name"), authority.get("applicant_name") or authority.get("name"))
    comparisons["applicant_name"] = name_res

    # 2. Certificate Number
    cert_res, _ = compare_identifiers("certificate_number", extracted.get("certificate_number"), authority.get("certificate_number"), is_full_authorized_match_supported=True)
    comparisons["certificate_number"] = cert_res

    # 3. State
    ext_st = normalize_whitespace(str(extracted.get("state") or "")).lower()
    auth_st = normalize_whitespace(str(authority.get("state") or "")).lower()
    if auth_st and ext_st:
        if ext_st == auth_st:
            comparisons["state"] = FieldComparisonResult(
                field_name="state", extracted_value=ext_st.title(), authority_value=auth_st.title(),
                status=FieldMatchStatus.MATCH, reason="Domicile state confirmed."
            )
        else:
            comparisons["state"] = FieldComparisonResult(
                field_name="state", extracted_value=ext_st.title(), authority_value=auth_st.title(),
                status=FieldMatchStatus.MISMATCH, reason=f"State mismatch: doc={ext_st.title()}, auth={auth_st.title()}."
            )
    else:
        comparisons["state"] = FieldComparisonResult(
            field_name="state", extracted_value=ext_st.title() if ext_st else None, authority_value=auth_st.title() if auth_st else None,
            status=FieldMatchStatus.NOT_AVAILABLE, reason="State not supplied in authority record."
        )

    # Overall evaluation
    has_mismatch = any(c.status == FieldMatchStatus.MISMATCH for c in comparisons.values())
    if has_mismatch:
        return comparisons, EvidenceStrength.NONE, AuthorityStatus.MISMATCH

    matched_count = sum(1 for c in comparisons.values() if c.status == FieldMatchStatus.MATCH)
    if matched_count == 0:
        return comparisons, EvidenceStrength.NONE, AuthorityStatus.NOT_AVAILABLE

    evidence = EvidenceStrength.STRONG if matched_count >= 2 else EvidenceStrength.MODERATE
    return comparisons, evidence, AuthorityStatus.MATCH
