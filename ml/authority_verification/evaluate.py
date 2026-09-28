"""
VeriCampus AI — Stage 5: Evaluation Harness
Validates schema compliance, field matching precision, masking, and non-punitive review routing.

NOTICE & GOVERNANCE COMPLIANCE:
All evaluation fixtures used herein are strictly labeled as SYNTHETIC TEST FIXTURES.
They are NOT real government or institutional records.
No simulated accuracy statistics or fake production metrics are claimed.
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.authority_verification.schemas import (
    AuthorityStatus,
    EvidenceStrength,
    FieldMatchStatus,
    ConsentStatus,
    RecordStatus,
)
from ml.authority_verification.matching import (
    match_government_id_fields,
    match_marksheet_fields,
    match_income_certificate_fields,
    match_domicile_certificate_fields,
)
from ml.authority_verification.providers.unavailable import UnavailableProvider
from ml.authority_verification.service import AuthorityVerificationService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stage5_evaluate")


# ==============================================================================
# SYNTHETIC TEST FIXTURES (NOT REAL GOVERNMENT RECORDS)
# ==============================================================================
SYNTHETIC_TEST_FIXTURES: List[Dict[str, Any]] = [
    {
        "fixture_id": "SYNTHETIC_01_GOVT_ID_EXACT_MATCH",
        "doc_type": "government_id",
        "extracted": {
            "name": "Amit Rajesh Patil",
            "date_of_birth": "2004-05-14",
            "id_number": "9876 5432 1098",
        },
        "authority": {
            "name": "Amit Rajesh Patil",
            "date_of_birth": "2004-05-14",
            "id_number": "987654321098",
        },
        "expected_status": AuthorityStatus.MATCH,
        "expected_strength": EvidenceStrength.MODERATE,  # Last-4 + name + DOB
    },
    {
        "fixture_id": "SYNTHETIC_02_GOVT_ID_DOB_MISMATCH",
        "doc_type": "government_id",
        "extracted": {
            "name": "Amit Rajesh Patil",
            "date_of_birth": "2004-05-14",
            "id_number": "9876 5432 1098",
        },
        "authority": {
            "name": "Amit Rajesh Patil",
            "date_of_birth": "2003-05-14",  # Discrepancy
            "id_number": "987654321098",
        },
        "expected_status": AuthorityStatus.MISMATCH,
        "expected_strength": EvidenceStrength.NONE,
    },
    {
        "fixture_id": "SYNTHETIC_03_MARKSHEET_MATCH",
        "doc_type": "marksheet",
        "extracted": {
            "student_name": "Patil Amit Rajesh",
            "roll_number": "M123456",
            "passing_year": "2024",
            "total_marks": "480",
        },
        "authority": {
            "student_name": "Amit Rajesh Patil",
            "roll_number": "M123456",
            "passing_year": "2024",
            "total_marks": "481",  # Within 2-mark tolerance
        },
        "expected_status": AuthorityStatus.MATCH,
        "expected_strength": EvidenceStrength.STRONG,
    },
    {
        "fixture_id": "SYNTHETIC_04_INCOME_CERT_MISMATCH",
        "doc_type": "income_certificate",
        "extracted": {
            "applicant_name": "Amit Patil",
            "certificate_number": "INC/2024/7890",
            "annual_income": "120000",
        },
        "authority": {
            "applicant_name": "Amit Patil",
            "certificate_number": "INC/2024/7890",
            "annual_income": "250000",  # Exceeds Rs. 1,000 tolerance
        },
        "expected_status": AuthorityStatus.MISMATCH,
        "expected_strength": EvidenceStrength.NONE,
    },
]


def run_evaluation() -> bool:
    logger.info("Starting Stage 5 Authority Verification Evaluation...")
    logger.info("Note: Using strictly labeled SYNTHETIC TEST FIXTURES. Zero live government calls.")

    passed_checks = 0
    total_checks = 0

    # 1. Evaluate UnavailableProvider (Default Offline Behavior)
    total_checks += 1
    unav_provider = UnavailableProvider()
    unav_res = unav_provider.verify("government_id", {"name": "Test Student"})
    if unav_res.status == AuthorityStatus.NOT_AVAILABLE and unav_res.evidence_strength == EvidenceStrength.NONE:
        passed_checks += 1
        logger.info("PASS: UnavailableProvider returned NOT_AVAILABLE with NONE evidence.")
    else:
        logger.error("FAIL: UnavailableProvider returned unexpected status: %s", unav_res.status)

    # 2. Evaluate Synthetic Matcher Fixtures
    for fix in SYNTHETIC_TEST_FIXTURES:
        total_checks += 1
        doc_type = fix["doc_type"]
        if doc_type == "government_id":
            comparisons, strength, status = match_government_id_fields(fix["extracted"], fix["authority"])
        elif doc_type == "marksheet":
            comparisons, strength, status = match_marksheet_fields(fix["extracted"], fix["authority"])
        elif doc_type == "income_certificate":
            comparisons, strength, status = match_income_certificate_fields(fix["extracted"], fix["authority"])
        else:
            comparisons, strength, status = match_domicile_certificate_fields(fix["extracted"], fix["authority"])

        status_ok = status == fix["expected_status"]
        strength_ok = strength == fix["expected_strength"]

        if status_ok and strength_ok:
            passed_checks += 1
            logger.info("PASS: %s -> %s (strength=%s)", fix["fixture_id"], status.value, strength.value)
        else:
            logger.error("FAIL: %s -> got status=%s (expected %s), strength=%s (expected %s)",
                         fix["fixture_id"], status.value, fix["expected_status"].value,
                         strength.value, fix["expected_strength"].value)

    # 3. Evaluate PII Masking Invariants
    total_checks += 1
    sample_id_comp, _, _ = match_government_id_fields(
        {"id_number": "1234 5678 9012", "name": "Test"},
        {"id_number": "1234 5678 9012", "name": "Test"}
    )
    extracted_val = sample_id_comp["id_number"].extracted_value
    if "12345678" not in extracted_val and "9012" in extracted_val:
        passed_checks += 1
        logger.info("PASS: Sensitive ID masking verified (value=%s)", extracted_val)
    else:
        logger.error("FAIL: Raw ID leaked in comparison value: %s", extracted_val)

    # 4. Evaluate Stage Gating (Stage 1 Low Quality -> BLOCKED)
    total_checks += 1
    service = AuthorityVerificationService()
    gated_res = service.verify_document(
        document_type="government_id",
        extracted_data={"name": "Test Student"},
        quality_info={"quality_score": 45.0, "quality_gate_status": "FAIL"},
    )
    if gated_res.status == AuthorityStatus.BLOCKED and "quality is insufficient" in gated_res.reason:
        passed_checks += 1
        logger.info("PASS: Stage 1 low-quality gating successfully returned BLOCKED status.")
    else:
        logger.error("FAIL: Quality gating failed to block: status=%s", gated_res.status)

    logger.info("Stage 5 Evaluation Completed: %d / %d checks passed (%.1f%%).",
                passed_checks, total_checks, (passed_checks / total_checks) * 100.0)
    return passed_checks == total_checks


if __name__ == "__main__":
    success = run_evaluation()
    sys.exit(0 if success else 1)
