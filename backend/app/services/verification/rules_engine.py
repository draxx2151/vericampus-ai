import re
from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

from app.db.models.enums import DocumentType
from app.services.verification.base import (
    DocumentExtractionResult,
    ReadabilityScore,
    GovernmentIdExtraction,
    MarksheetExtraction,
    IncomeCertificateExtraction,
    DomicileCertificateExtraction,
)


class CheckStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class FieldCheckResult(BaseModel):
    check_name: str
    status: CheckStatus
    score: float = Field(..., ge=0.0, le=100.0)
    details: str
    is_critical: bool = False
    flag_code: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class CrossDocumentMatch(BaseModel):
    check_name: str
    source_document: str
    target_document: str
    status: CheckStatus
    score: float = Field(..., ge=0.0, le=100.0)
    details: str
    flag_code: Optional[str] = None


class VerificationEvaluation(BaseModel):
    overall_status: CheckStatus
    overall_score: float = Field(..., ge=0.0, le=100.0)
    field_checks: Dict[str, FieldCheckResult] = Field(default_factory=dict)
    cross_document_matches: List[CrossDocumentMatch] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    critical_flags: List[str] = Field(default_factory=list)
    recommended_status: str = "NEEDS_REVIEW"


# Authoritative MahaDBT Scheme Eligibility Configuration
DEFAULT_SCHOLARSHIP_RULES: Dict[str, Dict[str, Any]] = {
    "Rajarshi Chhatrapati Shahu Maharaj Shikshan Shulkh Shishyavrutti Yojna (EBC)": {
        "minimum_percentage": 50.0,
        "income_limit": 800000.0,
        "requires_maharashtra_domicile": True
    },
    "Dr. Panjabrao Deshmukh Vasatigruh Nirvah Bhatta Yojna (DTE)": {
        "minimum_percentage": 50.0,
        "income_limit": 800000.0,
        "requires_maharashtra_domicile": True
    },
    "Post Matric Scholarship to OBC Students": {
        "minimum_percentage": None,
        "income_limit": 150000.0,
        "requires_maharashtra_domicile": True
    },
    "Post Matric Scholarship to VJNT Students": {
        "minimum_percentage": None,
        "income_limit": 150000.0,
        "requires_maharashtra_domicile": True
    },
    "Post Matric Scholarship to SBC Students": {
        "minimum_percentage": None,
        "income_limit": 150000.0,
        "requires_maharashtra_domicile": True
    },
    "Post Matric Scholarship to the Girls Belonging to Other Backward Classes taking admission in Professional Courses": {
        "minimum_percentage": None,
        "income_limit": 800000.0,
        "requires_maharashtra_domicile": True
    },
    "State Minority Scholarship Part II (DHE)": {
        "minimum_percentage": 50.0,
        "income_limit": 800000.0,
        "requires_maharashtra_domicile": True
    },
    "Scholarship for students of minority communities pursuing Higher and Professional courses (DTE)": {
        "minimum_percentage": 50.0,
        "income_limit": 800000.0,
        "requires_maharashtra_domicile": True
    }
}


class NameMatcher:
    """
    Deterministic name normalization and comparison engine for Indian applicant names.
    Handles case folding, punctuation, whitespace, word reordering, and single-letter initials.
    """

    @staticmethod
    def normalize_name(name: Optional[str]) -> str:
        if not name:
            return ""
        cleaned = name.strip().lower()
        cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
        return " ".join(cleaned.split())

    @classmethod
    def compare_names(cls, name1: Optional[str], name2: Optional[str]) -> tuple[CheckStatus, float, str, Optional[str]]:
        norm1 = cls.normalize_name(name1)
        norm2 = cls.normalize_name(name2)

        if not norm1 or not norm2:
            return CheckStatus.NOT_AVAILABLE, 0.0, "Name field not available for comparison", None

        # 1. Exact normalized match
        if norm1 == norm2:
            return CheckStatus.PASS, 100.0, f"Exact match for '{name1}'", None

        tokens1 = norm1.split()
        tokens2 = norm2.split()

        # 2. Token sort match (Word reordering, e.g. "Patil Amit Kumar" vs "Amit Kumar Patil")
        if sorted(tokens1) == sorted(tokens2):
            return CheckStatus.PASS, 95.0, f"Match with token reordering: '{name1}' vs '{name2}'", None

        # 3. Analyze partial token matches & initials
        set1 = set(tokens1)
        set2 = set(tokens2)
        common = set1.intersection(set2)

        remaining1 = [t for t in tokens1 if t not in common]
        remaining2 = [t for t in tokens2 if t not in common]

        initial_matches = 0
        for r1 in list(remaining1):
            for r2 in list(remaining2):
                if (len(r1) == 1 and r2.startswith(r1)) or (len(r2) == 1 and r1.startswith(r2)):
                    initial_matches += 1
                    remaining1.remove(r1)
                    remaining2.remove(r2)
                    break

        total_tokens = max(len(tokens1), len(tokens2))
        matched_tokens_count = len(common) + initial_matches

        # Case: All tokens matched with safe initial (e.g. "Amit K. Patil" vs "Amit Kumar Patil")
        if matched_tokens_count == total_tokens and initial_matches > 0:
            return CheckStatus.WARNING, 85.0, f"Minor initial variation detected: '{name1}' vs '{name2}'", "NAME_VARIATION"

        # Case: Subset name variation (e.g. "Amit Patil" vs "Amit Kumar Patil")
        if len(common) >= 2 and (len(remaining1) == 0 or len(remaining2) == 0):
            return CheckStatus.WARNING, 80.0, f"Partial name variation (middle name missing/extra): '{name1}' vs '{name2}'", "NAME_VARIATION"

        # Similarity calculation based on token overlap
        similarity = (matched_tokens_count / total_tokens) * 100.0 if total_tokens > 0 else 0.0

        if similarity >= 66.0:
            return CheckStatus.WARNING, round(similarity, 1), f"Moderate name variation detected: '{name1}' vs '{name2}'", "NAME_VARIATION"

        return CheckStatus.FAIL, round(similarity, 1), f"Significant name mismatch: '{name1}' vs '{name2}'", "NAME_MISMATCH"


class RulesEngine:
    """
    Deterministic cross-verification and scholarship eligibility rules evaluation engine.
    Compares student profile and scheme requirements against structured document extraction outputs.
    """

    def __init__(self, scholarship_rules: Optional[Dict[str, Dict[str, Any]]] = None):
        self.scholarship_rules = scholarship_rules if scholarship_rules is not None else DEFAULT_SCHOLARSHIP_RULES

    @staticmethod
    def mask_id(id_val: Optional[str]) -> str:
        """Mask identification numbers for privacy in logs and user-facing reports."""
        if not id_val:
            return "N/A"
        cleaned = re.sub(r'[\s\-_/]', '', str(id_val))
        if len(cleaned) <= 4:
            return "****"
        return f"{'*' * (len(cleaned) - 4)}{cleaned[-4:]}"

    @staticmethod
    def normalize_date(d: Union[date, str, None]) -> Optional[str]:
        """Normalize date strings to ISO YYYY-MM-DD for deterministic comparison."""
        if not d:
            return None
        if isinstance(d, date):
            return d.isoformat()
        clean = d.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(clean, fmt).date().isoformat()
            except ValueError:
                pass
        return clean

    def evaluate(
        self,
        student_data: Union[Dict[str, Any], Any],
        application_data: Union[Dict[str, Any], Any],
        extractions: Dict[Union[DocumentType, str], DocumentExtractionResult]
    ) -> VerificationEvaluation:
        # Normalize input dictionaries/objects
        student_dict = student_data if isinstance(student_data, dict) else {
            "full_name": getattr(student_data, "full_name", None),
            "date_of_birth": getattr(student_data, "date_of_birth", None),
            "government_id_number": getattr(student_data, "government_id_number", None),
        }
        app_dict = application_data if isinstance(application_data, dict) else {
            "scholarship_name": getattr(application_data, "scholarship_name", None),
        }

        # Normalize extractions mapping to DocumentType keys
        norm_extractions: Dict[DocumentType, DocumentExtractionResult] = {}
        for k, v in extractions.items():
            if isinstance(k, DocumentType):
                norm_extractions[k] = v
            else:
                try:
                    norm_extractions[DocumentType(k)] = v
                except ValueError:
                    pass

        field_checks: Dict[str, FieldCheckResult] = {}
        cross_document_matches: List[CrossDocumentMatch] = []
        issues: List[str] = []
        critical_flags: List[str] = []

        gov_id_res = norm_extractions.get(DocumentType.GOVERNMENT_ID)
        marksheet_res = norm_extractions.get(DocumentType.MARKSHEET)
        income_res = norm_extractions.get(DocumentType.INCOME_CERTIFICATE)
        domicile_res = norm_extractions.get(DocumentType.DOMICILE_CERTIFICATE)

        # -------------------------------------------------------------
        # 1. READABILITY & EXTRACTION QUALITY CHECK
        # -------------------------------------------------------------
        quality_score = 0.0
        for dt, res in [
            (DocumentType.GOVERNMENT_ID, gov_id_res),
            (DocumentType.MARKSHEET, marksheet_res),
            (DocumentType.INCOME_CERTIFICATE, income_res),
            (DocumentType.DOMICILE_CERTIFICATE, domicile_res),
        ]:
            if not res or not res.extraction_success:
                issues.append(f"Required document {dt.value} is missing, unreadable, or failed extraction.")
                critical_flags.append(f"MISSING_OR_UNREADABLE_{dt.value}")
                continue

            if res.readability == ReadabilityScore.UNREADABLE:
                issues.append(f"Document {dt.value} is heavily degraded or unreadable.")
                critical_flags.append(f"UNREADABLE_{dt.value}")
            elif res.readability == ReadabilityScore.LOW:
                issues.append(f"Document {dt.value} has low readability score.")
                quality_score += 5.0
            elif res.readability == ReadabilityScore.MEDIUM:
                issues.append(f"Document {dt.value} has medium readability tier.")
                quality_score += 15.0
            elif res.readability == ReadabilityScore.HIGH:
                quality_score += 25.0

            for w in res.warnings:
                issues.append(f"[{dt.value}] {w}")

        field_checks["document_readability"] = FieldCheckResult(
            check_name="Document Readability & Extraction Quality",
            status=CheckStatus.FAIL if any("UNREADABLE" in f for f in critical_flags) else (
                CheckStatus.WARNING if quality_score < 80.0 else CheckStatus.PASS
            ),
            score=round(quality_score, 1),
            details=f"Document quality aggregate score: {quality_score:.1f}%",
            is_critical=any("UNREADABLE" in f for f in critical_flags)
        )

        # -------------------------------------------------------------
        # 2. STUDENT IDENTITY VS GOVERNMENT ID CHECKS
        # -------------------------------------------------------------
        gov_fields: Optional[GovernmentIdExtraction] = (
            gov_id_res.extracted_fields if gov_id_res and isinstance(gov_id_res.extracted_fields, GovernmentIdExtraction)
            else None
        )

        # 2A. Name check (Student Profile vs Government ID)
        student_name = student_dict.get("full_name")
        gov_name = gov_fields.full_name if gov_fields else None
        name_status, name_score, name_details, name_flag = NameMatcher.compare_names(student_name, gov_name)

        if name_flag:
            critical_flags.append(name_flag)
            issues.append(name_details)

        field_checks["identity_name"] = FieldCheckResult(
            check_name="Student Profile vs Government ID Name",
            status=name_status,
            score=name_score,
            details=name_details,
            is_critical=(name_status == CheckStatus.FAIL),
            flag_code=name_flag
        )

        # 2B. Date of Birth check
        student_dob = self.normalize_date(student_dict.get("date_of_birth"))
        gov_dob = self.normalize_date(gov_fields.date_of_birth) if gov_fields else None

        if not student_dob or not gov_dob:
            dob_status = CheckStatus.NOT_AVAILABLE
            dob_score = 0.0
            dob_details = "Date of birth unavailable for comparison"
            dob_flag = None
        elif student_dob == gov_dob:
            dob_status = CheckStatus.PASS
            dob_score = 100.0
            dob_details = f"Date of birth verified ({student_dob})"
            dob_flag = None
        else:
            dob_status = CheckStatus.FAIL
            dob_score = 0.0
            dob_details = f"Date of birth mismatch: profile '{student_dob}' vs extracted '{gov_dob}'"
            dob_flag = "DOB_MISMATCH"
            critical_flags.append(dob_flag)
            issues.append(dob_details)

        field_checks["date_of_birth"] = FieldCheckResult(
            check_name="Date of Birth Verification",
            status=dob_status,
            score=dob_score,
            details=dob_details,
            is_critical=(dob_status == CheckStatus.FAIL),
            flag_code=dob_flag
        )

        # 2C. Government ID Number check
        student_id_num = student_dict.get("government_id_number")
        gov_id_num = gov_fields.id_number if gov_fields else None

        clean_stu_id = re.sub(r'[\s\-_/]', '', student_id_num).upper() if student_id_num else None
        clean_gov_id = re.sub(r'[\s\-_/]', '', gov_id_num).upper() if gov_id_num else None

        if not clean_stu_id or not clean_gov_id:
            id_status = CheckStatus.NOT_AVAILABLE
            id_score = 0.0
            id_details = "Government ID number unavailable for comparison"
            id_flag = None
        elif clean_stu_id == clean_gov_id:
            id_status = CheckStatus.PASS
            id_score = 100.0
            id_details = f"Government ID verified (Number: {self.mask_id(student_id_num)})"
            id_flag = None
        else:
            id_status = CheckStatus.FAIL
            id_score = 0.0
            id_details = f"Government ID number mismatch: profile '{self.mask_id(student_id_num)}' vs extracted '{self.mask_id(gov_id_num)}'"
            id_flag = "GOVERNMENT_ID_MISMATCH"
            critical_flags.append(id_flag)
            issues.append(id_details)

        field_checks["government_id_number"] = FieldCheckResult(
            check_name="Government ID Number Verification",
            status=id_status,
            score=id_score,
            details=id_details,
            is_critical=(id_status == CheckStatus.FAIL),
            flag_code=id_flag
        )

        # -------------------------------------------------------------
        # 3. CROSS-DOCUMENT NAME CONSISTENCY
        # -------------------------------------------------------------
        marksheet_fields = marksheet_res.extracted_fields if marksheet_res and isinstance(marksheet_res.extracted_fields, MarksheetExtraction) else None
        income_fields = income_res.extracted_fields if income_res and isinstance(income_res.extracted_fields, IncomeCertificateExtraction) else None
        domicile_fields = domicile_res.extracted_fields if domicile_res and isinstance(domicile_res.extracted_fields, DomicileCertificateExtraction) else None

        doc_names = [
            ("STUDENT_PROFILE", student_name),
            ("GOVERNMENT_ID", gov_name),
            ("MARKSHEET", marksheet_fields.candidate_name if marksheet_fields else None),
            ("INCOME_CERTIFICATE", income_fields.applicant_name if income_fields else None),
            ("DOMICILE_CERTIFICATE", domicile_fields.candidate_name if domicile_fields else None),
        ]

        cross_scores: List[float] = []
        for i in range(len(doc_names)):
            for j in range(i + 1, len(doc_names)):
                src_label, src_n = doc_names[i]
                tgt_label, tgt_n = doc_names[j]
                m_stat, m_sc, m_det, m_fl = NameMatcher.compare_names(src_n, tgt_n)

                if m_stat != CheckStatus.NOT_AVAILABLE:
                    cross_scores.append(m_sc)
                    if m_fl and m_fl not in critical_flags:
                        critical_flags.append(m_fl)
                        issues.append(f"[{src_label} vs {tgt_label}] {m_det}")

                cross_document_matches.append(CrossDocumentMatch(
                    check_name=f"Name Consistency ({src_label} vs {tgt_label})",
                    source_document=src_label,
                    target_document=tgt_label,
                    status=m_stat,
                    score=m_sc,
                    details=m_det,
                    flag_code=m_fl
                ))

        avg_cross_score = (sum(cross_scores) / len(cross_scores)) if cross_scores else 0.0
        field_checks["cross_document_name_consistency"] = FieldCheckResult(
            check_name="Cross-Document Name Consistency Matrix",
            status=CheckStatus.PASS if avg_cross_score >= 90.0 else (CheckStatus.WARNING if avg_cross_score >= 65.0 else CheckStatus.FAIL),
            score=round(avg_cross_score, 1),
            details=f"Cross-document name alignment score: {avg_cross_score:.1f}%",
            is_critical=(avg_cross_score < 65.0 and len(cross_scores) > 0)
        )

        # -------------------------------------------------------------
        # 4. SCHOLARSHIP ELIGIBILITY CRITERIA CHECKS
        # -------------------------------------------------------------
        scheme_name = app_dict.get("scholarship_name") or ""
        scheme_rule = self.scholarship_rules.get(scheme_name, {})

        # 4A. Income Ceiling Check
        income_limit = scheme_rule.get("income_limit")
        extracted_income = income_fields.annual_income_inr if income_fields else None

        if income_limit is None:
            inc_status = CheckStatus.NOT_AVAILABLE
            inc_score = 100.0  # Neutral
            inc_details = f"No authoritative income threshold configured for scheme '{scheme_name}'"
            inc_flag = None
        elif extracted_income is None:
            inc_status = CheckStatus.NOT_AVAILABLE
            inc_score = 0.0
            inc_details = "Annual income figure not available from Income Certificate"
            inc_flag = None
        elif extracted_income <= income_limit:
            inc_status = CheckStatus.PASS
            inc_score = 100.0
            inc_details = f"Annual income ₹{extracted_income:,.2f} is within limit of ₹{income_limit:,.2f}"
            inc_flag = None
        else:
            inc_status = CheckStatus.FAIL
            inc_score = 0.0
            inc_details = f"Annual income ₹{extracted_income:,.2f} exceeds scholarship limit of ₹{income_limit:,.2f}"
            inc_flag = "INCOME_LIMIT_EXCEEDED"
            critical_flags.append(inc_flag)
            issues.append(inc_details)

        field_checks["income_eligibility"] = FieldCheckResult(
            check_name="Scholarship Family Income Ceiling",
            status=inc_status,
            score=inc_score,
            details=inc_details,
            is_critical=(inc_status == CheckStatus.FAIL),
            flag_code=inc_flag,
            data={"extracted_income": extracted_income, "limit": income_limit}
        )

        # 4B. Domicile Check
        requires_domicile = scheme_rule.get("requires_maharashtra_domicile", True)
        is_domicile = domicile_fields.is_maharashtra_domicile if domicile_fields else None
        state_str = domicile_fields.state if domicile_fields else None

        if not requires_domicile:
            dom_status = CheckStatus.NOT_AVAILABLE
            dom_score = 100.0
            dom_details = "Scheme does not enforce a state domicile requirement"
            dom_flag = None
        elif is_domicile is True or (state_str and state_str.strip().lower() in ("maharashtra", "mh")):
            dom_status = CheckStatus.PASS
            dom_score = 100.0
            dom_details = f"Confirmed Maharashtra State domicile ({state_str or 'Maharashtra'})"
            dom_flag = None
        elif is_domicile is False or (state_str and state_str.strip().lower() not in ("maharashtra", "mh")):
            dom_status = CheckStatus.FAIL
            dom_score = 0.0
            dom_details = f"Domicile check failed: State is '{state_str or 'Non-Maharashtra'}'"
            dom_flag = "NON_MAHARASHTRA_DOMICILE"
            critical_flags.append(dom_flag)
            issues.append(dom_details)
        else:
            dom_status = CheckStatus.NOT_AVAILABLE
            dom_score = 0.0
            dom_details = "Domicile certificate state confirmation unavailable"
            dom_flag = None

        field_checks["domicile_eligibility"] = FieldCheckResult(
            check_name="Maharashtra Domicile Eligibility",
            status=dom_status,
            score=dom_score,
            details=dom_details,
            is_critical=(dom_status == CheckStatus.FAIL),
            flag_code=dom_flag
        )

        # 4C. Marksheet Academic Performance Check
        min_pct = scheme_rule.get("minimum_percentage")
        extracted_pct = marksheet_fields.percentage if marksheet_fields else None
        result_status_str = (marksheet_fields.result_status or "").strip().upper() if marksheet_fields else ""

        if result_status_str in ("FAIL", "FAILED", "ATKT", "DETENTION", "UNSUCCESSFUL"):
            mark_status = CheckStatus.FAIL
            mark_score = 0.0
            mark_details = f"Academic result status indicates failure ({result_status_str})"
            mark_flag = "MARKSHEET_FAILED"
            critical_flags.append(mark_flag)
            issues.append(mark_details)
        elif min_pct is not None:
            if extracted_pct is None:
                mark_status = CheckStatus.WARNING
                mark_score = 50.0
                mark_details = f"Percentage unavailable to evaluate minimum requirement ({min_pct}%)"
                mark_flag = None
            elif extracted_pct >= min_pct:
                mark_status = CheckStatus.PASS
                mark_score = 100.0
                mark_details = f"Academic marks ({extracted_pct}%) satisfy minimum threshold ({min_pct}%)"
                mark_flag = None
            else:
                mark_status = CheckStatus.FAIL
                mark_score = 0.0
                mark_details = f"Academic marks ({extracted_pct}%) below required threshold ({min_pct}%)"
                mark_flag = "MARKSHEET_PERCENTAGE_BELOW_THRESHOLD"
                critical_flags.append(mark_flag)
                issues.append(mark_details)
        else:
            if extracted_pct is not None or result_status_str in ("PASS", "PASSED", "FIRST CLASS", "DISTINCTION"):
                mark_status = CheckStatus.PASS
                mark_score = 100.0
                mark_details = f"Academic performance verified (Score: {extracted_pct or 'PASS'}%)"
                mark_flag = None
            else:
                mark_status = CheckStatus.NOT_AVAILABLE
                mark_score = 0.0
                mark_details = "Academic performance fields not available"
                mark_flag = None

        field_checks["marksheet_performance"] = FieldCheckResult(
            check_name="Academic Marksheet & Eligibility Check",
            status=mark_status,
            score=mark_score,
            details=mark_details,
            is_critical=(mark_status == CheckStatus.FAIL),
            flag_code=mark_flag
        )

        # -------------------------------------------------------------
        # 5. DETERMINISTIC AGGREGATE SCORING & DECISION
        # -------------------------------------------------------------
        # Explainable Weight Distribution (Total 100.0 points):
        # - Identity & Consistency (40 pts): Name (10), DOB (10), ID Number (10), Cross-Name (10)
        # - Eligibility Rules (40 pts): Income (15), Domicile (15), Marksheet (10)
        # - Document Quality & Completeness (20 pts): quality_score
        identity_pts = (
            (name_score * 0.10) +
            (dob_score * 0.10) +
            (id_score * 0.10) +
            (avg_cross_score * 0.10)
        )
        eligibility_pts = (
            (inc_score * 0.15) +
            (dom_score * 0.15) +
            (mark_score * 0.10)
        )
        total_score = min(100.0, max(0.0, identity_pts + eligibility_pts + (quality_score * 0.20)))

        # Overall Status Determination
        has_critical_fail = any(
            f in critical_flags for f in (
                "NAME_MISMATCH", "DOB_MISMATCH", "GOVERNMENT_ID_MISMATCH",
                "INCOME_LIMIT_EXCEEDED", "NON_MAHARASHTRA_DOMICILE", "MARKSHEET_FAILED"
            )
        )

        has_unreadable_or_missing = any("UNREADABLE" in f or "MISSING" in f for f in critical_flags)
        has_warnings = any(fc.status == CheckStatus.WARNING for fc in field_checks.values())

        if has_critical_fail:
            overall_status = CheckStatus.FAIL
            recommended_status = "NEEDS_REVIEW"
        elif has_unreadable_or_missing or has_warnings or total_score < 85.0:
            overall_status = CheckStatus.WARNING
            recommended_status = "NEEDS_REVIEW"
        else:
            overall_status = CheckStatus.PASS
            recommended_status = "VERIFIED"

        return VerificationEvaluation(
            overall_status=overall_status,
            overall_score=round(total_score, 1),
            field_checks=field_checks,
            cross_document_matches=cross_document_matches,
            issues=issues,
            critical_flags=critical_flags,
            recommended_status=recommended_status
        )
