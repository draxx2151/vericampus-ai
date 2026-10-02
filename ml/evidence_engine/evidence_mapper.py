"""
VeriCampus AI — Stage 6: Evidence Mapper
Transforms technical verification results from Stages 1-5 and eligibility rules
into structured, traceable, and explainable EvidenceItem instances.
Enforces non-punitive semantics for unavailable/blocked stages and masks sensitive PII.
"""
import uuid
from typing import Dict, List, Any, Optional

from .config import ReviewReason
from .schemas import (
    EvidenceCategory,
    EvidenceStrength,
    EvidenceItem,
    mask_sensitive_pii_string,
)


def _gen_id(prefix: str = "ev") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def map_stage1_quality(quality_results: Optional[Dict[str, Any]]) -> List[EvidenceItem]:
    """
    Maps Stage 1 Document Quality Gate outputs into evidence items.
    """
    items: List[EvidenceItem] = []
    if not quality_results:
        return items

    docs = quality_results.get("documents", quality_results)
    if not isinstance(docs, dict):
        return items

    for doc_type, assessment in docs.items():
        if not isinstance(assessment, dict):
            continue

        q_score = assessment.get("quality_score", 0.0)
        q_level = str(assessment.get("quality_level", "")).upper()
        q_status = str(assessment.get("quality_gate_status", "")).upper()
        reasons = assessment.get("reasons", [])

        if q_level == "HIGH" or (q_score >= 85.0 and q_status == "PASS"):
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.SUPPORTING,
                source_stage="STAGE_1",
                source_document=doc_type,
                check_type="document_quality_gate",
                status="PASS",
                strength=EvidenceStrength.MODERATE,
                title=f"High Document Quality: {doc_type.replace('_', ' ').title()}",
                explanation=f"Document image resolution and optical clarity meet quality verification standards (score: {q_score:.1f}/100).",
                requires_human_review=False,
                metadata={"quality_score": q_score, "quality_level": q_level},
            ))
        elif q_level == "ACCEPTABLE" or (q_score >= 70.0 and q_status == "PASS"):
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.SUPPORTING,
                source_stage="STAGE_1",
                source_document=doc_type,
                check_type="document_quality_gate",
                status="PASS",
                strength=EvidenceStrength.WEAK,
                title=f"Acceptable Document Quality: {doc_type.replace('_', ' ').title()}",
                explanation=f"Document image clarity is sufficient for OCR reading (score: {q_score:.1f}/100).",
                requires_human_review=False,
                metadata={"quality_score": q_score, "quality_level": q_level},
            ))
        elif q_level == "LOW" or q_status == "WARNING":
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.WARNING,
                source_stage="STAGE_1",
                source_document=doc_type,
                check_type="document_quality_gate",
                status="WARNING",
                strength=EvidenceStrength.WEAK,
                title=f"Moderate Document Quality Warning: {doc_type.replace('_', ' ').title()}",
                explanation=f"Document image exhibits minor blur or lower resolution (score: {q_score:.1f}/100). Administrative inspection recommended.",
                reason_code=ReviewReason.LOW_DOCUMENT_QUALITY.value,
                requires_human_review=False,
                metadata={"quality_score": q_score, "reasons": reasons},
            ))
        elif q_level == "UNREADABLE" or q_status == "REUPLOAD_REQUIRED":
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.WARNING,
                source_stage="STAGE_1",
                source_document=doc_type,
                check_type="document_quality_gate",
                status="REUPLOAD_REQUIRED",
                strength=EvidenceStrength.MODERATE,
                title=f"Document Unreadable / Re-upload Required: {doc_type.replace('_', ' ').title()}",
                explanation=f"Document scan is degraded or illegible (score: {q_score:.1f}/100). A clearer replacement scan is required.",
                reason_code=ReviewReason.LOW_DOCUMENT_QUALITY.value,
                requires_human_review=True,
                metadata={"quality_score": q_score, "reasons": reasons},
            ))

    return items


def map_stage2_classification(classification_results: Optional[Dict[str, Any]]) -> List[EvidenceItem]:
    """
    Maps Stage 2 AI Document Classification outputs into evidence items.
    """
    items: List[EvidenceItem] = []
    if not classification_results:
        return items

    docs = classification_results.get("documents", classification_results)
    if not isinstance(docs, dict):
        return items

    for doc_type, c_data in docs.items():
        if not isinstance(c_data, dict):
            continue

        c_status = str(c_data.get("classification_status", "")).upper()
        pred_type = c_data.get("predicted_type", "")
        conf = c_data.get("confidence", 0.0)
        reasons = c_data.get("reasons", [])

        if c_status == "PASS":
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.SUPPORTING,
                source_stage="STAGE_2",
                source_document=doc_type,
                check_type="document_classification",
                status="PASS",
                strength=EvidenceStrength.MODERATE,
                title=f"Document Type Verified: {doc_type.replace('_', ' ').title()}",
                explanation=f"Uploaded file matches the required {doc_type.replace('_', ' ')} layout (confidence: {conf*100:.1f}%).",
                requires_human_review=False,
                metadata={"confidence": conf, "predicted_type": pred_type},
            ))
        elif c_status == "WARNING":
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.WARNING,
                source_stage="STAGE_2",
                source_document=doc_type,
                check_type="document_classification",
                status="WARNING",
                strength=EvidenceStrength.WEAK,
                title=f"Classification Confidence Warning: {doc_type.replace('_', ' ').title()}",
                explanation=f"Document visual structure matches expected type with moderate confidence ({conf*100:.1f}%).",
                reason_code=ReviewReason.OCR_LOW_CONFIDENCE.value,
                requires_human_review=False,
                metadata={"confidence": conf, "reasons": reasons},
            ))
        elif c_status == "DOCUMENT_TYPE_MISMATCH":
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.CONFLICTING,
                source_stage="STAGE_2",
                source_document=doc_type,
                check_type="document_classification",
                status="DOCUMENT_TYPE_MISMATCH",
                strength=EvidenceStrength.STRONG,
                title=f"Document Slot Mismatch: {doc_type.replace('_', ' ').title()}",
                explanation=f"Uploaded file was recognized as {pred_type.replace('_', ' ')} instead of required {doc_type.replace('_', ' ')}. Replacement upload required.",
                expected_value=doc_type,
                observed_value=pred_type,
                reason_code=ReviewReason.DOCUMENT_TYPE_MISMATCH.value,
                requires_human_review=True,
                metadata={"confidence": conf, "reasons": reasons},
            ))
        elif c_status == "UNKNOWN":
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.WARNING,
                source_stage="STAGE_2",
                source_document=doc_type,
                check_type="document_classification",
                status="UNKNOWN",
                strength=EvidenceStrength.WEAK,
                title=f"Unrecognized Document Layout: {doc_type.replace('_', ' ').title()}",
                explanation=f"Document layout could not be confidently identified as {doc_type.replace('_', ' ')}. Administrative scrutiny recommended.",
                reason_code=ReviewReason.DOCUMENT_TYPE_MISMATCH.value,
                requires_human_review=True,
                metadata={"confidence": conf, "reasons": reasons},
            ))

    return items


def map_stage3_extractions(field_extractions: Optional[Dict[str, Any]]) -> List[EvidenceItem]:
    """
    Maps Stage 3 Structured Field Extractions into evidence items.
    """
    items: List[EvidenceItem] = []
    if not field_extractions or not isinstance(field_extractions, dict):
        return items

    for doc_type, ext_data in field_extractions.items():
        if not isinstance(ext_data, dict):
            continue

        e_status = str(ext_data.get("extraction_status", "")).upper()
        completeness = ext_data.get("completeness_score", 0.0)
        conf = ext_data.get("overall_confidence", 0.0)
        fields = ext_data.get("fields", {})

        if e_status == "COMPLETE":
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.SUPPORTING,
                source_stage="STAGE_3",
                source_document=doc_type,
                check_type="field_extraction_completeness",
                status="COMPLETE",
                strength=EvidenceStrength.MODERATE,
                title=f"Complete Information Extracted: {doc_type.replace('_', ' ').title()}",
                explanation=f"All key mandatory fields successfully extracted from {doc_type.replace('_', ' ')} (completeness: {completeness*100:.0f}%).",
                requires_human_review=False,
                metadata={"completeness_score": completeness, "overall_confidence": conf},
            ))
        elif e_status == "PARTIAL":
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.WARNING,
                source_stage="STAGE_3",
                source_document=doc_type,
                check_type="field_extraction_completeness",
                status="PARTIAL",
                strength=EvidenceStrength.WEAK,
                title=f"Partial Field Extraction: {doc_type.replace('_', ' ').title()}",
                explanation=f"Some non-critical fields in {doc_type.replace('_', ' ')} could not be automatically located by OCR.",
                reason_code=ReviewReason.REQUIRED_FIELD_MISSING.value,
                requires_human_review=False,
                metadata={"completeness_score": completeness},
            ))
        elif e_status == "BLOCKED":
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.NEUTRAL,
                source_stage="STAGE_3",
                source_document=doc_type,
                check_type="field_extraction_completeness",
                status="BLOCKED",
                strength=EvidenceStrength.NONE,
                title=f"Extraction Skipped: {doc_type.replace('_', ' ').title()}",
                explanation=f"Field extraction was deliberately bypassed because earlier stages flagged this document.",
                reason_code=ReviewReason.LOW_DOCUMENT_QUALITY.value,
                requires_human_review=False,
                metadata={"extraction_status": "BLOCKED"},
            ))
        elif e_status == "FAILED":
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.TECHNICAL_ERROR,
                source_stage="STAGE_3",
                source_document=doc_type,
                check_type="field_extraction_completeness",
                status="FAILED",
                strength=EvidenceStrength.NONE,
                title=f"Field Extraction Failed: {doc_type.replace('_', ' ').title()}",
                explanation=f"OCR engine could not parse text from this document.",
                reason_code=ReviewReason.TECHNICAL_PROCESSING_ERROR.value,
                requires_human_review=True,
                metadata={"extraction_status": "FAILED"},
            ))

        # Check field-level items (e.g. Government ID number masked)
        if isinstance(fields, dict):
            id_field = fields.get("id_number")
            if isinstance(id_field, dict) and id_field.get("extraction_status") == "EXTRACTED":
                disp_val = mask_sensitive_pii_string(id_field.get("display_value") or id_field.get("raw_value"))
                items.append(EvidenceItem(
                    evidence_id=_gen_id(),
                    category=EvidenceCategory.SUPPORTING,
                    source_stage="STAGE_3",
                    source_document=doc_type,
                    check_type="identity_number_extraction",
                    status="EXTRACTED",
                    strength=EvidenceStrength.MODERATE,
                    title="Government ID Number Captured",
                    explanation=f"Valid identifier string was recognized and securely masked: {disp_val}",
                    field_name="id_number",
                    masked_value=disp_val,
                    requires_human_review=False,
                ))

    return items


def map_stage4_tamper_and_consistency(stage4_result: Optional[Dict[str, Any]]) -> List[EvidenceItem]:
    """
    Maps Stage 4 Tamper Detection and Cross-Document Consistency outputs into evidence items.
    """
    items: List[EvidenceItem] = []
    if not stage4_result or not isinstance(stage4_result, dict):
        return items

    # 1. Cross-Document Consistency Checks
    cons_assessment = stage4_result.get("consistency_assessment", {})
    if isinstance(cons_assessment, dict):
        checks = cons_assessment.get("checks", [])
        for chk in checks:
            if not isinstance(chk, dict):
                continue

            c_name = chk.get("check_name", "cross_document_check")
            status = str(chk.get("status", "")).upper()
            reason = chk.get("reason", "")
            field_name = chk.get("field_name", "")
            is_critical = chk.get("is_critical", False)
            docs_compared = chk.get("documents_compared", [])

            if status == "PASS":
                strength = EvidenceStrength.STRONG if field_name in ("dob", "id_number") else EvidenceStrength.MODERATE
                items.append(EvidenceItem(
                    evidence_id=_gen_id(),
                    category=EvidenceCategory.SUPPORTING,
                    source_stage="STAGE_4",
                    source_document="cross_document",
                    check_type=f"cross_document_{field_name or c_name}",
                    status="PASS",
                    strength=strength,
                    title=f"Cross-Document {field_name.upper() if field_name else c_name} Verified",
                    explanation=f"Information is consistent across submitted records: {reason}",
                    field_name=field_name,
                    requires_human_review=False,
                    metadata={"documents_compared": docs_compared},
                ))
            elif status in ("NEEDS_REVIEW", "FAIL") or is_critical:
                reason_code = ReviewReason.CROSS_DOCUMENT_CONFLICT.value
                if "dob" in c_name.lower() or field_name == "dob":
                    reason_code = ReviewReason.DOB_MISMATCH.value
                elif "name" in c_name.lower() or field_name == "name":
                    reason_code = ReviewReason.NAME_MISMATCH.value
                elif "id" in c_name.lower() or field_name == "id_number":
                    reason_code = ReviewReason.GOVERNMENT_ID_MISMATCH.value
                elif "mark" in c_name.lower():
                    reason_code = ReviewReason.MARKS_ARITHMETIC_CONFLICT.value

                items.append(EvidenceItem(
                    evidence_id=_gen_id(),
                    category=EvidenceCategory.CONFLICTING,
                    source_stage="STAGE_4",
                    source_document="cross_document",
                    check_type=f"cross_document_{field_name or c_name}",
                    status="MISMATCH",
                    strength=EvidenceStrength.STRONG,
                    title=f"Cross-Document Discrepancy: {field_name.upper() if field_name else c_name}",
                    explanation=f"Inconsistency detected across documents: {reason}. Administrative review required.",
                    field_name=field_name,
                    reason_code=reason_code,
                    requires_human_review=True,
                    metadata={"documents_compared": docs_compared},
                ))
            elif status == "WARNING":
                items.append(EvidenceItem(
                    evidence_id=_gen_id(),
                    category=EvidenceCategory.WARNING,
                    source_stage="STAGE_4",
                    source_document="cross_document",
                    check_type=f"cross_document_{field_name or c_name}",
                    status="WARNING",
                    strength=EvidenceStrength.WEAK,
                    title=f"Cross-Document Variation: {field_name.upper() if field_name else c_name}",
                    explanation=f"Minor variation noted: {reason}",
                    field_name=field_name,
                    reason_code=ReviewReason.NAME_MISMATCH.value if "name" in c_name.lower() else ReviewReason.CROSS_DOCUMENT_CONFLICT.value,
                    requires_human_review=False,
                    metadata={"documents_compared": docs_compared},
                ))

    # 2. Tamper Signals
    tamper_assessment = stage4_result.get("tamper_assessment", {})
    if isinstance(tamper_assessment, dict):
        signals = tamper_assessment.get("signals", [])
        for sig in signals:
            if not isinstance(sig, dict):
                continue

            sig_name = sig.get("signal_name", "tamper_signal")
            sig_status = str(sig.get("status", "")).upper()
            sig_sev = str(sig.get("severity", "")).upper()
            sig_exp = sig.get("explanation", "")
            sig_cat = sig.get("category", "")
            doc_type = sig.get("affected_document")

            if sig_status in ("NEEDS_REVIEW", "FAIL") or sig_sev in ("CRITICAL", "HIGH"):
                items.append(EvidenceItem(
                    evidence_id=_gen_id(),
                    category=EvidenceCategory.CONFLICTING,
                    source_stage="STAGE_4",
                    source_document=doc_type,
                    check_type=f"tamper_{sig_name}",
                    status="NEEDS_REVIEW",
                    strength=EvidenceStrength.MODERATE,
                    title=f"Visual / Structural Inconsistency: {sig_name.replace('_', ' ').title()}",
                    explanation=f"A visual or structural image signal requires administrative attention: {sig_exp}",
                    reason_code=ReviewReason.TAMPER_SIGNAL.value,
                    requires_human_review=True,
                    metadata={"signal_category": sig_cat, "severity": sig_sev},
                ))
            elif sig_status == "WARNING" or sig_sev in ("MEDIUM", "LOW", "INFO"):
                items.append(EvidenceItem(
                    evidence_id=_gen_id(),
                    category=EvidenceCategory.WARNING,
                    source_stage="STAGE_4",
                    source_document=doc_type,
                    check_type=f"tamper_{sig_name}",
                    status="WARNING",
                    strength=EvidenceStrength.WEAK,
                    title=f"Image Advisory Signal: {sig_name.replace('_', ' ').title()}",
                    explanation=f"Advisory metadata/image observation: {sig_exp}. This signal alone does not indicate document inauthenticity.",
                    reason_code=ReviewReason.TAMPER_SIGNAL.value,
                    requires_human_review=False,
                    metadata={"signal_category": sig_cat, "severity": sig_sev},
                ))

    return items


def map_stage5_authority(authority_results: Optional[Dict[str, Any]]) -> List[EvidenceItem]:
    """
    Maps Stage 5 Authority Verification outputs into evidence items.
    Strictly follows the Stage 5 contract:
    - MATCH -> Supporting
    - MISMATCH -> Conflicting
    - NOT_AVAILABLE -> Neutral (never negative/failure)
    - BLOCKED -> Neutral (never negative/failure)
    - ERROR -> Technical issue (never applicant fault)
    """
    items: List[EvidenceItem] = []
    if not authority_results or not isinstance(authority_results, dict):
        return items

    overall_status = str(authority_results.get("overall_status", "NOT_AVAILABLE")).upper()
    docs = authority_results.get("documents", {})

    # If document-level entries exist, process them
    if isinstance(docs, dict) and docs:
        for doc_type, res in docs.items():
            if not isinstance(res, dict):
                continue

            status = str(res.get("status", "NOT_AVAILABLE")).upper()
            provider = res.get("provider", "UnknownProvider")
            reason = res.get("reason", "")
            strength_str = str(res.get("evidence_strength", "NONE")).upper()
            strength = getattr(EvidenceStrength, strength_str, EvidenceStrength.NONE)
            ver_id = res.get("verification_id", "")

            if status == "MATCH":
                items.append(EvidenceItem(
                    evidence_id=_gen_id(),
                    category=EvidenceCategory.SUPPORTING,
                    source_stage="STAGE_5",
                    source_document=doc_type,
                    check_type="authority_record_match",
                    status="MATCH",
                    strength=strength if strength != EvidenceStrength.NONE else EvidenceStrength.STRONG,
                    title=f"Authoritative External Record Confirmed: {doc_type.replace('_', ' ').title()}",
                    explanation=f"Independent authority ({provider}) confirmed a matching identity record: {reason}",
                    requires_human_review=False,
                    metadata={"provider": provider, "verification_id": ver_id},
                ))
            elif status == "MISMATCH":
                items.append(EvidenceItem(
                    evidence_id=_gen_id(),
                    category=EvidenceCategory.CONFLICTING,
                    source_stage="STAGE_5",
                    source_document=doc_type,
                    check_type="authority_record_match",
                    status="MISMATCH",
                    strength=strength if strength != EvidenceStrength.NONE else EvidenceStrength.STRONG,
                    title=f"Authoritative Record Mismatch: {doc_type.replace('_', ' ').title()}",
                    explanation=f"External record returned by {provider} conflicts with extracted document data: {reason}. Administrative review required.",
                    reason_code=ReviewReason.AUTHORITY_MISMATCH.value,
                    requires_human_review=True,
                    metadata={"provider": provider, "verification_id": ver_id},
                ))
            elif status == "NOT_AVAILABLE":
                items.append(EvidenceItem(
                    evidence_id=_gen_id(),
                    category=EvidenceCategory.NEUTRAL,
                    source_stage="STAGE_5",
                    source_document=doc_type,
                    check_type="authority_record_match",
                    status="NOT_AVAILABLE",
                    strength=EvidenceStrength.NONE,
                    title=f"Authority Verification Unavailable: {doc_type.replace('_', ' ').title()}",
                    explanation="No authoritative external registry provider is configured in this deployment environment.",
                    reason_code=ReviewReason.AUTHORITY_UNAVAILABLE.value,
                    requires_human_review=False,
                    metadata={"provider": provider},
                ))
            elif status == "BLOCKED":
                items.append(EvidenceItem(
                    evidence_id=_gen_id(),
                    category=EvidenceCategory.NEUTRAL,
                    source_stage="STAGE_5",
                    source_document=doc_type,
                    check_type="authority_record_match",
                    status="BLOCKED",
                    strength=EvidenceStrength.NONE,
                    title=f"Authority Verification Skipped: {doc_type.replace('_', ' ').title()}",
                    explanation="Authority check was intentionally skipped because an earlier stage flagged document quality or slot type.",
                    reason_code=ReviewReason.AUTHORITY_CHECK_BLOCKED.value,
                    requires_human_review=False,
                    metadata={"provider": provider},
                ))
            elif status == "ERROR":
                items.append(EvidenceItem(
                    evidence_id=_gen_id(),
                    category=EvidenceCategory.TECHNICAL_ERROR,
                    source_stage="STAGE_5",
                    source_document=doc_type,
                    check_type="authority_record_match",
                    status="ERROR",
                    strength=EvidenceStrength.NONE,
                    title=f"Authority Provider Connection Issue: {doc_type.replace('_', ' ').title()}",
                    explanation=f"A temporary connection timeout occurred contacting {provider}: {reason}. This does not reflect applicant discrepancy.",
                    reason_code=ReviewReason.TECHNICAL_PROCESSING_ERROR.value,
                    requires_human_review=False,
                    metadata={"provider": provider},
                ))
    else:
        # Top-level fallback when per-document records are absent
        if overall_status == "NOT_AVAILABLE":
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.NEUTRAL,
                source_stage="STAGE_5",
                check_type="authority_verification_overall",
                status="NOT_AVAILABLE",
                strength=EvidenceStrength.NONE,
                title="Authority Provider Not Configured",
                explanation="No authorized external verification provider is configured. Verification proceeded on primary document analysis.",
                reason_code=ReviewReason.AUTHORITY_UNAVAILABLE.value,
                requires_human_review=False,
            ))
        elif overall_status == "BLOCKED":
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.NEUTRAL,
                source_stage="STAGE_5",
                check_type="authority_verification_overall",
                status="BLOCKED",
                strength=EvidenceStrength.NONE,
                title="Authority Verification Skipped",
                explanation="Stage 5 was bypassed because earlier stages flagged document quality or classification requirements.",
                reason_code=ReviewReason.AUTHORITY_CHECK_BLOCKED.value,
                requires_human_review=False,
            ))
        elif overall_status == "MISMATCH":
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.CONFLICTING,
                source_stage="STAGE_5",
                check_type="authority_verification_overall",
                status="MISMATCH",
                strength=EvidenceStrength.STRONG,
                title="Authoritative Record Mismatch",
                explanation="External record comparison resulted in conflicting data. Administrative review required.",
                reason_code=ReviewReason.AUTHORITY_MISMATCH.value,
                requires_human_review=True,
            ))

    return items


def map_rules_engine_eligibility(rules_evaluation: Any) -> List[EvidenceItem]:
    """
    Maps RulesEngine scheme eligibility and basic field checks into evidence items.
    """
    items: List[EvidenceItem] = []
    if not rules_evaluation:
        return items

    field_checks = getattr(rules_evaluation, "field_checks", None)
    if field_checks is None and isinstance(rules_evaluation, dict):
        field_checks = rules_evaluation.get("field_checks", {})

    if not isinstance(field_checks, dict):
        return items

    for check_name, check_data in field_checks.items():
        if hasattr(check_data, "model_dump"):
            chk = check_data.model_dump()
        elif isinstance(check_data, dict):
            chk = check_data
        else:
            chk = {
                "status": getattr(check_data, "status", ""),
                "details": getattr(check_data, "details", ""),
                "is_critical": getattr(check_data, "is_critical", False),
            }

        status = str(chk.get("status", "")).upper()

        details = chk.get("details", "")
        is_critical = chk.get("is_critical", False)

        # Focus on statutory scheme criteria (income, domicile, minimum percentage)
        if status == "FAIL" or (status == "NEEDS_REVIEW" and is_critical):
            items.append(EvidenceItem(
                evidence_id=_gen_id(),
                category=EvidenceCategory.CONFLICTING,
                source_stage="RULES_ENGINE",
                check_type=f"scheme_{check_name}",
                status="FAIL",
                strength=EvidenceStrength.STRONG,
                title=f"Eligibility Limit Exceeded: {check_name.replace('_', ' ').title()}",
                explanation=f"Scheme requirement check failed: {details}. Administrative review is required.",
                reason_code=ReviewReason.SCHEME_ELIGIBILITY_CONFLICT.value,
                requires_human_review=True,
                metadata={"check_name": check_name},
            ))
        elif status == "PASS":
            if any(k in check_name.lower() for k in ["income", "domicile", "percentage", "eligible"]):
                items.append(EvidenceItem(
                    evidence_id=_gen_id(),
                    category=EvidenceCategory.SUPPORTING,
                    source_stage="RULES_ENGINE",
                    check_type=f"scheme_{check_name}",
                    status="PASS",
                    strength=EvidenceStrength.MODERATE,
                    title=f"Scheme Requirement Satisfied: {check_name.replace('_', ' ').title()}",
                    explanation=f"Statutory eligibility check passed: {details}",
                    requires_human_review=False,
                    metadata={"check_name": check_name},
                ))

    return items
