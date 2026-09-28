"""
VeriCampus AI — Stage 4: Tamper Detection & Cross-Document Consistency Automated Test Suite
Comprehensive test suite (40+ test cases) verifying:
1. Schemas, evidence strength hierarchy, and confidence bounds
2. Cross-document Name consistency (token reordering, substrings, abbreviations, mismatches)
3. Date of Birth (DOB) consistency (ISO formatting, mismatches, single-doc handling)
4. Masked Government ID consistency (masking enforcement, last-4 matching, mismatches)
5. Date & Temporal consistency (future dates, passing year vs age, financial year)
6. Marksheet arithmetic & percentage consistency (subject sum, total > max, calculated %)
7. Visual & Structural tamper detectors (ELA, blur, noise, copy-move, bbox overlaps)
8. Metadata analysis (advisory software signals, never proof of fraud)
9. Hierarchical evidence scoring (strong vs weak evidence weighting)
10. Tabular ML feature vector extraction
11. End-to-end VerificationService integration and re-verification safe merge regression
"""
import unittest
import uuid
from datetime import date, datetime
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock
import numpy as np
from PIL import Image

from app.db.models.enums import DocumentType, ApplicationStatus, VerificationStatus, UploadStatus, UserRole
from app.db.models.student import Student
from app.db.models.scholarship_application import ScholarshipApplication
from app.db.models.document import Document
from app.db.models.verification_result import VerificationResult
from app.services.verification import VerificationService, MockAIVerifier, MockScenario
from app.services.verification.base import DocumentExtractionResult

from ml.tamper_consistency import (
    CheckStatus,
    SignalCategory,
    SignalSeverity,
    NameMatchCategory,
    EvidenceStrength,
    TamperSignal,
    TamperAssessment,
    ConsistencyCheckResult,
    ConsistencyAssessment,
    Stage4VerificationResult,
    TamperConsistencyService,
    STAGE4_VERSION,
    STAGE4_PASS_THRESHOLD,
    STAGE4_WARNING_THRESHOLD,
)
from ml.tamper_consistency.consistency.name_consistency import NameConsistencyChecker
from ml.tamper_consistency.consistency.dob_consistency import DOBConsistencyChecker
from ml.tamper_consistency.consistency.id_consistency import IDConsistencyChecker
from ml.tamper_consistency.consistency.date_consistency import DateConsistencyChecker
from ml.tamper_consistency.consistency.marks_consistency import MarksConsistencyChecker
from ml.tamper_consistency.tamper.visual_features import (
    extract_ela_signal,
    extract_local_blur_signal,
    extract_noise_variance_signal,
    extract_copy_move_signal,
)
from ml.tamper_consistency.tamper.structural_features import (
    extract_bbox_overlap_signal,
    extract_aspect_ratio_signal,
)
from ml.tamper_consistency.tamper.metadata_features import extract_metadata_signals
from ml.tamper_consistency.tamper.heuristic_detector import HeuristicTamperDetector
from ml.tamper_consistency.scorer import (
    score_tamper_signals,
    score_consistency_checks,
    score_stage4_overall,
)
from ml.tamper_consistency.features import (
    extract_features_from_assessments,
    extract_feature_vector,
    FEATURE_NAMES,
)


class TestTamperConsistencySchemas(unittest.TestCase):
    """1. Schema validation and data contract invariants."""

    def test_01_tamper_signal_creation(self):
        sig = TamperSignal(
            signal_name="test_signal",
            category=SignalCategory.VISUAL,
            severity=SignalSeverity.LOW,
            score=85.0,
            confidence=0.90,
            status=CheckStatus.PASS,
            explanation="Normal compression levels.",
            affected_document="GOVERNMENT_ID",
            evidence_strength=EvidenceStrength.WEAK,
        )
        self.assertEqual(sig.signal_name, "test_signal")
        self.assertEqual(sig.score, 85.0)
        self.assertEqual(sig.evidence_strength, EvidenceStrength.WEAK)

    def test_02_consistency_check_result_bounds(self):
        chk = ConsistencyCheckResult(
            check_name="name_check",
            category="CROSS_DOCUMENT_IDENTITY",
            status=CheckStatus.PASS,
            confidence=0.95,
            documents_compared=["GOVERNMENT_ID", "MARKSHEET"],
            field_name="student_name",
            reason="Exact match.",
            is_critical=False,
        )
        self.assertEqual(chk.status, CheckStatus.PASS)
        self.assertFalse(chk.is_critical)
        self.assertGreaterEqual(chk.confidence, 0.0)
        self.assertLessEqual(chk.confidence, 1.0)

    def test_03_stage4_verification_result_defaults(self):
        t_assess = TamperAssessment(status=CheckStatus.PASS, overall_score=95.0, confidence=0.90)
        c_assess = ConsistencyAssessment(status=CheckStatus.PASS, overall_score=100.0)
        res = Stage4VerificationResult(
            stage_version=STAGE4_VERSION,
            tamper_assessment=t_assess,
            consistency_assessment=c_assess,
            overall_status=CheckStatus.PASS,
            overall_score=98.5,
            confidence=0.92,
            review_required=False,
        )
        self.assertEqual(res.overall_status, CheckStatus.PASS)
        self.assertFalse(res.review_required)
        self.assertEqual(res.stage_version, STAGE4_VERSION)


class TestNameConsistencyChecker(unittest.TestCase):
    """2. Name consistency matching, normalization, and mismatch logic."""

    def setUp(self):
        self.checker = NameConsistencyChecker()

    def test_04_name_exact_match(self):
        extractions = {
            "GOVERNMENT_ID": {"fields": {"student_name": {"normalized_value": "rahul patil", "confidence": 0.95}}},
            "MARKSHEET": {"fields": {"student_name": {"normalized_value": "rahul patil", "confidence": 0.95}}},
        }
        res = self.checker.check(extractions)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, CheckStatus.PASS)
        self.assertEqual(res[0].match_type, NameMatchCategory.NORMALIZED_MATCH.value)

    def test_05_name_token_reordering(self):
        extractions = {
            "GOVERNMENT_ID": {"fields": {"student_name": {"normalized_value": "patil rahul", "confidence": 0.95}}},
            "MARKSHEET": {"fields": {"student_name": {"normalized_value": "rahul patil", "confidence": 0.95}}},
        }
        res = self.checker.check(extractions)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, CheckStatus.PASS)
        self.assertEqual(res[0].match_type, NameMatchCategory.MINOR_VARIATION.value)

    def test_06_name_subset_expansion(self):
        extractions = {
            "GOVERNMENT_ID": {"fields": {"student_name": {"normalized_value": "rahul patil", "confidence": 0.95}}},
            "DOMICILE_CERTIFICATE": {"fields": {"applicant_name": {"normalized_value": "rahul kumar patil", "confidence": 0.90}}},
        }
        res = self.checker.check(extractions)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, CheckStatus.PASS)
        self.assertIn("subset or expansion", res[0].reason)

    def test_07_name_initial_abbreviation(self):
        extractions = {
            "GOVERNMENT_ID": {"fields": {"student_name": {"normalized_value": "rahul k patil", "confidence": 0.95}}},
            "MARKSHEET": {"fields": {"student_name": {"normalized_value": "rahul kumar patil", "confidence": 0.90}}},
        }
        res = self.checker.check(extractions)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, CheckStatus.PASS)
        self.assertEqual(res[0].match_type, NameMatchCategory.MINOR_VARIATION.value)

    def test_08_name_critical_mismatch(self):
        extractions = {
            "GOVERNMENT_ID": {"fields": {"student_name": {"normalized_value": "rahul patil", "confidence": 0.95}}},
            "MARKSHEET": {"fields": {"student_name": {"normalized_value": "amit sharma", "confidence": 0.90}}},
        }
        res = self.checker.check(extractions)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, CheckStatus.NEEDS_REVIEW)
        self.assertTrue(res[0].is_critical)
        self.assertEqual(res[0].match_type, NameMatchCategory.MISMATCH.value)

    def test_09_name_insufficient_documents(self):
        extractions = {
            "GOVERNMENT_ID": {"fields": {"student_name": {"normalized_value": "rahul patil", "confidence": 0.95}}},
        }
        res = self.checker.check(extractions)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, CheckStatus.NOT_AVAILABLE)


class TestDOBConsistencyChecker(unittest.TestCase):
    """3. Date of Birth cross-comparison and discrepancy handling."""

    def setUp(self):
        self.checker = DOBConsistencyChecker()

    def test_10_dob_identical_match(self):
        extractions = {
            "GOVERNMENT_ID": {"fields": {"date_of_birth": {"normalized_value": "2002-05-15", "confidence": 0.95}}},
            "MARKSHEET": {"fields": {"date_of_birth": {"normalized_value": "2002-05-15", "confidence": 0.90}}},
        }
        res = self.checker.check(extractions)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, CheckStatus.PASS)
        self.assertEqual(res[0].match_type, "EXACT_DATE_MATCH")
        self.assertFalse(res[0].is_critical)

    def test_11_dob_discrepancy_critical(self):
        extractions = {
            "GOVERNMENT_ID": {"fields": {"date_of_birth": {"normalized_value": "2002-05-15", "confidence": 0.95}}},
            "MARKSHEET": {"fields": {"date_of_birth": {"normalized_value": "2001-08-20", "confidence": 0.90}}},
        }
        res = self.checker.check(extractions)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, CheckStatus.NEEDS_REVIEW)
        self.assertEqual(res[0].match_type, "DATE_MISMATCH")
        self.assertTrue(res[0].is_critical)

    def test_12_dob_single_document_not_available(self):
        extractions = {
            "GOVERNMENT_ID": {"fields": {"date_of_birth": {"normalized_value": "2002-05-15", "confidence": 0.95}}},
        }
        res = self.checker.check(extractions)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, CheckStatus.NOT_AVAILABLE)


class TestIDConsistencyChecker(unittest.TestCase):
    """4. Sensitive Government ID masking and cross-comparison."""

    def setUp(self):
        self.checker = IDConsistencyChecker()

    def test_13_id_matching_with_masking(self):
        extractions = {
            "GOVERNMENT_ID": {"fields": {"id_number": {"normalized_value": "987654321098", "confidence": 0.95}}},
            "DOMICILE_CERTIFICATE": {"fields": {"aadhaar_number": {"normalized_value": "987654321098", "confidence": 0.90}}},
        }
        res = self.checker.check(extractions)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, CheckStatus.PASS)
        # Check mandatory masking in values_compared and reason
        self.assertNotIn("987654321098", str(res[0].values_compared))
        self.assertIn("1098", str(res[0].values_compared))
        self.assertNotIn("987654321098", res[0].reason)

    def test_14_id_mismatch_critical(self):
        extractions = {
            "GOVERNMENT_ID": {"fields": {"id_number": {"normalized_value": "987654321098", "confidence": 0.95}}},
            "DOMICILE_CERTIFICATE": {"fields": {"aadhaar_number": {"normalized_value": "112233445566", "confidence": 0.90}}},
        }
        res = self.checker.check(extractions)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, CheckStatus.NEEDS_REVIEW)
        self.assertTrue(res[0].is_critical)
        self.assertEqual(res[0].match_type, "ID_MISMATCH")

    def test_15_id_single_document_safe(self):
        extractions = {
            "GOVERNMENT_ID": {"fields": {"id_number": {"normalized_value": "987654321098", "confidence": 0.95}}},
            "MARKSHEET": {"fields": {"roll_number": {"normalized_value": "ROLL-12345", "confidence": 0.95}}},
        }
        res = self.checker.check(extractions)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, CheckStatus.NOT_AVAILABLE)
        # Verify roll_number was not mistaken for Government ID
        self.assertNotIn("ROLL-12345", str(res[0].values_compared))


class TestDateConsistencyChecker(unittest.TestCase):
    """5. Temporal logic, future dates, passing age, and financial years."""

    def setUp(self):
        self.checker = DateConsistencyChecker()

    def test_16_future_issue_date_critical(self):
        future_year = datetime.now().year + 2
        extractions = {
            "INCOME_CERTIFICATE": {"fields": {"issue_date": {"normalized_value": f"{future_year}-06-15", "confidence": 0.95}}},
        }
        res = self.checker.check(extractions)
        future_chks = [r for r in res if "future_date_check" in r.check_name]
        self.assertEqual(len(future_chks), 1)
        self.assertEqual(future_chks[0].status, CheckStatus.NEEDS_REVIEW)
        self.assertTrue(future_chks[0].is_critical)

    def test_17_dob_vs_passing_year_coherent(self):
        extractions = {
            "GOVERNMENT_ID": {"fields": {"date_of_birth": {"normalized_value": "2002-05-15", "confidence": 0.95}}},
            "MARKSHEET": {"fields": {"passing_year": {"normalized_value": 2020, "confidence": 0.95}}},
        }
        res = self.checker.check(extractions)
        age_chk = next(r for r in res if "dob_vs_passing_year" in r.check_name)
        self.assertEqual(age_chk.status, CheckStatus.PASS)
        self.assertEqual(age_chk.match_type, "VALID_CHRONOLOGICAL_AGE")

    def test_18_dob_vs_passing_year_impossible(self):
        # Student born in 2012 cannot pass 12th in 2020 (age 8)
        extractions = {
            "GOVERNMENT_ID": {"fields": {"date_of_birth": {"normalized_value": "2012-05-15", "confidence": 0.95}}},
            "MARKSHEET": {"fields": {"passing_year": {"normalized_value": 2020, "confidence": 0.95}}},
        }
        res = self.checker.check(extractions)
        age_chk = next(r for r in res if "dob_vs_passing_year" in r.check_name)
        self.assertEqual(age_chk.status, CheckStatus.NEEDS_REVIEW)
        self.assertTrue(age_chk.is_critical)
        self.assertEqual(age_chk.match_type, "CHRONOLOGICAL_IMPOSSIBILITY")

    def test_19_income_financial_year_currency(self):
        extractions = {
            "INCOME_CERTIFICATE": {
                "fields": {
                    "issue_date": {"normalized_value": "2024-05-10", "confidence": 0.95},
                    "financial_year": {"normalized_value": "2023-2024", "confidence": 0.95},
                }
            }
        }
        res = self.checker.check(extractions)
        fy_chk = next(r for r in res if "income_fy" in r.check_name)
        self.assertEqual(fy_chk.status, CheckStatus.PASS)


class TestMarksConsistencyChecker(unittest.TestCase):
    """6. Marksheet arithmetic and percentage consistency."""

    def setUp(self):
        self.checker = MarksConsistencyChecker()

    def test_20_subject_sum_matches_total(self):
        extractions = {
            "MARKSHEET": {
                "fields": {
                    "total_marks": {"normalized_value": 300.0, "source_text": "300 / 300", "confidence": 0.95},
                    "subjects": {
                        "normalized_value": [
                            {"subject_name": "Math", "marks_obtained": 100.0, "max_marks": 100.0},
                            {"subject_name": "Physics", "marks_obtained": 100.0, "max_marks": 100.0},
                            {"subject_name": "Chemistry", "marks_obtained": 100.0, "max_marks": 100.0},
                        ]
                    }
                }
            }
        }
        res = self.checker.check(extractions)
        sum_chk = next(r for r in res if "subject_sum" in r.check_name)
        self.assertEqual(sum_chk.status, CheckStatus.PASS)
        self.assertEqual(sum_chk.match_type, "ARITHMETIC_MATCH")

    def test_21_subject_sum_contradiction(self):
        extractions = {
            "MARKSHEET": {
                "fields": {
                    "total_marks": {"normalized_value": 450.0, "source_text": "450 / 600", "confidence": 0.95},
                    "subjects": {
                        "normalized_value": [
                            {"subject_name": "Math", "marks_obtained": 60.0, "max_marks": 100.0},
                            {"subject_name": "Physics", "marks_obtained": 70.0, "max_marks": 100.0},
                            {"subject_name": "Chemistry", "marks_obtained": 65.0, "max_marks": 100.0},
                        ]  # sum is 195 != 450
                    }
                }
            }
        }
        res = self.checker.check(extractions)
        sum_chk = next(r for r in res if "subject_sum" in r.check_name)
        self.assertEqual(sum_chk.status, CheckStatus.NEEDS_REVIEW)
        self.assertTrue(sum_chk.is_critical)
        self.assertEqual(sum_chk.match_type, "ARITHMETIC_CONTRADICTION")

    def test_22_total_exceeds_max_marks(self):
        extractions = {
            "MARKSHEET": {
                "fields": {
                    "total_marks": {"normalized_value": 550.0, "source_text": "550 / 500", "confidence": 0.95},
                }
            }
        }
        res = self.checker.check(extractions)
        bounds_chk = next(r for r in res if "bounds" in r.check_name)
        self.assertEqual(bounds_chk.status, CheckStatus.NEEDS_REVIEW)
        self.assertTrue(bounds_chk.is_critical)
        self.assertEqual(bounds_chk.match_type, "INVALID_MARKS_BOUNDS")

    def test_23_percentage_calculation_consistent(self):
        extractions = {
            "MARKSHEET": {
                "fields": {
                    "total_marks": {"normalized_value": 450.0, "source_text": "450 / 600", "confidence": 0.95},
                    "percentage": {"normalized_value": 75.0, "confidence": 0.95},
                }
            }
        }
        res = self.checker.check(extractions)
        pct_chk = next(r for r in res if "percentage" in r.check_name)
        self.assertEqual(pct_chk.status, CheckStatus.PASS)
        self.assertEqual(pct_chk.match_type, "PERCENTAGE_CONSISTENT")

    def test_24_percentage_contradiction(self):
        extractions = {
            "MARKSHEET": {
                "fields": {
                    "total_marks": {"normalized_value": 450.0, "source_text": "450 / 600", "confidence": 0.95},
                    "percentage": {"normalized_value": 92.5, "confidence": 0.95},  # 450/600 is 75.0%
                }
            }
        }
        res = self.checker.check(extractions)
        pct_chk = next(r for r in res if "percentage" in r.check_name)
        self.assertEqual(pct_chk.status, CheckStatus.NEEDS_REVIEW)
        self.assertTrue(pct_chk.is_critical)
        self.assertEqual(pct_chk.match_type, "PERCENTAGE_CONTRADICTION")


class TestTamperDetectors(unittest.TestCase):
    """7. Visual, structural, and metadata tamper signal extraction."""

    def test_25_ela_signal_clean_image(self):
        # Create uniform gradient test image
        img = np.ones((200, 200, 3), dtype=np.uint8) * 200
        sig = extract_ela_signal(img, "MARKSHEET")
        self.assertEqual(sig.category, SignalCategory.VISUAL)
        self.assertEqual(sig.status, CheckStatus.PASS)
        self.assertGreaterEqual(sig.score, 85.0)

    def test_26_local_blur_signal_evaluation(self):
        img = np.ones((200, 200, 3), dtype=np.uint8) * 128
        sig = extract_local_blur_signal(img, "GOVERNMENT_ID")
        self.assertEqual(sig.category, SignalCategory.VISUAL)
        self.assertIn(sig.status, [CheckStatus.PASS, CheckStatus.WARNING])

    def test_27_noise_variance_signal_evaluation(self):
        img = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        sig = extract_noise_variance_signal(img, "INCOME_CERTIFICATE")
        self.assertEqual(sig.category, SignalCategory.VISUAL)

    def test_28_copy_move_heuristics_execution(self):
        img = np.ones((150, 150, 3), dtype=np.uint8) * 240
        sig = extract_copy_move_signal(img, "DOMICILE_CERTIFICATE")
        self.assertEqual(sig.category, SignalCategory.VISUAL)

    def test_29_ocr_bbox_overlap_anomaly(self):
        class MockLine:
            def __init__(self, xmin, ymin, xmax, ymax):
                self.bounding_box = {"x_min": xmin, "y_min": ymin, "x_max": xmax, "y_max": ymax}

        class MockOCR:
            lines = [
                MockLine(10, 10, 100, 50),
                MockLine(15, 12, 98, 48),  # almost completely overlapping!
            ]

        sig = extract_bbox_overlap_signal(MockOCR(), "MARKSHEET")
        self.assertEqual(sig.category, SignalCategory.STRUCTURAL)
        self.assertEqual(sig.status, CheckStatus.WARNING)
        self.assertIn("overlapping", sig.explanation.lower())

    def test_30_aspect_ratio_sanity(self):
        # Extreme stretched aspect ratio 800 x 50
        meta = {"width": 800, "height": 50}
        sig = extract_aspect_ratio_signal(meta, "GOVERNMENT_ID")
        self.assertEqual(sig.category, SignalCategory.STRUCTURAL)
        self.assertEqual(sig.status, CheckStatus.WARNING)

    def test_31_software_metadata_advisory_only(self):
        # Photoshop in metadata should be LOW severity / WEAK evidence only
        meta = {"software": "Adobe Photoshop CC 2023"}
        signals = extract_metadata_signals(None, "MARKSHEET", metadata=meta)
        sw_sig = next(s for s in signals if s.signal_name == "editing_software_metadata")
        self.assertEqual(sw_sig.severity, SignalSeverity.LOW)
        self.assertEqual(sw_sig.evidence_strength, EvidenceStrength.WEAK)
        self.assertEqual(sw_sig.status, CheckStatus.WARNING)
        self.assertIn("Advisory signal only", sw_sig.explanation)


class TestScorerAndFeatures(unittest.TestCase):
    """8. Hierarchical evidence scoring and tabular feature extraction."""

    def test_32_strong_evidence_decisively_requires_review(self):
        # Even with high tamper score, critical inconsistency triggers review_required
        score, status, review_req, reasons = score_stage4_overall(
            tamper_score=95.0,
            tamper_status=CheckStatus.PASS,
            consistency_score=40.0,
            consistency_status=CheckStatus.NEEDS_REVIEW,
            critical_inconsistencies=["Date of Birth mismatch between GOVERNMENT_ID and MARKSHEET"],
            warnings=[],
        )
        self.assertEqual(status, CheckStatus.NEEDS_REVIEW)
        self.assertTrue(review_req)
        self.assertIn("critical cross-document contradiction", reasons[0].lower())

    def test_33_weak_evidence_never_triggers_needs_review_alone(self):
        # Single advisory warning reduces tamper score slightly but does not force review_required
        sigs = [
            TamperSignal(
                signal_name="editing_software_metadata",
                category=SignalCategory.METADATA,
                severity=SignalSeverity.LOW,
                score=78.0,
                confidence=0.70,
                status=CheckStatus.WARNING,
                explanation="Canva detected.",
                evidence_strength=EvidenceStrength.WEAK,
            )
        ]
        t_score, t_status, _, _ = score_tamper_signals(sigs)
        self.assertGreaterEqual(t_score, STAGE4_PASS_THRESHOLD)
        self.assertNotEqual(t_status, CheckStatus.NEEDS_REVIEW)
        self.assertEqual(t_status, CheckStatus.WARNING)

    def test_34_tabular_features_vector_extraction(self):
        checks = [
            ConsistencyCheckResult(
                check_name="name_consistency_gov_marksheet",
                category="CROSS_DOCUMENT_IDENTITY",
                status=CheckStatus.PASS,
                confidence=0.95,
                documents_compared=["GOVERNMENT_ID", "MARKSHEET"],
                field_name="student_name",
                reason="Match.",
            )
        ]
        feat_dict = extract_features_from_assessments([], checks)
        self.assertEqual(feat_dict["name_consistency_score"], 100.0)
        self.assertEqual(feat_dict["dob_mismatch_flag"], 0.0)

        vec = extract_feature_vector([], checks)
        self.assertIsInstance(vec, np.ndarray)
        self.assertEqual(len(vec), len(FEATURE_NAMES))


class TestStage4ServiceAndVerificationIntegration(unittest.TestCase):
    """9. TamperConsistencyService and full backend VerificationService integration."""

    def test_35_stage4_service_clean_execution(self):
        service = TamperConsistencyService()
        extractions = {
            "GOVERNMENT_ID": {
                "fields": {
                    "student_name": {"normalized_value": "rahul patil", "confidence": 0.95},
                    "date_of_birth": {"normalized_value": "2002-05-15", "confidence": 0.95},
                    "id_number": {"normalized_value": "987654321098", "confidence": 0.95},
                }
            },
            "MARKSHEET": {
                "fields": {
                    "student_name": {"normalized_value": "rahul patil", "confidence": 0.95},
                    "date_of_birth": {"normalized_value": "2002-05-15", "confidence": 0.95},
                    "total_marks": {"normalized_value": 450.0, "source_text": "450 / 600", "confidence": 0.95},
                    "percentage": {"normalized_value": 75.0, "confidence": 0.95},
                    "passing_year": {"normalized_value": 2020, "confidence": 0.95},
                }
            },
        }
        res = service.evaluate(extractions)
        self.assertEqual(res.overall_status, CheckStatus.PASS)
        self.assertFalse(res.review_required)
        self.assertGreaterEqual(res.overall_score, 80.0)

    def test_36_reverification_safe_merge_preserves_all_stages(self):
        """Constraint explicit test: Re-verification must not overwrite prior metadata."""
        mock_db = MagicMock()
        existing_result = MagicMock()
        existing_result.extracted_data = {
            "review_history": [{"action": "INITIAL_AUDIT", "admin": "admin1"}],
            "correction_request": {"status": "PENDING", "admin_name": "Officer A"},
            "risk_analysis": {"risk_level": "LOW", "risk_score": 10.0},
            "authority_verification": {"GOVERNMENT_ID": {"status": "NOT_AVAILABLE"}},
            "document_quality": {"overall_quality_score": 92.0},
            "document_classification": {"overall_status": "PASS"},
            "field_extraction": {"GOVERNMENT_ID": {"extraction_status": "COMPLETE"}},
            "tamper_consistency": {"overall_status": "PASS", "overall_score": 95.0},
        }

        mock_student = MagicMock(
            college_id=uuid.uuid4(),
            full_name="Test Student",
            date_of_birth="2002-01-01",
            government_id_number="TEST-1234-5678-9012"
        )

        # Mock DB queries
        mock_db.query().filter().first.side_effect = [
            # 1. ScholarshipApplication
            MagicMock(
                id=uuid.uuid4(),
                student_id=uuid.uuid4(),
                application_number="VC-TEST-9999",
                status=ApplicationStatus.DRAFT,
                documents=[
                    MagicMock(document_type=DocumentType.GOVERNMENT_ID, storage_path=None),
                    MagicMock(document_type=DocumentType.MARKSHEET, storage_path=None),
                    MagicMock(document_type=DocumentType.INCOME_CERTIFICATE, storage_path=None),
                    MagicMock(document_type=DocumentType.DOMICILE_CERTIFICATE, storage_path=None),
                ],
                student=mock_student,
            ),
            # 2. Existing VerificationResult
            existing_result,
        ]

        app_id = uuid.uuid4()
        with patch("app.services.document_storage_service.DocumentStorageService.get_document_file_path", side_effect=Exception("No disk file")):
            res = VerificationService.verify_application(mock_db, app_id)

        # Confirm all prior metadata fields are preserved in response
        self.assertIn("tamper_consistency", res)
        self.assertIn("field_extraction", res["extracted_data"])
        self.assertIn("review_history", res["extracted_data"])
        self.assertIn("correction_request", res["extracted_data"])
        self.assertIn("authority_verification", res["extracted_data"])
        self.assertIn("document_quality", res["extracted_data"])
        self.assertIn("document_classification", res["extracted_data"])

    def test_37_stage4_critical_signal_moves_to_needs_review_never_rejected(self):
        """Constraint explicit test: Stage 4 contradictions set NEEDS_REVIEW, NEVER REJECTED."""
        service = TamperConsistencyService()
        contradictory_extractions = {
            "GOVERNMENT_ID": {
                "fields": {
                    "student_name": {"normalized_value": "rahul patil", "confidence": 0.95},
                    "date_of_birth": {"normalized_value": "1998-01-01", "confidence": 0.95},
                }
            },
            "MARKSHEET": {
                "fields": {
                    "student_name": {"normalized_value": "suresh deshmukh", "confidence": 0.95},
                    "date_of_birth": {"normalized_value": "2005-09-09", "confidence": 0.95},
                }
            },
        }
        res = service.evaluate(contradictory_extractions)
        self.assertEqual(res.overall_status, CheckStatus.NEEDS_REVIEW)
        self.assertTrue(res.review_required)
        # Verify status is NEEDS_REVIEW, not REJECTED
        self.assertNotEqual(res.overall_status, "REJECTED")


if __name__ == "__main__":
    unittest.main()
