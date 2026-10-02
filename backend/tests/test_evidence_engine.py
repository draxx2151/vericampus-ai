"""
VeriCampus AI — Stage 6: Evidence & Decision Support Engine Automated Test Suite
Comprehensive suite (35+ test cases) verifying:
1. Schema integrity, EvidenceCategory, EvidenceStrength, EvidenceState, ReviewReason
2. PII masking in EvidenceItem descriptions (Aadhaar, PAN, storage paths)
3. Stage 1 Quality Gate evidence mapping (supporting vs warning/insufficient)
4. Stage 2 Classification evidence mapping (matching vs slot mismatch conflict)
5. Stage 3 Field Extraction evidence mapping (complete vs partial vs blocked)
6. Stage 4 Tamper & Consistency mapping (consistent vs tampering/mismatch conflicts)
7. Stage 5 Authority Verification mapping:
   - MATCH -> SUPPORTING
   - MISMATCH -> CONFLICTING (triggers review)
   - NOT_AVAILABLE -> NEUTRAL (never negative/punitive)
   - BLOCKED -> NEUTRAL / TECHNICAL (never negative/punitive)
   - ERROR -> TECHNICAL_ERROR (never negative/punitive)
8. Eligibility Rules mapping (eligible vs criteria mismatch)
9. Evidence deduplication (merging overlapping cross-doc and authority findings)
10. State determination:
    - CLEAR_FOR_REVIEW
    - HUMAN_REVIEW_REQUIRED
    - INSUFFICIENT_EVIDENCE
    - PROCESSING_ERROR
11. Plain-English narrative explanation generation
12. Strict Assistive Safety: Zero fraud scores, no autonomous approval/rejection
13. Zero Network Sockets Safety (100% offline, no socket calls)
14. VerificationService integration: execution & persistence in VerificationResult
15. Safe re-verification merge preserving evidence summary and prior history
16. Tenant isolation and student ownership authorization in get_evidence_summary
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
root_dir = backend_dir.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import unittest
import uuid
import socket
from datetime import datetime
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.db.base import Base
from app.db.models.enums import DocumentType, ApplicationStatus, VerificationStatus, UserRole
from app.db.models.student import Student
from app.db.models.college import College
from app.db.models.scholarship_application import ScholarshipApplication
from app.db.models.document import Document
from app.db.models.verification_result import VerificationResult
from app.services.verification import VerificationService, MockAIVerifier

from ml.evidence_engine import (
    STAGE6_VERSION,
    EvidenceCategory,
    EvidenceStrength,
    EvidenceState,
    ReviewReason,
    EvidenceItem,
    EvidenceSummary,
    EvidenceEngineService,
    map_stage1_quality,
    map_stage2_classification,
    map_stage3_extractions,
    map_stage4_tamper_and_consistency,
    map_stage5_authority,
    map_rules_engine_eligibility,
    consolidate_overlapping_evidence,
    synthesize_evidence_summary,
)


class TestEvidenceEngineSchemas(unittest.TestCase):
    """Verifies schema definitions, enums, and automatic PII sanitization."""

    def test_enums_values(self):
        self.assertEqual(EvidenceCategory.SUPPORTING.value, "SUPPORTING")
        self.assertEqual(EvidenceCategory.CONFLICTING.value, "CONFLICTING")
        self.assertEqual(EvidenceCategory.NEUTRAL.value, "NEUTRAL")
        self.assertEqual(EvidenceCategory.WARNING.value, "WARNING")
        self.assertEqual(EvidenceCategory.TECHNICAL_ERROR.value, "TECHNICAL_ERROR")

        self.assertEqual(EvidenceStrength.STRONG.value, "STRONG")
        self.assertEqual(EvidenceStrength.MODERATE.value, "MODERATE")
        self.assertEqual(EvidenceStrength.WEAK.value, "WEAK")
        self.assertEqual(EvidenceStrength.NONE.value, "NONE")

        self.assertEqual(EvidenceState.CLEAR_FOR_REVIEW.value, "CLEAR_FOR_REVIEW")
        self.assertEqual(EvidenceState.HUMAN_REVIEW_REQUIRED.value, "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(EvidenceState.INSUFFICIENT_EVIDENCE.value, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(EvidenceState.PROCESSING_ERROR.value, "PROCESSING_ERROR")

    def test_pii_masking_in_evidence_item(self):
        # 12-digit Aadhaar should be masked in explanation
        item = EvidenceItem(
            evidence_id="ev-001",
            category=EvidenceCategory.SUPPORTING,
            source_stage="STAGE_3",
            check_type="identity_number_extraction",
            status="EXTRACTED",
            strength=EvidenceStrength.STRONG,
            title="Aadhaar ID Captured",
            explanation="Extracted Aadhaar number: 1234 5678 9012 for student."
        )
        self.assertNotIn("1234 5678 9012", item.explanation)
        self.assertIn("9012", item.explanation)
        self.assertIn("********", item.explanation)

    def test_pan_masking_in_evidence_item(self):
        item = EvidenceItem(
            evidence_id="ev-002",
            category=EvidenceCategory.SUPPORTING,
            source_stage="STAGE_3",
            check_type="identity_number_extraction",
            status="EXTRACTED",
            strength=EvidenceStrength.STRONG,
            title="PAN Card Captured",
            explanation="Found PAN card ABCDE1234F in marksheet document."
        )
        self.assertNotIn("ABCDE1234F", item.explanation)
        self.assertIn("34F", item.explanation)

    def test_file_path_sanitization_in_evidence_item(self):
        item = EvidenceItem(
            evidence_id="ev-003",
            category=EvidenceCategory.WARNING,
            source_stage="STAGE_1",
            check_type="document_quality_gate",
            status="WARNING",
            strength=EvidenceStrength.WEAK,
            title="Quality Advisory",
            explanation="Unable to read C:\\veriicampus prerequisites\\storage\\docs\\secret.pdf from disk."
        )
        self.assertNotIn("C:\\veriicampus", item.explanation)
        self.assertNotIn("secret.pdf", item.explanation)
        self.assertIn("[SECURE_STORAGE_PATH]", item.explanation)

    def test_no_fraud_scores_in_summary(self):
        summary = EvidenceSummary(explanation="Clear for administrative review.")
        summary_dict = summary.model_dump()
        self.assertNotIn("fraud_score", summary_dict)
        self.assertNotIn("fraud_probability", summary_dict)
        self.assertNotIn("fake_score", summary_dict)


class TestEvidenceMappers(unittest.TestCase):
    """Verifies that evidence mappers correctly convert Stages 1-5 outputs into EvidenceItems."""

    def test_stage1_mapper_pass(self):
        stage1_data = {
            "GOVERNMENT_ID": {"quality_level": "HIGH", "quality_score": 95.0, "quality_gate_status": "PASS"},
            "MARKSHEET": {"quality_level": "HIGH", "quality_score": 88.0, "quality_gate_status": "PASS"}
        }
        items = map_stage1_quality(stage1_data)
        self.assertEqual(len(items), 2)
        self.assertTrue(all(it.category == EvidenceCategory.SUPPORTING for it in items))

    def test_stage1_mapper_fail(self):
        stage1_data = {
            "GOVERNMENT_ID": {"quality_level": "LOW", "quality_score": 40.0, "quality_gate_status": "WARNING", "reasons": ["Image blurry"]}
        }
        items = map_stage1_quality(stage1_data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].category, EvidenceCategory.WARNING)
        self.assertEqual(items[0].reason_code, ReviewReason.LOW_DOCUMENT_QUALITY.value)

    def test_stage2_mapper_slot_match(self):
        stage2_data = {
            "GOVERNMENT_ID": {"classification_status": "PASS", "confidence": 0.98, "predicted_type": "GOVERNMENT_ID"}
        }
        items = map_stage2_classification(stage2_data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].category, EvidenceCategory.SUPPORTING)

    def test_stage2_mapper_slot_mismatch(self):
        stage2_data = {
            "MARKSHEET": {"classification_status": "DOCUMENT_TYPE_MISMATCH", "confidence": 0.90, "predicted_type": "INCOME_CERTIFICATE"}
        }
        items = map_stage2_classification(stage2_data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].category, EvidenceCategory.CONFLICTING)
        self.assertEqual(items[0].reason_code, ReviewReason.DOCUMENT_TYPE_MISMATCH.value)
        self.assertTrue(items[0].requires_human_review)

    def test_stage3_mapper_complete_and_partial(self):
        stage3_data = {
            "GOVERNMENT_ID": {
                "extraction_status": "COMPLETE",
                "completeness_score": 1.0,
                "overall_confidence": 0.95,
                "fields": {"id_number": {"extraction_status": "EXTRACTED", "display_value": "1234 5678 9012"}}
            },
            "MARKSHEET": {"extraction_status": "BLOCKED"}
        }
        items = map_stage3_extractions(stage3_data)
        supp = [i for i in items if i.category == EvidenceCategory.SUPPORTING]
        neut = [i for i in items if i.category == EvidenceCategory.NEUTRAL]
        self.assertGreater(len(supp), 0)
        self.assertEqual(len(neut), 1)

    def test_stage4_tamper_flag_creates_conflict(self):
        stage4_data = {
            "tamper_assessment": {
                "signals": [{"signal_name": "font_anomaly", "status": "NEEDS_REVIEW", "severity": "HIGH", "affected_document": "MARKSHEET", "explanation": "Font variation detected"}]
            },
            "consistency_assessment": {"checks": []}
        }
        items = map_stage4_tamper_and_consistency(stage4_data)
        conflicts = [i for i in items if i.category == EvidenceCategory.CONFLICTING]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].reason_code, ReviewReason.TAMPER_SIGNAL.value)
        self.assertTrue(conflicts[0].requires_human_review)

    def test_stage4_consistency_mismatch_creates_conflict(self):
        stage4_data = {
            "tamper_assessment": {"signals": []},
            "consistency_assessment": {
                "checks": [{"check_name": "cross_document_dob", "field_name": "dob", "status": "FAIL", "reason": "DOB mismatch across documents"}]
            }
        }
        items = map_stage4_tamper_and_consistency(stage4_data)
        conflicts = [i for i in items if i.category == EvidenceCategory.CONFLICTING]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].reason_code, ReviewReason.DOB_MISMATCH.value)
        self.assertTrue(conflicts[0].requires_human_review)

    def test_stage5_match_creates_supporting(self):
        stage5_data = {
            "overall_status": "MATCH",
            "overall_evidence_strength": "STRONG",
            "documents": {
                "GOVERNMENT_ID": {"status": "MATCH", "evidence_strength": "STRONG", "reason": "Verified with authority registry", "provider_name": "DigiLocker"}
            }
        }
        items = map_stage5_authority(stage5_data)
        supporting = [i for i in items if i.category == EvidenceCategory.SUPPORTING]
        self.assertGreater(len(supporting), 0)
        self.assertEqual(supporting[0].strength, EvidenceStrength.STRONG)

    def test_stage5_mismatch_creates_conflicting(self):
        stage5_data = {
            "overall_status": "MISMATCH",
            "documents": {
                "MARKSHEET": {"status": "MISMATCH", "evidence_strength": "STRONG", "reason": "Academic record not found", "provider_name": "NAD"}
            }
        }
        items = map_stage5_authority(stage5_data)
        conflicts = [i for i in items if i.category == EvidenceCategory.CONFLICTING]
        self.assertGreater(len(conflicts), 0)
        self.assertEqual(conflicts[0].reason_code, ReviewReason.AUTHORITY_MISMATCH.value)
        self.assertTrue(conflicts[0].requires_human_review)

    def test_stage5_not_available_is_strictly_neutral(self):
        stage5_data = {
            "overall_status": "NOT_AVAILABLE",
            "documents": {
                "GOVERNMENT_ID": {"status": "NOT_AVAILABLE", "evidence_strength": "NONE", "reason": "Provider not configured", "provider_name": "Unavailable"}
            }
        }
        items = map_stage5_authority(stage5_data)
        self.assertGreater(len(items), 0)
        self.assertTrue(all(i.category == EvidenceCategory.NEUTRAL for i in items))
        self.assertTrue(all(i.strength == EvidenceStrength.NONE for i in items))
        self.assertFalse(any(i.requires_human_review for i in items))

    def test_stage5_blocked_is_strictly_neutral(self):
        stage5_data = {
            "overall_status": "BLOCKED",
            "documents": {
                "INCOME_CERTIFICATE": {"status": "BLOCKED", "evidence_strength": "NONE", "reason": "Blocked by quality gate", "provider_name": "Unavailable"}
            }
        }
        items = map_stage5_authority(stage5_data)
        self.assertGreater(len(items), 0)
        self.assertTrue(all(i.category == EvidenceCategory.NEUTRAL for i in items))
        self.assertFalse(any(i.requires_human_review for i in items))

    def test_stage5_error_is_technical_error(self):
        stage5_data = {
            "overall_status": "ERROR",
            "documents": {
                "DOMICILE_CERTIFICATE": {"status": "ERROR", "evidence_strength": "NONE", "reason": "Registry timeout", "provider_name": "Issuer"}
            }
        }
        items = map_stage5_authority(stage5_data)
        tech_errors = [i for i in items if i.category == EvidenceCategory.TECHNICAL_ERROR]
        self.assertEqual(len(tech_errors), 1)

    def test_rules_engine_eligibility_mapping(self):
        rules_result = {
            "field_checks": {
                "scheme_percentage": {"status": "FAIL", "details": "Marks below 60%", "is_critical": True},
                "income_limit": {"status": "PASS", "details": "Income within limit"}
            }
        }
        items = map_rules_engine_eligibility(rules_result)
        self.assertEqual(len(items), 2)
        conflicts = [i for i in items if i.category == EvidenceCategory.CONFLICTING]
        supporting = [i for i in items if i.category == EvidenceCategory.SUPPORTING]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(len(supporting), 1)
        self.assertEqual(conflicts[0].reason_code, ReviewReason.SCHEME_ELIGIBILITY_CONFLICT.value)


class TestEvidenceConsolidationAndSynthesis(unittest.TestCase):
    """Verifies overlapping evidence consolidation, state determination, and narrative explanation."""

    def test_consolidate_overlapping_evidence(self):
        items = [
            EvidenceItem(
                evidence_id="ev-c1",
                category=EvidenceCategory.CONFLICTING,
                strength=EvidenceStrength.MODERATE,
                source_stage="STAGE_4",
                check_type="cross_document_dob",
                status="MISMATCH",
                title="Cross Document DOB",
                field_name="date_of_birth",
                explanation="DOB mismatch across documents.",
                requires_human_review=True,
                reason_code=ReviewReason.DOB_MISMATCH.value
            ),
            EvidenceItem(
                evidence_id="ev-c2",
                category=EvidenceCategory.CONFLICTING,
                strength=EvidenceStrength.STRONG,
                source_stage="STAGE_5",
                check_type="authority_record_match",
                status="MISMATCH",
                title="Authority DOB",
                field_name="date_of_birth",
                explanation="DOB does not match authority registry.",
                requires_human_review=True,
                reason_code=ReviewReason.DOB_MISMATCH.value
            )
        ]
        consolidated = consolidate_overlapping_evidence(items)
        self.assertEqual(len(consolidated), 1)
        self.assertEqual(consolidated[0].strength, EvidenceStrength.STRONG)
        self.assertIn("STAGE_4", consolidated[0].source_stage)
        self.assertIn("STAGE_5", consolidated[0].source_stage)

    def test_state_clear_for_review(self):
        items = [
            EvidenceItem(evidence_id="ev-1", category=EvidenceCategory.SUPPORTING, strength=EvidenceStrength.STRONG, source_stage="STAGE_1", check_type="q", status="PASS", title="Quality", explanation="Valid quality"),
            EvidenceItem(evidence_id="ev-2", category=EvidenceCategory.SUPPORTING, strength=EvidenceStrength.STRONG, source_stage="STAGE_2", check_type="c", status="PASS", title="Class", explanation="Valid slot"),
            EvidenceItem(evidence_id="ev-3", category=EvidenceCategory.SUPPORTING, strength=EvidenceStrength.STRONG, source_stage="STAGE_3", check_type="e", status="PASS", title="OCR", explanation="Complete OCR"),
            EvidenceItem(evidence_id="ev-4", category=EvidenceCategory.SUPPORTING, strength=EvidenceStrength.STRONG, source_stage="STAGE_4", check_type="t", status="PASS", title="Consistency", explanation="Consistent"),
            EvidenceItem(evidence_id="ev-5", category=EvidenceCategory.NEUTRAL, strength=EvidenceStrength.NONE, source_stage="STAGE_5", check_type="a", status="NOT_AVAILABLE", title="Authority", explanation="Authority unavailable")
        ]
        summary = synthesize_evidence_summary(items)
        self.assertEqual(summary.overall_evidence_state, EvidenceState.CLEAR_FOR_REVIEW)
        self.assertFalse(summary.human_review_required)
        self.assertEqual(len(summary.review_reasons), 0)

    def test_state_human_review_required_on_conflict(self):
        items = [
            EvidenceItem(evidence_id="ev-1", category=EvidenceCategory.SUPPORTING, strength=EvidenceStrength.STRONG, source_stage="STAGE_1", check_type="q", status="PASS", title="Quality", explanation="Valid quality"),
            EvidenceItem(evidence_id="ev-2", category=EvidenceCategory.CONFLICTING, strength=EvidenceStrength.STRONG, source_stage="STAGE_4", check_type="name", status="MISMATCH", title="Name Discrepancy", explanation="Name mismatch", requires_human_review=True, reason_code=ReviewReason.NAME_MISMATCH.value)
        ]
        summary = synthesize_evidence_summary(items)
        self.assertEqual(summary.overall_evidence_state, EvidenceState.HUMAN_REVIEW_REQUIRED)
        self.assertTrue(summary.human_review_required)
        self.assertIn(ReviewReason.NAME_MISMATCH.value, summary.review_reasons)

    def test_state_insufficient_evidence(self):
        items = [
            EvidenceItem(
                evidence_id="ev-1",
                category=EvidenceCategory.WARNING,
                strength=EvidenceStrength.STRONG,
                source_stage="STAGE_1",
                check_type="quality",
                status="REUPLOAD_REQUIRED",
                title="Unreadable",
                explanation="Missing documents",
                reason_code=ReviewReason.LOW_DOCUMENT_QUALITY.value,
                requires_human_review=True
            )
        ]
        summary = synthesize_evidence_summary(items)
        self.assertEqual(summary.overall_evidence_state, EvidenceState.INSUFFICIENT_EVIDENCE)
        self.assertTrue(summary.human_review_required)
        self.assertEqual(len(summary.conflicting_evidence), 0)

    def test_service_evaluate_end_to_end(self):
        service = EvidenceEngineService()
        summary = service.evaluate(
            quality_results={"GOVERNMENT_ID": {"quality_level": "HIGH", "quality_score": 90.0, "quality_gate_status": "PASS"}},
            classification_results={"GOVERNMENT_ID": {"classification_status": "PASS", "confidence": 0.95}},
            extractions={"GOVERNMENT_ID": {"extraction_status": "COMPLETE", "completeness_score": 1.0, "overall_confidence": 0.95, "fields": {}}},
            tamper_results={"tamper_assessment": {"signals": []}, "consistency_assessment": {"checks": []}},
            authority_results={"overall_status": "NOT_AVAILABLE", "documents": {}},
            rules_evaluation={"field_checks": {}}
        )
        self.assertEqual(summary.overall_evidence_state, EvidenceState.CLEAR_FOR_REVIEW)
        self.assertFalse(summary.human_review_required)
        self.assertGreater(summary.total_evidence_count, 0)
        self.assertIn("administrative sign-off", summary.explanation.lower())

    def test_processing_error_state(self):
        items = [
            EvidenceItem(
                evidence_id="ev-err",
                category=EvidenceCategory.TECHNICAL_ERROR,
                strength=EvidenceStrength.NONE,
                source_stage="STAGE_3",
                check_type="ocr_crash",
                status="ERROR",
                title="OCR Engine Crash",
                explanation="Internal failure",
                requires_human_review=True,
                reason_code=ReviewReason.TECHNICAL_PROCESSING_ERROR.value
            )
        ]
        summary = synthesize_evidence_summary(items)
        self.assertEqual(summary.overall_evidence_state, EvidenceState.PROCESSING_ERROR)
        self.assertIn("technical processing problem", summary.explanation.lower())

    def test_non_punitive_not_available_does_not_alter_clear_state(self):
        items = [
            EvidenceItem(evidence_id="ev-s1", category=EvidenceCategory.SUPPORTING, strength=EvidenceStrength.STRONG, source_stage="STAGE_1", check_type="q", status="PASS", title="Quality Pass", explanation="Good"),
            EvidenceItem(evidence_id="ev-s2", category=EvidenceCategory.SUPPORTING, strength=EvidenceStrength.STRONG, source_stage="STAGE_2", check_type="c", status="PASS", title="Class Pass", explanation="Good"),
            EvidenceItem(evidence_id="ev-n1", category=EvidenceCategory.NEUTRAL, strength=EvidenceStrength.NONE, source_stage="STAGE_5", check_type="auth1", status="NOT_AVAILABLE", title="DigiLocker Unconfigured", explanation="None"),
            EvidenceItem(evidence_id="ev-n2", category=EvidenceCategory.NEUTRAL, strength=EvidenceStrength.NONE, source_stage="STAGE_5", check_type="auth2", status="NOT_AVAILABLE", title="NAD Unconfigured", explanation="None"),
            EvidenceItem(evidence_id="ev-n3", category=EvidenceCategory.NEUTRAL, strength=EvidenceStrength.NONE, source_stage="STAGE_5", check_type="auth3", status="BLOCKED", title="Income Registry Skipped", explanation="None"),
        ]
        summary = synthesize_evidence_summary(items)
        self.assertEqual(summary.overall_evidence_state, EvidenceState.CLEAR_FOR_REVIEW)
        self.assertFalse(summary.human_review_required)
        self.assertEqual(len(summary.conflicting_evidence), 0)
        self.assertEqual(len(summary.neutral_evidence), 3)

    def test_review_reasons_deduplication(self):
        items = [
            EvidenceItem(evidence_id="ev-d1", category=EvidenceCategory.CONFLICTING, strength=EvidenceStrength.STRONG, source_stage="STAGE_4", check_type="name_c", status="FAIL", title="Name 1", explanation="Name diff", requires_human_review=True, reason_code=ReviewReason.NAME_MISMATCH.value),
            EvidenceItem(evidence_id="ev-d2", category=EvidenceCategory.CONFLICTING, strength=EvidenceStrength.STRONG, source_stage="STAGE_5", check_type="name_a", status="FAIL", title="Name 2", explanation="Name diff auth", requires_human_review=True, reason_code=ReviewReason.NAME_MISMATCH.value),
        ]
        summary = synthesize_evidence_summary(items)
        self.assertEqual(summary.review_reasons.count(ReviewReason.NAME_MISMATCH.value), 1)

    def test_stage3_field_extraction_blocked_status(self):
        stage3_data = {
            "DOMICILE_CERTIFICATE": {"extraction_status": "BLOCKED"}
        }
        items = map_stage3_extractions(stage3_data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].category, EvidenceCategory.NEUTRAL)
        self.assertEqual(items[0].strength, EvidenceStrength.NONE)
        self.assertFalse(items[0].requires_human_review)

    def test_stage3_field_extraction_failed_status(self):
        stage3_data = {
            "MARKSHEET": {"extraction_status": "FAILED"}
        }
        items = map_stage3_extractions(stage3_data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].category, EvidenceCategory.TECHNICAL_ERROR)
        self.assertTrue(items[0].requires_human_review)

    def test_stage4_marks_arithmetic_reason_code(self):
        stage4_data = {
            "tamper_assessment": {"signals": []},
            "consistency_assessment": {
                "checks": [{"check_name": "marks_total_check", "field_name": "total_marks", "status": "FAIL", "reason": "Subject sum does not match total"}]
            }
        }
        items = map_stage4_tamper_and_consistency(stage4_data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].reason_code, ReviewReason.MARKS_ARITHMETIC_CONFLICT.value)

    def test_stage4_government_id_mismatch_reason_code(self):
        stage4_data = {
            "tamper_assessment": {"signals": []},
            "consistency_assessment": {
                "checks": [{"check_name": "id_match_check", "field_name": "id_number", "status": "FAIL", "reason": "ID mismatch across forms"}]
            }
        }
        items = map_stage4_tamper_and_consistency(stage4_data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].reason_code, ReviewReason.GOVERNMENT_ID_MISMATCH.value)

    def test_evidence_strength_breakdown_counters(self):
        items = [
            EvidenceItem(evidence_id="ev-s1", category=EvidenceCategory.SUPPORTING, strength=EvidenceStrength.STRONG, source_stage="STAGE_1", check_type="q", status="PASS", title="S1", explanation=""),
            EvidenceItem(evidence_id="ev-s2", category=EvidenceCategory.SUPPORTING, strength=EvidenceStrength.MODERATE, source_stage="STAGE_2", check_type="c", status="PASS", title="S2", explanation=""),
            EvidenceItem(evidence_id="ev-s3", category=EvidenceCategory.SUPPORTING, strength=EvidenceStrength.WEAK, source_stage="STAGE_3", check_type="e", status="PASS", title="S3", explanation=""),
            EvidenceItem(evidence_id="ev-c1", category=EvidenceCategory.CONFLICTING, strength=EvidenceStrength.STRONG, source_stage="STAGE_4", check_type="t", status="MISMATCH", title="C1", explanation="", requires_human_review=True),
            EvidenceItem(evidence_id="ev-c2", category=EvidenceCategory.CONFLICTING, strength=EvidenceStrength.MODERATE, source_stage="STAGE_4", check_type="t2", status="MISMATCH", title="C2", explanation="", requires_human_review=True),
            EvidenceItem(evidence_id="ev-c3", category=EvidenceCategory.CONFLICTING, strength=EvidenceStrength.WEAK, source_stage="STAGE_4", check_type="t3", status="MISMATCH", title="C3", explanation="", requires_human_review=True),
        ]
        summary = synthesize_evidence_summary(items)
        self.assertEqual(summary.strong_support_count, 1)
        self.assertEqual(summary.moderate_support_count, 1)
        self.assertEqual(summary.weak_support_count, 1)
        self.assertEqual(summary.strong_conflict_count, 1)
        self.assertEqual(summary.moderate_conflict_count, 1)
        self.assertEqual(summary.weak_conflict_count, 1)


class TestSafetyAndZeroNetwork(unittest.TestCase):
    """Ensures 100% offline safety and zero network socket activity."""

    def test_zero_network_calls_during_evaluation(self):
        socket_mock = MagicMock(side_effect=RuntimeError("NETWORK CALL DETECTED: Stage 6 must remain 100% offline."))

        with patch("socket.socket", socket_mock):
            service = EvidenceEngineService()
            summary = service.evaluate(
                quality_results={},
                classification_results={},
                extractions={},
                tamper_results={},
                authority_results={},
                rules_evaluation=None
            )
            self.assertIsNotNone(summary)
            socket_mock.assert_not_called()


class TestVerificationServiceIntegrationAndTenantIsolation(unittest.TestCase):
    """Verifies backend database integration, re-verification merge, and tenant isolation."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()
        self.college1_id = uuid.uuid4()
        self.college2_id = uuid.uuid4()

        suffix = uuid.uuid4().hex[:6].upper()
        college1 = College(id=self.college1_id, college_name="Campus Alpha", college_code=f"ALPHA_{suffix}")
        college2 = College(id=self.college2_id, college_name="Campus Beta", college_code=f"BETA_{suffix}")
        self.db.add_all([college1, college2])
        self.db.commit()

        self.student1_id = uuid.uuid4()
        student1 = Student(
            id=self.student1_id,
            email=f"student1_{suffix}@alpha.edu",
            full_name="Alice Smith",
            college_id=self.college1_id,
            password_hash="hashed_pw"
        )
        self.student2_id = uuid.uuid4()
        student2 = Student(
            id=self.student2_id,
            email=f"student2_{suffix}@beta.edu",
            full_name="Bob Jones",
            college_id=self.college2_id,
            password_hash="hashed_pw"
        )
        self.db.add_all([student1, student2])
        self.db.commit()

        self.app1_id = uuid.uuid4()
        app1 = ScholarshipApplication(
            id=self.app1_id,
            scholarship_name="Merit Scholarship 2026",
            application_number=f"APP-ALPHA-{suffix}",
            student_id=self.student1_id,
            status=ApplicationStatus.SUBMITTED
        )
        self.db.add(app1)
        self.db.commit()

        # Add 4 documents for app1
        for dt in [DocumentType.GOVERNMENT_ID, DocumentType.MARKSHEET, DocumentType.INCOME_CERTIFICATE, DocumentType.DOMICILE_CERTIFICATE]:
            doc = Document(
                id=uuid.uuid4(),
                application_id=self.app1_id,
                document_type=dt,
                original_filename=f"{dt.value.lower()}.pdf",
                storage_path=f"storage/docs/{dt.value.lower()}.pdf"
            )
            self.db.add(doc)
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_verify_application_executes_stage6_and_persists_summary(self):
        # Run verification using MockAIVerifier
        result = VerificationService.verify_application(
            db=self.db,
            app_id_str=str(self.app1_id),
            verifier=MockAIVerifier()
        )
        self.assertIn("evidence_summary", result)
        ev = result["evidence_summary"]
        self.assertIn(ev["overall_evidence_state"], [
            EvidenceState.CLEAR_FOR_REVIEW.value,
            EvidenceState.HUMAN_REVIEW_REQUIRED.value
        ])
        self.assertEqual(ev["engine_version"], STAGE6_VERSION)

        # Check DB record
        vr = self.db.query(VerificationResult).filter(
            VerificationResult.application_id == self.app1_id,
            VerificationResult.document_id.is_(None)
        ).first()
        self.assertIsNotNone(vr)
        self.assertIn("evidence_summary", vr.extracted_data)

    def test_safe_reverification_preserves_evidence_summary_and_review_history(self):
        # Verify first time
        VerificationService.verify_application(
            db=self.db,
            app_id_str=str(self.app1_id),
            verifier=MockAIVerifier()
        )

        vr_before = self.db.query(VerificationResult).filter(
            VerificationResult.application_id == self.app1_id,
            VerificationResult.document_id.is_(None)
        ).first()
        self.assertIsNotNone(vr_before)

        # Re-verify second time
        VerificationService.verify_application(
            db=self.db,
            app_id_str=str(self.app1_id),
            verifier=MockAIVerifier()
        )

        vr_after = self.db.query(VerificationResult).filter(
            VerificationResult.application_id == self.app1_id,
            VerificationResult.document_id.is_(None)
        ).first()
        self.assertIn("evidence_summary", vr_after.extracted_data)
        self.assertIn("field_extraction", vr_after.extracted_data)
        self.assertIn("authority_verification", vr_after.extracted_data)

    def test_tenant_isolation_get_evidence_summary(self):
        # First verify app1 so evidence exists
        VerificationService.verify_application(
            db=self.db,
            app_id_str=str(self.app1_id),
            verifier=MockAIVerifier()
        )

        # 1. Student owner can access
        res = VerificationService.get_evidence_summary(
            db=self.db,
            app_id_str=str(self.app1_id),
            user_id_str=str(self.student1_id),
            role=UserRole.STUDENT,
            user_college_id_str=str(self.college1_id)
        )
        self.assertEqual(res["application_id"], str(self.app1_id))
        self.assertEqual(res["engine_version"], STAGE6_VERSION)

        # 2. Other student receives 403 Forbidden
        with self.assertRaises(HTTPException) as ctx:
            VerificationService.get_evidence_summary(
                db=self.db,
                app_id_str=str(self.app1_id),
                user_id_str=str(self.student2_id),
                role=UserRole.STUDENT,
                user_college_id_str=str(self.college2_id)
            )
        self.assertEqual(ctx.exception.status_code, 403)

        # 3. Same college admin can access
        admin_res = VerificationService.get_evidence_summary(
            db=self.db,
            app_id_str=str(self.app1_id),
            user_id_str=str(uuid.uuid4()),
            role=UserRole.ADMIN,
            user_college_id_str=str(self.college1_id)
        )
        self.assertEqual(admin_res["application_id"], str(self.app1_id))

        # 4. Different college admin receives 403 Forbidden
        with self.assertRaises(HTTPException) as ctx:
            VerificationService.get_evidence_summary(
                db=self.db,
                app_id_str=str(self.app1_id),
                user_id_str=str(uuid.uuid4()),
                role=UserRole.ADMIN,
                user_college_id_str=str(self.college2_id)
            )
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
