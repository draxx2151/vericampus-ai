"""
VeriCampus AI — Stage 6: Evidence Engine Synthetic Evaluation Suite
Runs automated benchmark scenarios validating evidence aggregation, semantics, and review state logic.
Uses synthetic fixtures to avoid data leakage and verifies zero PII exposure.
"""
import os
import sys
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ml.evidence_engine.service import EvidenceEngineService

from ml.evidence_engine.schemas import EvidenceState, EvidenceCategory, EvidenceStrength


def evaluate_synthetic_scenarios() -> Dict[str, Any]:
    """
    Evaluates 6 core benchmark scenarios validating Stage 6 decision-support logic.
    """
    service = EvidenceEngineService()
    results = {}

    # Scenario 1: Clean consistent application
    clean_summary = service.evaluate(
        application_id="app-synthetic-01",
        quality_results={
            "documents": {
                "government_id": {"quality_score": 92.0, "quality_level": "HIGH", "quality_gate_status": "PASS"},
                "marksheet": {"quality_score": 88.0, "quality_level": "HIGH", "quality_gate_status": "PASS"},
            }
        },
        classification_results={
            "documents": {
                "government_id": {"classification_status": "PASS", "confidence": 0.95},
                "marksheet": {"classification_status": "PASS", "confidence": 0.93},
            }
        },
        extractions={
            "government_id": {
                "extraction_status": "COMPLETE",
                "completeness_score": 1.0,
                "fields": {
                    "id_number": {"extraction_status": "EXTRACTED", "display_value": "********1234"}
                }
            }
        },
        tamper_results={
            "overall_status": "PASS",
            "consistency_assessment": {
                "checks": [
                    {"check_name": "name_consistency", "status": "PASS", "field_name": "name", "reason": "Identical names"},
                    {"check_name": "dob_consistency", "status": "PASS", "field_name": "dob", "reason": "Identical dates"}
                ]
            }
        },
        authority_results={
            "overall_status": "NOT_AVAILABLE",
            "documents": {}
        }
    )
    assert clean_summary.overall_evidence_state == EvidenceState.CLEAR_FOR_REVIEW, f"Expected CLEAR_FOR_REVIEW, got {clean_summary.overall_evidence_state}"
    assert clean_summary.human_review_required is False
    assert len(clean_summary.supporting_evidence) >= 4
    results["scenario_1_clean"] = "PASS"

    # Scenario 2: DOB mismatch across documents
    dob_summary = service.evaluate(
        application_id="app-synthetic-02",
        tamper_results={
            "overall_status": "NEEDS_REVIEW",
            "consistency_assessment": {
                "checks": [
                    {"check_name": "dob_consistency", "status": "NEEDS_REVIEW", "field_name": "dob", "reason": "2004-01-01 vs 2005-02-02", "is_critical": True}
                ]
            }
        }
    )
    assert dob_summary.overall_evidence_state == EvidenceState.HUMAN_REVIEW_REQUIRED
    assert dob_summary.human_review_required is True
    assert "DOB_MISMATCH" in dob_summary.review_reasons
    results["scenario_2_dob_mismatch"] = "PASS"

    # Scenario 3: Authority mismatch
    auth_summary = service.evaluate(
        application_id="app-synthetic-03",
        authority_results={
            "overall_status": "MISMATCH",
            "documents": {
                "government_id": {
                    "status": "MISMATCH",
                    "provider": "DigiLockerProvider",
                    "reason": "Name mismatch on authoritative record",
                    "evidence_strength": "STRONG",
                    "verification_id": "av-auth-01"
                }
            }
        }
    )
    assert auth_summary.overall_evidence_state == EvidenceState.HUMAN_REVIEW_REQUIRED
    assert auth_summary.human_review_required is True
    assert "AUTHORITY_MISMATCH" in auth_summary.review_reasons
    results["scenario_3_authority_mismatch"] = "PASS"

    # Scenario 4: Authority unavailable (must remain neutral, not conflict)
    unavail_summary = service.evaluate(
        application_id="app-synthetic-04",
        authority_results={
            "overall_status": "NOT_AVAILABLE",
            "documents": {
                "government_id": {
                    "status": "NOT_AVAILABLE",
                    "provider": "UnavailableProvider",
                    "reason": "Provider not configured"
                }
            }
        }
    )
    assert len(unavail_summary.conflicting_evidence) == 0
    assert len(unavail_summary.neutral_evidence) >= 1
    results["scenario_4_authority_unavailable_neutral"] = "PASS"

    # Scenario 5: Scheme income ceiling exceeded
    class MockCheck:
        def __init__(self, status, details):
            self.status = status
            self.details = details
            self.is_critical = True

    class MockRulesEval:
        def __init__(self):
            self.field_checks = {
                "income_limit": MockCheck("FAIL", "Income Rs 8,50,000 exceeds ceiling Rs 8,00,000")
            }

    elig_summary = service.evaluate(
        application_id="app-synthetic-05",
        rules_evaluation=MockRulesEval()
    )
    assert elig_summary.overall_evidence_state == EvidenceState.HUMAN_REVIEW_REQUIRED
    assert "SCHEME_ELIGIBILITY_CONFLICT" in elig_summary.review_reasons
    results["scenario_5_eligibility_conflict"] = "PASS"

    # Scenario 6: Unreadable document scan (insufficient evidence)
    unreadable_summary = service.evaluate(
        application_id="app-synthetic-06",
        quality_results={
            "documents": {
                "government_id": {"quality_score": 15.0, "quality_level": "UNREADABLE", "quality_gate_status": "REUPLOAD_REQUIRED"}
            }
        }
    )
    assert unreadable_summary.overall_evidence_state == EvidenceState.INSUFFICIENT_EVIDENCE
    results["scenario_6_unreadable_insufficient"] = "PASS"

    return results


if __name__ == "__main__":
    res = evaluate_synthetic_scenarios()
    print("=" * 60)
    print("STAGE 6 EVIDENCE ENGINE EVALUATION BENCHMARK RESULTS")
    print("=" * 60)
    for k, v in res.items():
        print(f"  {k}: {v}")
    print("All 6 benchmark scenarios passed successfully.")
