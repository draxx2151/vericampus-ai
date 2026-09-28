from typing import Optional, Dict, Any, Union
from app.db.models.enums import DocumentType
from app.services.verification.base import DocumentExtractionResult, ReadabilityScore
from app.services.verification.rules_engine import VerificationEvaluation, CheckStatus
from app.services.risk_analysis.schemas import RiskFeatures


class FeatureBuilder:
    """
    Constructs deterministic, model-friendly RiskFeatures from VerificationEvaluation
    and document extraction outputs.
    Strictly excludes all Personally Identifiable Information (PII) such as Aadhaar
    numbers, student names, phone numbers, addresses, emails, and raw document contents.
    """

    @classmethod
    def build_features(
        cls,
        evaluation: VerificationEvaluation,
        extractions: Optional[Dict[Union[DocumentType, str], DocumentExtractionResult]] = None,
    ) -> RiskFeatures:
        field_checks = evaluation.field_checks or {}
        cross_matches = evaluation.cross_document_matches or []
        critical_flags = evaluation.critical_flags or []

        # 1. Identity Pass Rate (Checks relating to applicant identity)
        identity_check_keys = [
            "student_name_match",
            "date_of_birth_match",
            "government_id_match",
            "cross_document_name_consistency",
        ]
        identity_checks = [field_checks[k] for k in identity_check_keys if k in field_checks]
        if identity_checks:
            passed_count = sum(1 for c in identity_checks if c.status == CheckStatus.PASS)
            identity_pass_rate = round(passed_count / len(identity_checks), 3)
        else:
            identity_pass_rate = 1.0 if not critical_flags else 0.0

        # 2. Specific Mismatch Counts
        name_mismatches = sum(
            1 for c in identity_checks
            if c.flag_code in ("NAME_MISMATCH", "NAME_VARIATION") or c.status in (CheckStatus.FAIL, CheckStatus.WARNING)
        )
        if any("NAME_MISMATCH" in f for f in critical_flags) and name_mismatches == 0:
            name_mismatches = 1

        dob_mismatch_count = 1 if any("DOB_MISMATCH" in f for f in critical_flags) or (
            "date_of_birth_match" in field_checks and field_checks["date_of_birth_match"].status == CheckStatus.FAIL
        ) else 0

        government_id_mismatch_count = 1 if any("GOVERNMENT_ID_MISMATCH" in f for f in critical_flags) or (
            "government_id_match" in field_checks and field_checks["government_id_match"].status == CheckStatus.FAIL
        ) else 0

        # 3. Scheme Eligibility Issue Indicators (0 or 1)
        domicile_issue = 1 if any("DOMICILE" in f for f in critical_flags) or (
            "domicile_eligibility" in field_checks and field_checks["domicile_eligibility"].status == CheckStatus.FAIL
        ) else 0

        income_issue = 1 if any("INCOME" in f for f in critical_flags) or (
            "income_eligibility" in field_checks and field_checks["income_eligibility"].status == CheckStatus.FAIL
        ) else 0

        marksheet_issue = 1 if any("MARKSHEET" in f for f in critical_flags) or (
            "marksheet_performance" in field_checks and field_checks["marksheet_performance"].status == CheckStatus.FAIL
        ) else 0

        # 4. Missing Fields Count
        missing_fields = sum(
            1 for fc in field_checks.values() if fc.status == CheckStatus.NOT_AVAILABLE
        )
        if extractions:
            for ext in extractions.values():
                if ext and ext.extracted_fields:
                    dump = ext.extracted_fields.model_dump()
                    missing_fields += sum(1 for v in dump.values() if v is None)
                elif ext and not ext.extraction_success:
                    missing_fields += 4

        # 5. Warning and Critical Failure Counts
        warnings = sum(1 for fc in field_checks.values() if fc.status == CheckStatus.WARNING)
        warnings += sum(1 for cm in cross_matches if cm.status == CheckStatus.WARNING)
        critical_count = len(critical_flags)

        # 6. Cross Document Mismatch Count
        cross_mismatches = sum(
            1 for cm in cross_matches if cm.status in (CheckStatus.FAIL, CheckStatus.WARNING)
        )

        # 7. OCR Readability / Quality Score (0.0 to 1.0)
        readability_weights = {
            ReadabilityScore.HIGH: 1.0,
            ReadabilityScore.MEDIUM: 0.75,
            ReadabilityScore.LOW: 0.40,
            ReadabilityScore.UNREADABLE: 0.0,
        }
        if extractions:
            scores = [
                readability_weights.get(ext.readability, 0.0)
                for ext in extractions.values()
                if ext is not None
            ]
            ocr_quality_score = round(sum(scores) / len(scores), 3) if scores else 0.5
        else:
            # Estimate from overall score if extractions not provided
            ocr_quality_score = round(max(0.0, min(1.0, evaluation.overall_score / 100.0)), 3)

        # 8. Overall Rule Score from rules engine (0.0 to 100.0)
        overall_rule_score = round(max(0.0, min(100.0, evaluation.overall_score)), 1)

        return RiskFeatures(
            identity_pass_rate=identity_pass_rate,
            name_mismatch_count=name_mismatches,
            dob_mismatch_count=dob_mismatch_count,
            government_id_mismatch_count=government_id_mismatch_count,
            domicile_issue=domicile_issue,
            income_issue=income_issue,
            marksheet_issue=marksheet_issue,
            missing_field_count=missing_fields,
            warning_count=warnings,
            critical_failure_count=critical_count,
            cross_document_mismatch_count=cross_mismatches,
            ocr_quality_score=ocr_quality_score,
            overall_rule_score=overall_rule_score,
        )
