import unittest
import uuid
from datetime import date
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import HTTPException
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
from app.services.verification import (
    VerificationService,
    MockAIVerifier,
    MockScenario,
    CheckStatus,
    VerificationEvaluation,
    map_evaluation_to_statuses,
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


class TestVerificationServiceOrchestrator(unittest.TestCase):
    """
    Focused unit & API integration tests for Phase 6 Module 3:
    Verification Service Orchestrator + Database Persistence.
    """

    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()

        # Seed College 1 & 2
        self.college1_id = uuid.uuid4()
        self.college2_id = uuid.uuid4()
        c1 = College(id=self.college1_id, college_name="Demo College One", college_code="COLL001", email="c1@demo.edu")
        c2 = College(id=self.college2_id, college_name="Demo College Two", college_code="COLL002", email="c2@demo.edu")
        self.db.add_all([c1, c2])

        # Seed Student 1 (College 1)
        self.student1_id = uuid.uuid4()
        self.student1 = Student(
            id=self.student1_id,
            college_id=self.college1_id,
            full_name="Test Student",
            email="student1@demo.edu",
            password_hash=get_password_hash("Pass123!"),
            date_of_birth=date(2004, 1, 15),
            government_id_number="TEST-1234-5678-9012"
        )

        # Seed Student 2 (College 1 - another student)
        self.student2_id = uuid.uuid4()
        self.student2 = Student(
            id=self.student2_id,
            college_id=self.college1_id,
            full_name="Other Student",
            email="student2@demo.edu",
            password_hash=get_password_hash("Pass123!"),
            date_of_birth=date(2003, 5, 20),
            government_id_number="TEST-0000-1111-2222"
        )

        # Seed Admin for College 2 (Cross-college admin)
        self.admin2_id = uuid.uuid4()
        self.admin2 = AdminOfficer(
            id=self.admin2_id,
            college_id=self.college2_id,
            full_name="Admin College Two",
            email="admin2@demo.edu",
            password_hash=get_password_hash("AdminPass123!")
        )

        # Seed Scholarship Application for Student 1
        self.app1_id = uuid.uuid4()
        self.app1 = ScholarshipApplication(
            id=self.app1_id,
            student_id=self.student1_id,
            scholarship_name="Rajarshi Chhatrapati Shahu Maharaj Shikshan Shulkh Shishyavrutti Yojna (EBC)",
            application_number="VC-2026-1001",
            status=ApplicationStatus.DRAFT
        )

        self.db.add_all([self.student1, self.student2, self.admin2, self.app1])
        self.db.commit()

        # Seed all 4 required documents for App 1
        self.seed_four_documents(self.app1_id)

    def tearDown(self):
        self.db.close()

    def seed_four_documents(self, application_id: uuid.UUID):
        """Helper to seed the 4 mandatory documents for an application"""
        docs = [
            Document(
                id=uuid.uuid4(),
                application_id=application_id,
                document_type=DocumentType.GOVERNMENT_ID,
                original_filename="aadhaar.pdf",
                storage_path=f"{application_id}/government_id/aadhaar.pdf",
                upload_status=UploadStatus.UPLOADED
            ),
            Document(
                id=uuid.uuid4(),
                application_id=application_id,
                document_type=DocumentType.MARKSHEET,
                original_filename="hsc_marksheet.pdf",
                storage_path=f"{application_id}/marksheet/hsc_marksheet.pdf",
                upload_status=UploadStatus.UPLOADED
            ),
            Document(
                id=uuid.uuid4(),
                application_id=application_id,
                document_type=DocumentType.INCOME_CERTIFICATE,
                original_filename="income_cert.pdf",
                storage_path=f"{application_id}/income_certificate/income_cert.pdf",
                upload_status=UploadStatus.UPLOADED
            ),
            Document(
                id=uuid.uuid4(),
                application_id=application_id,
                document_type=DocumentType.DOMICILE_CERTIFICATE,
                original_filename="domicile_cert.pdf",
                storage_path=f"{application_id}/domicile_certificate/domicile_cert.pdf",
                upload_status=UploadStatus.UPLOADED
            ),
        ]
        self.db.add_all(docs)
        self.db.commit()

    # 1. Successful Verification
    def test_01_successful_verification(self):
        res = VerificationService.verify_application(
            db=self.db,
            app_id_str=self.app1_id,
            user_id_str=self.student1_id,
            role=UserRole.STUDENT,
            user_college_id_str=self.college1_id
        )

        self.assertEqual(res["status"], "VERIFIED")
        self.assertEqual(res["verification_status"], "VERIFIED")
        self.assertEqual(res["overall_score"], 100.0)
        self.assertEqual(len(res["critical_flags"]), 0)

    # 2. All Four Required Documents Present
    def test_02_all_four_required_documents_present(self):
        res = VerificationService.verify_application(self.db, self.app1_id)
        self.assertIn("GOVERNMENT_ID", res["extracted_data"])
        self.assertIn("MARKSHEET", res["extracted_data"])
        self.assertIn("INCOME_CERTIFICATE", res["extracted_data"])
        self.assertIn("DOMICILE_CERTIFICATE", res["extracted_data"])

    # 3. Missing Government ID
    def test_03_missing_government_id(self):
        self.db.query(Document).filter(
            Document.application_id == self.app1_id,
            Document.document_type == DocumentType.GOVERNMENT_ID
        ).delete()
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            VerificationService.verify_application(self.db, self.app1_id)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("GOVERNMENT_ID", ctx.exception.detail)

    # 4. Missing Marksheet
    def test_04_missing_marksheet(self):
        self.db.query(Document).filter(
            Document.application_id == self.app1_id,
            Document.document_type == DocumentType.MARKSHEET
        ).delete()
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            VerificationService.verify_application(self.db, self.app1_id)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("MARKSHEET", ctx.exception.detail)

    # 5. Missing Income Certificate
    def test_05_missing_income_certificate(self):
        self.db.query(Document).filter(
            Document.application_id == self.app1_id,
            Document.document_type == DocumentType.INCOME_CERTIFICATE
        ).delete()
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            VerificationService.verify_application(self.db, self.app1_id)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("INCOME_CERTIFICATE", ctx.exception.detail)

    # 6. Missing Domicile Certificate
    def test_06_missing_domicile_certificate(self):
        self.db.query(Document).filter(
            Document.application_id == self.app1_id,
            Document.document_type == DocumentType.DOMICILE_CERTIFICATE
        ).delete()
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            VerificationService.verify_application(self.db, self.app1_id)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("DOMICILE_CERTIFICATE", ctx.exception.detail)

    # 7. Mock Extraction Failure
    def test_07_mock_extraction_failure(self):
        fail_verifier = MockAIVerifier(default_scenario=MockScenario.FIELD_FAILURE)
        res = VerificationService.verify_application(
            self.db, self.app1_id, verifier=fail_verifier
        )

        self.assertEqual(res["verification_status"], "NEEDS_REVIEW")
        self.assertEqual(res["status"], "NEEDS_REVIEW")
        self.assertTrue(len(res["issues"]) > 0)

    # 8. Unreadable Document Handling
    def test_08_unreadable_document(self):
        unreadable_verifier = MockAIVerifier(default_scenario=MockScenario.UNREADABLE)
        res = VerificationService.verify_application(
            self.db, self.app1_id, verifier=unreadable_verifier
        )

        self.assertEqual(res["verification_status"], "NEEDS_REVIEW")
        self.assertEqual(res["status"], "NEEDS_REVIEW")
        self.assertTrue(any("UNREADABLE" in f for f in res["critical_flags"]))

    # 9. RulesEngine FAIL Result (e.g. Income exceeded)
    def test_09_rules_engine_fail_result(self):
        # Student DOB mismatch triggers critical flag and FAIL
        self.student1.date_of_birth = date(1998, 12, 1)
        self.db.commit()

        res = VerificationService.verify_application(self.db, self.app1_id)
        self.assertEqual(res["status"], "NEEDS_REVIEW")
        self.assertEqual(res["verification_status"], "NEEDS_REVIEW")
        self.assertIn("DOB_MISMATCH", res["critical_flags"])

    # 10. RulesEngine WARNING Result (e.g. Minor initial variation)
    def test_10_rules_engine_warning_result(self):
        self.student1.full_name = "Test K. Student"
        self.db.commit()

        res = VerificationService.verify_application(self.db, self.app1_id)
        self.assertEqual(res["status"], "NEEDS_REVIEW")
        self.assertEqual(res["verification_status"], "NEEDS_REVIEW")
        self.assertIn("NAME_VARIATION", res["critical_flags"])

    # 11. RulesEngine PASS Result
    def test_11_rules_engine_pass_result(self):
        res = VerificationService.verify_application(self.db, self.app1_id)
        self.assertEqual(res["status"], "VERIFIED")
        self.assertEqual(res["overall_score"], 100.0)

    # 12. VerificationResult Persistence
    def test_12_verification_result_persistence(self):
        VerificationService.verify_application(self.db, self.app1_id)

        record = self.db.query(VerificationResult).filter(
            VerificationResult.application_id == self.app1_id,
            VerificationResult.document_id.is_(None)
        ).first()

        self.assertIsNotNone(record)
        self.assertEqual(record.verification_status, VerificationStatus.VERIFIED)
        self.assertEqual(record.overall_score, 100.0)
        self.assertIsInstance(record.field_checks, dict)
        self.assertIsInstance(record.cross_document_matches, list)

    # 13. ScholarshipApplication Status Update
    def test_13_scholarship_application_status_update(self):
        VerificationService.verify_application(self.db, self.app1_id)

        app_record = self.db.query(ScholarshipApplication).filter(
            ScholarshipApplication.id == self.app1_id
        ).first()

        self.assertEqual(app_record.status, ApplicationStatus.VERIFIED)

    # 14. Transaction Rollback on Persistence Failure
    def test_14_transaction_rollback_on_persistence_failure(self):
        with patch.object(self.db, "commit", side_effect=Exception("DB Commit Failure")):
            with self.assertRaises(HTTPException) as ctx:
                VerificationService.verify_application(self.db, self.app1_id)
            self.assertEqual(ctx.exception.status_code, 500)

        # Confirm app status remains DRAFT after rollback
        app_record = self.db.query(ScholarshipApplication).filter(
            ScholarshipApplication.id == self.app1_id
        ).first()
        self.assertEqual(app_record.status, ApplicationStatus.DRAFT)

    # 15. Re-Verification Behavior (No duplicates)
    def test_15_re_verification_behavior(self):
        # Run 1
        VerificationService.verify_application(self.db, self.app1_id)
        count_1 = self.db.query(VerificationResult).filter(
            VerificationResult.application_id == self.app1_id
        ).count()
        self.assertEqual(count_1, 1)

        # Run 2 (Re-verification)
        VerificationService.verify_application(self.db, self.app1_id)
        count_2 = self.db.query(VerificationResult).filter(
            VerificationResult.application_id == self.app1_id
        ).count()
        # Strictly enforces single application-level result (no duplicates created)
        self.assertEqual(count_2, 1)

    # 16. Student Cannot Verify Another Student's Application
    def test_16_student_cannot_verify_another_student_application(self):
        with self.assertRaises(HTTPException) as ctx:
            VerificationService.verify_application(
                db=self.db,
                app_id_str=self.app1_id,
                user_id_str=self.student2_id,  # Student 2 trying to verify Student 1 app
                role=UserRole.STUDENT,
                user_college_id_str=self.college1_id
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Access denied", ctx.exception.detail)

    # 17. Admin Cannot Verify Another College's Application
    def test_17_admin_cannot_verify_another_college_application(self):
        with self.assertRaises(HTTPException) as ctx:
            VerificationService.verify_application(
                db=self.db,
                app_id_str=self.app1_id,
                user_id_str=self.admin2_id,
                role=UserRole.ADMIN,
                user_college_id_str=self.college2_id  # Admin is from College 2, App is College 1
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Cross-college", ctx.exception.detail)

    # 18. storage_path is Never Returned in Response
    def test_18_storage_path_never_returned_in_response(self):
        res = VerificationService.verify_application(self.db, self.app1_id)
        res_str = str(res).lower()
        self.assertNotIn("storage_path", res_str)
        self.assertNotIn("storage/applications", res_str)

    # 19. Deterministic Status Mapping
    def test_19_deterministic_status_mapping(self):
        eval_pass = VerificationEvaluation(
            overall_status=CheckStatus.PASS,
            overall_score=95.0,
            recommended_status="VERIFIED"
        )
        v_stat, a_stat = map_evaluation_to_statuses(eval_pass)
        self.assertEqual(v_stat, VerificationStatus.VERIFIED)
        self.assertEqual(a_stat, ApplicationStatus.VERIFIED)

        eval_warn = VerificationEvaluation(
            overall_status=CheckStatus.WARNING,
            overall_score=75.0,
            recommended_status="NEEDS_REVIEW"
        )
        v_stat, a_stat = map_evaluation_to_statuses(eval_warn)
        self.assertEqual(v_stat, VerificationStatus.NEEDS_REVIEW)
        self.assertEqual(a_stat, ApplicationStatus.NEEDS_REVIEW)

        eval_fail = VerificationEvaluation(
            overall_status=CheckStatus.FAIL,
            overall_score=40.0,
            recommended_status="NEEDS_REVIEW"
        )
        v_stat, a_stat = map_evaluation_to_statuses(eval_fail)
        self.assertEqual(v_stat, VerificationStatus.NEEDS_REVIEW)
        self.assertEqual(a_stat, ApplicationStatus.NEEDS_REVIEW)

    # 20. API Endpoints: POST /verify and GET /verification-result
    def test_20_api_endpoints(self):
        # Create student token
        student_token = create_access_token(
            subject=str(self.student1_id),
            role="STUDENT",
            college_id=str(self.college1_id)
        )

        # 1. Trigger verification via API
        response = self.client.post(
            f"/api/v1/applications/{self.app1_id}/verify",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "VERIFIED")
        self.assertEqual(data["verification_status"], "VERIFIED")
        self.assertNotIn("storage_path", str(data))

        # 2. Retrieve verification result via API
        get_response = self.client.get(
            f"/api/v1/applications/{self.app1_id}/verification-result",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        self.assertEqual(get_response.status_code, 200)
        get_data = get_response.json()
        self.assertEqual(get_data["overall_score"], 100.0)
        self.assertNotIn("storage_path", str(get_data))


if __name__ == "__main__":
    unittest.main()
