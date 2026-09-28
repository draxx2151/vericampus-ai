"""
VeriCampus AI — Document Quality Gate Test Suite
Tests all 20 required verification scenarios for Stage 1: AI Document Quality Gate.
"""
import unittest
import uuid
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.models.college import College
from app.db.models.student import Student
from app.db.models.admin_officer import AdminOfficer
from app.db.models.scholarship_application import ScholarshipApplication
from app.db.models.document import Document
from app.db.models.verification_result import VerificationResult
from app.db.models.enums import UserRole, ApplicationStatus, DocumentType, UploadStatus, VerificationStatus
from app.core.security import create_access_token, get_password_hash
from app.services.verification import VerificationService, MockAIVerifier, MockScenario
from app.services.verification.authority import UnavailableProvider, AuthorityStatus

from ml.document_quality import (
    DocumentQualityAnalyzer,
    QualityLevel,
    QualityGateStatus,
    QualityFeatures,
    QualityAssessment,
    HIGH_THRESHOLD,
    ACCEPTABLE_THRESHOLD,
    LOW_THRESHOLD,
    MODEL_VERSION,
)
from ml.document_quality.scorer import evaluate_features_rule_based, map_score_to_assessment
from ml.document_quality.model import QualityGateClassifier
from ml.document_quality.dataset import split_samples_by_student
from ml.data_generator.quality_degradations import (
    degrade_to_high,
    degrade_to_medium,
    degrade_to_low,
    degrade_to_unreadable,
)


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestAIDocumentQualityGate(unittest.TestCase):
    """
    Comprehensive 20-point verification test suite for Stage 1: AI Document Quality Gate.
    """

    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        self._seed_entities()

    def tearDown(self):
        self.db.rollback()
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def _seed_entities(self):
        self.college = College(
            id=uuid.uuid4(),
            college_name="Government Engineering College, Pune",
            college_code=f"COEP_{uuid.uuid4().hex[:6]}",
            address="Shivajinagar, Pune, Maharashtra",
        )
        self.db.add(self.college)

        self.student = Student(
            id=uuid.uuid4(),
            college_id=self.college.id,
            email=f"aarav.{uuid.uuid4().hex[:6]}@example.com",
            password_hash=get_password_hash("Student@123"),
            full_name="Aarav Tambekar",
            is_active=True,
        )
        self.db.add(self.student)

        self.admin = AdminOfficer(
            id=uuid.uuid4(),
            college_id=self.college.id,
            email=f"admin.{uuid.uuid4().hex[:6]}@coep.ac.in",
            password_hash=get_password_hash("Admin@123"),
            full_name="Dr. S. R. Joshi",
            is_active=True,
        )
        self.db.add(self.admin)
        self.db.commit()

        self.student_token = create_access_token(
            subject=str(self.student.id),
            role=UserRole.STUDENT.value,
            college_id=str(self.college.id),
        )
        self.admin_token = create_access_token(
            subject=str(self.admin.id),
            role=UserRole.ADMIN.value,
            college_id=str(self.college.id),
        )

    def _create_synthetic_canvas(self) -> np.ndarray:
        """Creates a clean synthetic test document image."""
        import cv2
        img = np.full((1100, 800, 3), 255, dtype=np.uint8)
        cv2.rectangle(img, (20, 20), (780, 1080), (102, 51, 0), 4)
        cv2.putText(img, "GOVERNMENT OF INDIA", (200, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
        cv2.putText(img, "Full Name: Aarav Tambekar", (60, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 2)
        cv2.putText(img, "Date of Birth: 2004-05-15", (60, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 2)
        cv2.putText(img, "Income: 120000", (60, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 2)
        cv2.putText(img, "State: Maharashtra", (60, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 2)
        return img

    # ─────────────────────────────────────────────────────────────
    # TEST 1: Clean document -> HIGH (Score >= 85)
    # ─────────────────────────────────────────────────────────────
    def test_01_clean_document_produces_high_quality(self):
        img = self._create_synthetic_canvas()
        degraded, metrics = degrade_to_high(img)
        assessment = DocumentQualityAnalyzer.analyze(degraded)

        self.assertGreaterEqual(assessment.quality_score, HIGH_THRESHOLD)
        self.assertEqual(assessment.quality_level, QualityLevel.HIGH)
        self.assertEqual(assessment.quality_gate_status, QualityGateStatus.PASS)

    # ─────────────────────────────────────────────────────────────
    # TEST 2: Slightly degraded -> ACCEPTABLE (70 <= Score < 85)
    # ─────────────────────────────────────────────────────────────
    def test_02_slightly_degraded_produces_acceptable_quality(self):
        # Feature payload representing a mild scan / slight angle
        features = QualityFeatures(
            resolution_megapixels=1.2,
            blur_laplacian_variance=180.0, # Mild softness (-7 pts)
            normalized_sharpness=70.0,
            brightness_mean=220.0,
            brightness_std=35.0,
            contrast_rms=35.0,
            noise_estimate_sigma=3.0,
            skew_angle_degrees=6.0,        # Moderate tilt (-10 pts)
            crop_margin_completeness=0.96, # Clean margins
            ocr_confidence=0.85,           # Adequate OCR
        )
        score, reasons = evaluate_features_rule_based(features)
        assessment = map_score_to_assessment(score, reasons, features.model_dump())

        self.assertGreaterEqual(assessment.quality_score, ACCEPTABLE_THRESHOLD)
        self.assertLess(assessment.quality_score, HIGH_THRESHOLD)
        self.assertEqual(assessment.quality_level, QualityLevel.ACCEPTABLE)
        self.assertEqual(assessment.quality_gate_status, QualityGateStatus.WARNING)

    # ─────────────────────────────────────────────────────────────
    # TEST 3: Blurry document -> LOW (40 <= Score < 70)
    # ─────────────────────────────────────────────────────────────
    def test_03_blurry_document_produces_low_quality(self):
        features = QualityFeatures(
            resolution_megapixels=0.88,
            blur_laplacian_variance=80.0,  # Noticeable blur (-18 pts)
            normalized_sharpness=16.0,
            brightness_mean=210.0,
            brightness_std=20.0,
            contrast_rms=16.0,            # Very low contrast (-22 pts)
            noise_estimate_sigma=5.0,
            skew_angle_degrees=2.0,
            crop_margin_completeness=1.0,
            ocr_confidence=0.62,           # Low OCR conf (-15 pts)
        )
        score, reasons = evaluate_features_rule_based(features)
        assessment = map_score_to_assessment(score, reasons, features.model_dump())

        self.assertLess(assessment.quality_score, ACCEPTABLE_THRESHOLD)
        self.assertGreaterEqual(assessment.quality_score, 40.0)
        self.assertEqual(assessment.quality_level, QualityLevel.LOW)
        self.assertEqual(assessment.quality_gate_status, QualityGateStatus.REUPLOAD_REQUIRED)
        self.assertTrue(any("blur" in r.lower() for r in assessment.reasons))

    # ─────────────────────────────────────────────────────────────
    # TEST 4: Severe degradation -> UNREADABLE (Score < 40)
    # ─────────────────────────────────────────────────────────────
    def test_04_severe_degradation_produces_unreadable(self):
        features = QualityFeatures(
            resolution_megapixels=0.15,    # Very low res (-30 pts)
            blur_laplacian_variance=25.0,  # Severe blur (-35 pts)
            normalized_sharpness=5.0,
            brightness_mean=40.0,          # Severe dark (-30 pts)
            brightness_std=10.0,
            contrast_rms=10.0,             # No contrast (-22 pts)
            noise_estimate_sigma=25.0,
            skew_angle_degrees=15.0,
            crop_margin_completeness=0.55, # Severe crop (-35 pts)
            ocr_confidence=0.15,
        )
        score, reasons = evaluate_features_rule_based(features)
        assessment = map_score_to_assessment(score, reasons, features.model_dump())

        self.assertLess(assessment.quality_score, 40.0)
        self.assertEqual(assessment.quality_level, QualityLevel.UNREADABLE)
        self.assertEqual(assessment.quality_gate_status, QualityGateStatus.REUPLOAD_REQUIRED)

    # ─────────────────────────────────────────────────────────────
    # TEST 5: OCR confidence influence
    # ─────────────────────────────────────────────────────────────
    def test_05_ocr_confidence_influence(self):
        f_high_ocr = QualityFeatures(
            resolution_megapixels=0.88, blur_laplacian_variance=500.0, normalized_sharpness=100.0,
            brightness_mean=240.0, brightness_std=30.0, contrast_rms=30.0, noise_estimate_sigma=1.0,
            skew_angle_degrees=0.5, crop_margin_completeness=1.0, ocr_confidence=0.98,
        )
        f_low_ocr = QualityFeatures(
            resolution_megapixels=0.88, blur_laplacian_variance=500.0, normalized_sharpness=100.0,
            brightness_mean=240.0, brightness_std=30.0, contrast_rms=30.0, noise_estimate_sigma=1.0,
            skew_angle_degrees=0.5, crop_margin_completeness=1.0, ocr_confidence=0.30,
        )
        score_high, reasons_high = evaluate_features_rule_based(f_high_ocr)
        score_low, reasons_low = evaluate_features_rule_based(f_low_ocr)

        self.assertGreater(score_high, score_low)
        self.assertTrue(any("OCR" in r for r in reasons_low))

    # ─────────────────────────────────────────────────────────────
    # TEST 6: Resolution influence
    # ─────────────────────────────────────────────────────────────
    def test_06_resolution_influence(self):
        f_good_res = QualityFeatures(
            resolution_megapixels=1.2, blur_laplacian_variance=500.0, normalized_sharpness=100.0,
            brightness_mean=240.0, brightness_std=30.0, contrast_rms=30.0, noise_estimate_sigma=1.0,
            skew_angle_degrees=0.5, crop_margin_completeness=1.0, ocr_confidence=0.90,
        )
        f_tiny_res = QualityFeatures(
            resolution_megapixels=0.10, blur_laplacian_variance=500.0, normalized_sharpness=100.0,
            brightness_mean=240.0, brightness_std=30.0, contrast_rms=30.0, noise_estimate_sigma=1.0,
            skew_angle_degrees=0.5, crop_margin_completeness=1.0, ocr_confidence=0.90,
        )
        score_good, _ = evaluate_features_rule_based(f_good_res)
        score_tiny, reasons_tiny = evaluate_features_rule_based(f_tiny_res)

        self.assertGreater(score_good, score_tiny)
        self.assertTrue(any("resolution" in r.lower() for r in reasons_tiny))

    # ─────────────────────────────────────────────────────────────
    # TEST 7: Rotation influence
    # ─────────────────────────────────────────────────────────────
    def test_07_rotation_influence(self):
        f_straight = QualityFeatures(
            resolution_megapixels=0.88, blur_laplacian_variance=500.0, normalized_sharpness=100.0,
            brightness_mean=240.0, brightness_std=30.0, contrast_rms=30.0, noise_estimate_sigma=1.0,
            skew_angle_degrees=0.2, crop_margin_completeness=1.0, ocr_confidence=0.95,
        )
        f_skewed = QualityFeatures(
            resolution_megapixels=0.88, blur_laplacian_variance=500.0, normalized_sharpness=100.0,
            brightness_mean=240.0, brightness_std=30.0, contrast_rms=30.0, noise_estimate_sigma=1.0,
            skew_angle_degrees=14.5, crop_margin_completeness=1.0, ocr_confidence=0.95,
        )
        score_straight, _ = evaluate_features_rule_based(f_straight)
        score_skewed, reasons_skewed = evaluate_features_rule_based(f_skewed)

        self.assertGreater(score_straight, score_skewed)
        self.assertTrue(any("skew" in r.lower() or "rotation" in r.lower() for r in reasons_skewed))

    # ─────────────────────────────────────────────────────────────
    # TEST 8: Crop influence
    # ─────────────────────────────────────────────────────────────
    def test_08_crop_influence(self):
        f_complete = QualityFeatures(
            resolution_megapixels=0.88, blur_laplacian_variance=500.0, normalized_sharpness=100.0,
            brightness_mean=240.0, brightness_std=30.0, contrast_rms=30.0, noise_estimate_sigma=1.0,
            skew_angle_degrees=0.5, crop_margin_completeness=1.0, ocr_confidence=0.95,
        )
        f_cut_edges = QualityFeatures(
            resolution_megapixels=0.88, blur_laplacian_variance=500.0, normalized_sharpness=100.0,
            brightness_mean=240.0, brightness_std=30.0, contrast_rms=30.0, noise_estimate_sigma=1.0,
            skew_angle_degrees=0.5, crop_margin_completeness=0.55, ocr_confidence=0.95,
        )
        score_complete, _ = evaluate_features_rule_based(f_complete)
        score_cut, reasons_cut = evaluate_features_rule_based(f_cut_edges)

        self.assertGreater(score_complete, score_cut)
        self.assertTrue(any("cut off" in r.lower() or "crop" in r.lower() for r in reasons_cut))

    # ─────────────────────────────────────────────────────────────
    # TEST 9: Quality threshold boundaries
    # ─────────────────────────────────────────────────────────────
    def test_09_threshold_boundaries(self):
        # Exactly 85.0 -> HIGH, PASS
        a85 = map_score_to_assessment(85.0, [], {})
        self.assertEqual(a85.quality_level, QualityLevel.HIGH)
        self.assertEqual(a85.quality_gate_status, QualityGateStatus.PASS)

        # 84.9 -> ACCEPTABLE, WARNING
        a849 = map_score_to_assessment(84.9, [], {})
        self.assertEqual(a849.quality_level, QualityLevel.ACCEPTABLE)
        self.assertEqual(a849.quality_gate_status, QualityGateStatus.WARNING)

        # Exactly 70.0 -> ACCEPTABLE, WARNING
        a70 = map_score_to_assessment(70.0, [], {})
        self.assertEqual(a70.quality_level, QualityLevel.ACCEPTABLE)
        self.assertEqual(a70.quality_gate_status, QualityGateStatus.WARNING)

        # 69.9 -> LOW, REUPLOAD_REQUIRED
        a699 = map_score_to_assessment(69.9, [], {})
        self.assertEqual(a699.quality_level, QualityLevel.LOW)
        self.assertEqual(a699.quality_gate_status, QualityGateStatus.REUPLOAD_REQUIRED)

        # 39.9 -> UNREADABLE, REUPLOAD_REQUIRED
        a399 = map_score_to_assessment(39.9, [], {})
        self.assertEqual(a399.quality_level, QualityLevel.UNREADABLE)
        self.assertEqual(a399.quality_gate_status, QualityGateStatus.REUPLOAD_REQUIRED)

    # ─────────────────────────────────────────────────────────────
    # TEST 10: Threshold configuration (Single source of truth)
    # ─────────────────────────────────────────────────────────────
    def test_10_threshold_configuration_constants(self):
        self.assertEqual(HIGH_THRESHOLD, 85.0)
        self.assertEqual(ACCEPTABLE_THRESHOLD, 70.0)
        self.assertEqual(LOW_THRESHOLD, 0.0)

    # ─────────────────────────────────────────────────────────────
    # TEST 11: No false application rejection (< 70 -> NEVER REJECTED)
    # ─────────────────────────────────────────────────────────────
    def test_11_no_false_application_rejection_on_low_quality(self):
        app_record = ScholarshipApplication(
            id=uuid.uuid4(),
            student_id=self.student.id,
            scholarship_name="Post Matric Scholarship to OBC Students",
            application_number="VC-2026-TEST-QG1",
            status=ApplicationStatus.DRAFT,
        )
        self.db.add(app_record)

        # Add 4 documents
        for dt in [DocumentType.GOVERNMENT_ID, DocumentType.MARKSHEET, DocumentType.INCOME_CERTIFICATE, DocumentType.DOMICILE_CERTIFICATE]:
            doc = Document(
                id=uuid.uuid4(),
                application_id=app_record.id,
                document_type=dt,
                original_filename=f"{dt.value.lower()}.png",
                storage_path=f"mock_storage/{dt.value.lower()}.png",
                mime_type="image/png",
                file_size=102400,
                upload_status=UploadStatus.UPLOADED,
            )
            self.db.add(doc)
        self.db.commit()

        # Mock Quality Analyzer to return score 55.0 (LOW) for one document
        with patch.object(DocumentQualityAnalyzer, "analyze") as mock_analyze:
            mock_analyze.return_value = QualityAssessment(
                quality_score=55.0,
                quality_level=QualityLevel.LOW,
                quality_gate_status=QualityGateStatus.REUPLOAD_REQUIRED,
                reasons=["Noticeable image blur detected; text clarity is reduced."],
                features={"resolution_megapixels": 0.88},
                model_version=MODEL_VERSION,
            )

            res = VerificationService.verify_application(
                db=self.db,
                app_id_str=app_record.id,
                user_id_str=self.student.id,
                role=UserRole.STUDENT,
                verifier=MockAIVerifier(),
            )

            # CRITICAL CHECK: Status is NEEDS_REVIEW, absolutely NEVER REJECTED
            self.assertNotEqual(res["status"], "REJECTED")
            self.assertEqual(res["status"], "NEEDS_REVIEW")
            self.assertEqual(res["verification_status"], "NEEDS_REVIEW")

    # ─────────────────────────────────────────────────────────────
    # TEST 12: Correction workflow integration on REUPLOAD_REQUIRED
    # ─────────────────────────────────────────────────────────────
    def test_12_correction_workflow_integration(self):
        app_record = ScholarshipApplication(
            id=uuid.uuid4(),
            student_id=self.student.id,
            scholarship_name="Post Matric Scholarship to OBC Students",
            application_number="VC-2026-TEST-QG2",
            status=ApplicationStatus.DRAFT,
        )
        self.db.add(app_record)

        for dt in [DocumentType.GOVERNMENT_ID, DocumentType.MARKSHEET, DocumentType.INCOME_CERTIFICATE, DocumentType.DOMICILE_CERTIFICATE]:
            doc = Document(
                id=uuid.uuid4(),
                application_id=app_record.id,
                document_type=dt,
                original_filename=f"{dt.value.lower()}.png",
                storage_path=f"mock_storage/{dt.value.lower()}.png",
                mime_type="image/png",
                file_size=102400,
                upload_status=UploadStatus.UPLOADED,
            )
            self.db.add(doc)
        self.db.commit()

        with patch.object(DocumentQualityAnalyzer, "analyze") as mock_analyze:
            mock_analyze.return_value = QualityAssessment(
                quality_score=50.0,
                quality_level=QualityLevel.LOW,
                quality_gate_status=QualityGateStatus.REUPLOAD_REQUIRED,
                reasons=["Excessive blur detected."],
                features={},
                model_version=MODEL_VERSION,
            )

            res = VerificationService.verify_application(
                db=self.db,
                app_id_str=app_record.id,
                user_id_str=self.student.id,
                role=UserRole.STUDENT,
                verifier=MockAIVerifier(),
            )

            # Check that correction_request was created in extracted_data
            vr = self.db.query(VerificationResult).filter(VerificationResult.application_id == app_record.id).first()
            self.assertIsNotNone(vr)
            cr = vr.extracted_data.get("correction_request")
            self.assertIsNotNone(cr)
            self.assertEqual(cr["status"], "PENDING")
            self.assertEqual(cr["admin_id"], "SYSTEM_QUALITY_GATE")

    # ─────────────────────────────────────────────────────────────
    # TEST 13: Notification integration
    # ─────────────────────────────────────────────────────────────
    def test_13_notification_integration_on_quality_flag(self):
        from app.db.models.notification import Notification

        app_record = ScholarshipApplication(
            id=uuid.uuid4(),
            student_id=self.student.id,
            scholarship_name="Post Matric Scholarship to OBC Students",
            application_number="VC-2026-TEST-QG3",
            status=ApplicationStatus.DRAFT,
        )
        self.db.add(app_record)

        for dt in [DocumentType.GOVERNMENT_ID, DocumentType.MARKSHEET, DocumentType.INCOME_CERTIFICATE, DocumentType.DOMICILE_CERTIFICATE]:
            doc = Document(
                id=uuid.uuid4(),
                application_id=app_record.id,
                document_type=dt,
                original_filename=f"{dt.value.lower()}.png",
                storage_path=f"mock_storage/{dt.value.lower()}.png",
                mime_type="image/png",
                file_size=102400,
                upload_status=UploadStatus.UPLOADED,
            )
            self.db.add(doc)
        self.db.commit()

        with patch.object(DocumentQualityAnalyzer, "analyze") as mock_analyze:
            mock_analyze.return_value = QualityAssessment(
                quality_score=52.0,
                quality_level=QualityLevel.LOW,
                quality_gate_status=QualityGateStatus.REUPLOAD_REQUIRED,
                reasons=["Low OCR readability."],
                features={},
                model_version=MODEL_VERSION,
            )

            VerificationService.verify_application(
                db=self.db,
                app_id_str=app_record.id,
                user_id_str=self.student.id,
                role=UserRole.STUDENT,
                verifier=MockAIVerifier(),
            )

            # Check that a DOCUMENT_CORRECTION_REQUESTED notification was sent to student
            notif = self.db.query(Notification).filter(
                Notification.student_id == self.student.id,
                Notification.event_type == "DOCUMENT_CORRECTION_REQUESTED"
            ).first()
            self.assertIsNotNone(notif)
            self.assertIn("Document Re-upload Required", notif.title)

    # ─────────────────────────────────────────────────────────────
    # TEST 14: Student tenant isolation
    # ─────────────────────────────────────────────────────────────
    def test_14_student_tenant_isolation(self):
        # Create a second student
        other_student = Student(
            id=uuid.uuid4(),
            college_id=self.college.id,
            email="other.student@example.com",
            password_hash=get_password_hash("Pass@123"),
            full_name="Other Student",
            is_active=True,
        )
        self.db.add(other_student)
        app_record = ScholarshipApplication(
            id=uuid.uuid4(),
            student_id=other_student.id,
            scholarship_name="Post Matric Scholarship to OBC Students",
            application_number="VC-2026-TEST-QG4",
            status=ApplicationStatus.DRAFT,
        )
        self.db.add(app_record)
        self.db.commit()

        response = self.client.post(
            f"/api/v1/applications/{app_record.id}/verify",
            headers={"Authorization": f"Bearer {self.student_token}"},
        )
        self.assertEqual(response.status_code, 403)

    # ─────────────────────────────────────────────────────────────
    # TEST 15: Admin tenant isolation
    # ─────────────────────────────────────────────────────────────
    def test_15_admin_tenant_isolation(self):
        other_college = College(
            id=uuid.uuid4(),
            college_name="Other College",
            college_code=f"OTH_{uuid.uuid4().hex[:6]}",
            address="Mumbai",
        )
        self.db.add(other_college)
        other_admin = AdminOfficer(
            id=uuid.uuid4(),
            college_id=other_college.id,
            email=f"admin.{uuid.uuid4().hex[:6]}@other.edu",
            password_hash=get_password_hash("Admin@123"),
            full_name="Other Admin",
            is_active=True,
        )
        self.db.add(other_admin)
        other_admin_token = create_access_token(
            subject=str(other_admin.id),
            role=UserRole.ADMIN.value,
            college_id=str(other_college.id),
        )
        app_record = ScholarshipApplication(
            id=uuid.uuid4(),
            student_id=self.student.id,
            scholarship_name="Post Matric Scholarship to OBC Students",
            application_number="VC-2026-TEST-QG5",
            status=ApplicationStatus.DRAFT,
        )
        self.db.add(app_record)
        self.db.commit()

        response = self.client.get(
            f"/api/v1/applications/{app_record.id}",
            headers={"Authorization": f"Bearer {other_admin_token}"},
        )
        self.assertEqual(response.status_code, 403)

    # ─────────────────────────────────────────────────────────────
    # TEST 16: Train/test leakage prevention (Zero ID Overlap)
    # ─────────────────────────────────────────────────────────────
    def test_16_train_test_leakage_prevention(self):
        mock_samples = []
        for sid in range(20):
            for doc in ["GOVERNMENT_ID", "MARKSHEET", "INCOME_CERTIFICATE", "DOMICILE_CERTIFICATE"]:
                mock_samples.append({
                    "student_id": sid,
                    "document_type": doc,
                    "quality_label": "HIGH",
                    "features": {"resolution_megapixels": 0.88},
                })

        train, val, test = split_samples_by_student(mock_samples, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42)
        train_ids = set(s["student_id"] for s in train)
        val_ids = set(s["student_id"] for s in val)
        test_ids = set(s["student_id"] for s in test)

        self.assertEqual(len(train_ids.intersection(val_ids)), 0)
        self.assertEqual(len(train_ids.intersection(test_ids)), 0)
        self.assertEqual(len(val_ids.intersection(test_ids)), 0)

    # ─────────────────────────────────────────────────────────────
    # TEST 17: Deterministic inference
    # ─────────────────────────────────────────────────────────────
    def test_17_deterministic_inference(self):
        f = QualityFeatures(
            resolution_megapixels=0.88, blur_laplacian_variance=300.0, normalized_sharpness=60.0,
            brightness_mean=230.0, brightness_std=25.0, contrast_rms=25.0, noise_estimate_sigma=2.0,
            skew_angle_degrees=2.5, crop_margin_completeness=1.0, ocr_confidence=0.88,
        )
        score1, reasons1 = evaluate_features_rule_based(f)
        score2, reasons2 = evaluate_features_rule_based(f)
        self.assertEqual(score1, score2)
        self.assertEqual(reasons1, reasons2)

    # ─────────────────────────────────────────────────────────────
    # TEST 18: Model artifact loading
    # ─────────────────────────────────────────────────────────────
    def test_18_model_artifact_loading(self):
        from ml.document_quality.config import DEFAULT_MODEL_PATH
        if DEFAULT_MODEL_PATH.exists():
            clf = QualityGateClassifier.load(str(DEFAULT_MODEL_PATH))
            self.assertTrue(clf.is_fitted)
            self.assertEqual(clf.classes_, ["HIGH", "LOW", "MEDIUM", "UNREADABLE"])

    # ─────────────────────────────────────────────────────────────
    # TEST 19: Missing / corrupt model handling (Graceful Fallback)
    # ─────────────────────────────────────────────────────────────
    def test_19_missing_model_graceful_fallback(self):
        # Providing non-existent model path
        fake_path = "/nonexistent/path/to/model.joblib"
        assessment = DocumentQualityAnalyzer.analyze(
            self._create_synthetic_canvas(),
            model_path=fake_path
        )
        self.assertTrue(assessment.is_fallback)
        self.assertGreaterEqual(assessment.quality_score, 0.0)
        self.assertLessEqual(assessment.quality_score, 100.0)

    # ─────────────────────────────────────────────────────────────
    # TEST 20: Stage 5 Authority Verification returns NOT_AVAILABLE
    # ─────────────────────────────────────────────────────────────
    def test_20_stage_5_authority_verification_not_available(self):
        provider = UnavailableProvider()
        res = provider.verify_document(DocumentType.GOVERNMENT_ID)
        self.assertEqual(res.status, AuthorityStatus.NOT_AVAILABLE)
        self.assertFalse(res.is_available)
        self.assertEqual(res.provider_name, "UnavailableProvider")


if __name__ == "__main__":
    unittest.main()
