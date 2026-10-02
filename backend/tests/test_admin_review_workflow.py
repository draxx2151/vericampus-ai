import sys
from pathlib import Path
import unittest
import uuid
import io
from datetime import date, datetime, timezone
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

backend_dir = Path(__file__).resolve().parent.parent
root_dir = backend_dir.parent
for d in (str(backend_dir), str(root_dir)):
    if d not in sys.path:
        sys.path.insert(0, d)

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.models.college import College
from app.db.models.student import Student
from app.db.models.admin_officer import AdminOfficer
from app.db.models.scholarship_application import ScholarshipApplication
from app.db.models.document import Document
from app.db.models.verification_result import VerificationResult
from app.db.models.appointment import PhysicalVerificationAppointment
from app.db.models.enums import UserRole, ApplicationStatus, DocumentType, UploadStatus, VerificationStatus, AppointmentStatus
from app.core.security import create_access_token, get_password_hash
from app.services.admin_review_service import AdminReviewService
from app.schemas.admin_review import (
    ApproveApplicationRequest,
    RequestCorrectionRequest,
    SchedulePhysicalVerificationRequest,
    CompletePhysicalVerificationRequest,
    RejectApplicationRequest,
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


class TestAdminReviewWorkflow(unittest.TestCase):
    """
    Comprehensive test suite for Phase 6 Module 6A:
    Admin Review & Human-in-the-Loop Decision Workflow.
    """

    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()

        # Seed College 1 & College 2
        self.college1_id = uuid.uuid4()
        self.college2_id = uuid.uuid4()
        c1 = College(id=self.college1_id, college_name="Engineering College A", college_code="COLL001", email="c1@demo.edu")
        c2 = College(id=self.college2_id, college_name="Engineering College B", college_code="COLL002", email="c2@demo.edu")
        self.db.add_all([c1, c2])

        # Seed Admin 1 (College 1) & Admin 2 (College 2)
        self.admin1_id = uuid.uuid4()
        self.admin1 = AdminOfficer(
            id=self.admin1_id,
            college_id=self.college1_id,
            full_name="Admin College One",
            email="admin1@demo.edu",
            password_hash=get_password_hash("AdminPass123!"),
            is_active=True,
        )
        self.admin2_id = uuid.uuid4()
        self.admin2 = AdminOfficer(
            id=self.admin2_id,
            college_id=self.college2_id,
            full_name="Admin College Two",
            email="admin2@demo.edu",
            password_hash=get_password_hash("AdminPass123!"),
            is_active=True,
        )

        # Seed Student 1 (College 1) & Student 2 (College 1, different student)
        self.student1_id = uuid.uuid4()
        self.student1 = Student(
            id=self.student1_id,
            college_id=self.college1_id,
            full_name="Rajesh Patil",
            email="rajesh@demo.edu",
            password_hash=get_password_hash("StudentPass123!"),
            date_of_birth=date(2003, 4, 15),
            government_id_number="TEST-1111-2222-3333",
        )
        self.student2_id = uuid.uuid4()
        self.student2 = Student(
            id=self.student2_id,
            college_id=self.college1_id,
            full_name="Sneha Sharma",
            email="sneha@demo.edu",
            password_hash=get_password_hash("StudentPass123!"),
            date_of_birth=date(2004, 8, 20),
            government_id_number="TEST-4444-5555-6666",
        )

        # Seed Application 1 for Student 1 (College 1)
        self.app1_id = uuid.uuid4()
        self.app1 = ScholarshipApplication(
            id=self.app1_id,
            student_id=self.student1_id,
            scholarship_name="Post Matric Scholarship to VJNT Students",
            application_number="VC-2026-9001",
            status=ApplicationStatus.SUBMITTED,
        )

        self.db.add_all([self.admin1, self.admin2, self.student1, self.student2, self.app1])
        self.db.commit()

        # Seed 4 required documents
        self.seed_four_documents(self.app1_id)

        # Pre-seed VerificationResult
        self.vr1 = VerificationResult(
            id=uuid.uuid4(),
            application_id=self.app1_id,
            overall_score=88.5,
            verification_status=VerificationStatus.NEEDS_REVIEW,
            extracted_data={
                "GOVERNMENT_ID": {"aadhaar_number": "1111-2222-3333"},
                "review_history": [],
            },
            field_checks=[],
            cross_document_matches=[],
            issues=["Minor discrepancy in marksheet"],
        )
        self.db.add(self.vr1)
        self.db.commit()

        # Generate tokens
        self.admin1_token = create_access_token(
            subject=str(self.admin1_id),
            role="ADMIN",
            college_id=str(self.college1_id),
        )
        self.admin2_token = create_access_token(
            subject=str(self.admin2_id),
            role="ADMIN",
            college_id=str(self.college2_id),
        )
        self.student1_token = create_access_token(
            subject=str(self.student1_id),
            role="STUDENT",
            college_id=str(self.college1_id),
        )
        self.student2_token = create_access_token(
            subject=str(self.student2_id),
            role="STUDENT",
            college_id=str(self.college1_id),
        )

    def tearDown(self):
        self.db.close()

    def seed_four_documents(self, application_id: uuid.UUID):
        docs = [
            Document(
                id=uuid.uuid4(),
                application_id=application_id,
                document_type=DocumentType.GOVERNMENT_ID,
                original_filename="aadhaar.pdf",
                storage_path=f"{application_id}/government_id/aadhaar.pdf",
                upload_status=UploadStatus.UPLOADED,
            ),
            Document(
                id=uuid.uuid4(),
                application_id=application_id,
                document_type=DocumentType.MARKSHEET,
                original_filename="marksheet.pdf",
                storage_path=f"{application_id}/marksheet/marksheet.pdf",
                upload_status=UploadStatus.UPLOADED,
            ),
            Document(
                id=uuid.uuid4(),
                application_id=application_id,
                document_type=DocumentType.INCOME_CERTIFICATE,
                original_filename="income.pdf",
                storage_path=f"{application_id}/income_certificate/income.pdf",
                upload_status=UploadStatus.UPLOADED,
            ),
            Document(
                id=uuid.uuid4(),
                application_id=application_id,
                document_type=DocumentType.DOMICILE_CERTIFICATE,
                original_filename="domicile.pdf",
                storage_path=f"{application_id}/domicile_certificate/domicile.pdf",
                upload_status=UploadStatus.UPLOADED,
            ),
        ]
        self.db.add_all(docs)
        self.db.commit()

    # --------------------------------------------------------------------------
    # 1. APPROVE / VERIFY TESTS
    # --------------------------------------------------------------------------
    def test_01_admin_approve_success(self):
        payload = {"notes": "All documents verified manually. Looks solid."}
        response = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/approve",
            json=payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "VERIFIED")
        self.assertEqual(data["verification_status"], "VERIFIED")
        self.assertIn("review_history", data["extracted_data"])
        history = data["extracted_data"]["review_history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["action"], "APPROVE")
        self.assertEqual(history[0]["admin_id"], str(self.admin1_id))
        self.assertEqual(history[0]["notes"], payload["notes"])

        # Check DB directly
        app = self.db.query(ScholarshipApplication).filter(ScholarshipApplication.id == self.app1_id).first()
        self.assertEqual(app.status, ApplicationStatus.VERIFIED)

        vr = self.db.query(VerificationResult).filter(VerificationResult.application_id == self.app1_id).first()
        self.assertEqual(vr.verification_status, VerificationStatus.VERIFIED)
        self.assertEqual(vr.verified_by_admin_id, self.admin1_id)
        self.assertIsNotNone(vr.reviewed_at)

    def test_02_student_cannot_approve(self):
        response = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/approve",
            json={"notes": "Trying to self approve"},
            headers={"Authorization": f"Bearer {self.student1_token}"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Admin", response.json()["detail"])

    def test_03_cross_college_admin_cannot_approve(self):
        response = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/approve",
            json={"notes": "Cross college attempt"},
            headers={"Authorization": f"Bearer {self.admin2_token}"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cross-college", response.json()["detail"])

    def test_04_approve_fails_if_missing_required_documents(self):
        # Remove government_id
        self.db.query(Document).filter(
            Document.application_id == self.app1_id,
            Document.document_type == DocumentType.GOVERNMENT_ID,
        ).delete()
        self.db.commit()

        response = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/approve",
            json={"notes": "Approving with missing doc"},
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing required documents", response.json()["detail"])

    # --------------------------------------------------------------------------
    # 2. REQUEST DOCUMENT CORRECTION TESTS
    # --------------------------------------------------------------------------
    def test_05_admin_request_document_correction_success(self):
        payload = {
            "document_types": ["INCOME_CERTIFICATE", "MARKSHEET"],
            "reason": "Income certificate is blurred and HSC marksheet is missing signature.",
        }
        response = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/request-correction",
            json=payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "NEEDS_REVIEW")
        self.assertEqual(data["verification_status"], "NEEDS_REVIEW")

        correction = data["extracted_data"].get("correction_request")
        self.assertIsNotNone(correction)
        self.assertEqual(correction["status"], "PENDING")
        self.assertEqual(correction["requested_documents"], payload["document_types"])
        self.assertEqual(correction["reason"], payload["reason"])
        self.assertEqual(correction["requested_by"], str(self.admin1_id))

        # Check DB application status
        app = self.db.query(ScholarshipApplication).filter(ScholarshipApplication.id == self.app1_id).first()
        self.assertEqual(app.status, ApplicationStatus.NEEDS_REVIEW)

        # Issues should have correction entry
        vr = self.db.query(VerificationResult).filter(VerificationResult.application_id == self.app1_id).first()
        self.assertTrue(any("Correction requested" in issue for issue in vr.issues))

    def test_06_request_correction_validation_min_length(self):
        payload = {
            "document_types": ["INCOME_CERTIFICATE"],
            "reason": "Bad",  # < 5 chars
        }
        response = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/request-correction",
            json=payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )
        self.assertEqual(response.status_code, 422)

    def test_07_request_correction_validation_invalid_doc_type(self):
        payload = {
            "document_types": ["INVALID_DOC_TYPE"],
            "reason": "Please re-upload a proper document",
        }
        response = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/request-correction",
            json=payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )
        self.assertEqual(response.status_code, 422)

    def test_08_student_views_correction_request_in_application(self):
        # Admin requests correction first
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/request-correction",
            json={
                "document_types": ["DOMICILE_CERTIFICATE"],
                "reason": "The domicile certificate is from another state.",
            },
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )

        # Student gets application details
        response = self.client.get(
            f"/api/v1/applications/{self.app1_id}",
            headers={"Authorization": f"Bearer {self.student1_token}"},
        )
        self.assertEqual(response.status_code, 200)
        app_data = response.json()
        self.assertIn("correction_request", app_data)
        corr = app_data["correction_request"]
        self.assertEqual(corr["status"], "PENDING")
        self.assertEqual(corr["requested_documents"], ["DOMICILE_CERTIFICATE"])

    # --------------------------------------------------------------------------
    # 3. PHYSICAL VERIFICATION TESTS
    # --------------------------------------------------------------------------
    def test_09_admin_schedule_physical_verification_success(self):
        payload = {
            "scheduled_date": "2026-10-15",
            "scheduled_time": "10:30 AM",
            "venue": "Dean Office, Room 102",
            "purpose": "Verify original caste and domicile certificates",
            "instructions": "Bring original certificates along with two photocopies.",
        }
        response = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/physical-verification",
            json=payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "SCHEDULED")
        self.assertEqual(data["application_status"], "PHYSICAL_VERIFICATION_REQUIRED")

        # Check DB appointment record
        appt = self.db.query(PhysicalVerificationAppointment).filter(
            PhysicalVerificationAppointment.application_id == self.app1_id
        ).first()
        self.assertIsNotNone(appt)
        self.assertEqual(str(appt.scheduled_date), "2026-10-15")
        self.assertEqual(appt.scheduled_time.strftime("%H:%M"), "10:30")
        self.assertEqual(appt.venue, "Dean Office, Room 102")
        self.assertEqual(appt.status, AppointmentStatus.SCHEDULED)

    def test_10_rescheduling_physical_verification_updates_in_place(self):
        payload1 = {
            "scheduled_date": "2026-10-15",
            "scheduled_time": "10:30 AM",
            "venue": "Room 102",
            "purpose": "First attempt",
            "instructions": "Bring docs",
        }
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/physical-verification",
            json=payload1,
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )

        # Re-schedule to new date/time
        payload2 = {
            "scheduled_date": "2026-10-20",
            "scheduled_time": "02:00 PM",
            "venue": "Room 205 (New Building)",
            "purpose": "Rescheduled meeting",
            "instructions": "Bring updated original documents",
        }
        response = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/physical-verification",
            json=payload2,
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )
        self.assertEqual(response.status_code, 200)

        # Ensure only 1 appointment exists for this application and it's updated
        appts = self.db.query(PhysicalVerificationAppointment).filter(
            PhysicalVerificationAppointment.application_id == self.app1_id
        ).all()
        self.assertEqual(len(appts), 1)
        self.assertEqual(str(appts[0].scheduled_date), "2026-10-20")
        self.assertEqual(appts[0].scheduled_time.strftime("%H:%M"), "14:00")
        self.assertEqual(appts[0].venue, "Room 205 (New Building)")

    def test_11_student_can_fetch_own_appointment(self):
        # Schedule first
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/physical-verification",
            json={
                "scheduled_date": "2026-10-15",
                "scheduled_time": "11:00 AM",
                "venue": "Admin Block Desk 4",
                "purpose": "Verify income certificate authenticity",
                "instructions": "Original income certificate required",
            },
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )

        # Student fetches via /my-application/physical-verification
        res_my = self.client.get(
            "/api/v1/applications/my-application/physical-verification",
            headers={"Authorization": f"Bearer {self.student1_token}"},
        )
        self.assertEqual(res_my.status_code, 200)
        data = res_my.json()
        self.assertEqual(data["scheduled_date"], "2026-10-15")
        self.assertEqual(data["venue"], "Admin Block Desk 4")

        # Student fetches via /{application_id}/physical-verification
        res_id = self.client.get(
            f"/api/v1/applications/{self.app1_id}/physical-verification",
            headers={"Authorization": f"Bearer {self.student1_token}"},
        )
        self.assertEqual(res_id.status_code, 200)
        self.assertEqual(res_id.json()["scheduled_date"], "2026-10-15")

    def test_12_other_student_cannot_fetch_appointment(self):
        # Schedule for Student 1
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/physical-verification",
            json={
                "scheduled_date": "2026-10-15",
                "scheduled_time": "11:00 AM",
                "venue": "Desk 4",
                "purpose": "Verify",
                "instructions": "Originals",
            },
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )

        # Student 2 attempts to fetch Student 1's appointment
        res = self.client.get(
            f"/api/v1/applications/{self.app1_id}/physical-verification",
            headers={"Authorization": f"Bearer {self.student2_token}"},
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Access denied", res.json()["detail"])

    def test_13_complete_physical_verification_verified(self):
        # Schedule first
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/physical-verification",
            json={
                "scheduled_date": "2026-10-15",
                "scheduled_time": "11:00 AM",
                "venue": "Desk 4",
                "purpose": "Verify",
                "instructions": "Originals",
            },
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )

        # Complete with VERIFIED
        comp_payload = {
            "result": "VERIFIED",
            "remarks": "Original government ID and income certificate verified physically in office.",
        }
        res = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/physical-verification/complete",
            json=comp_payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "PHYSICAL_VERIFICATION_COMPLETED")
        self.assertEqual(data["verification_status"], "VERIFIED")

        # Check appointment status in DB
        appt = self.db.query(PhysicalVerificationAppointment).filter(
            PhysicalVerificationAppointment.application_id == self.app1_id
        ).first()
        self.assertEqual(appt.status, AppointmentStatus.COMPLETED)
        self.assertIn("Original government ID", appt.notes)
        self.assertIn("VERIFIED", appt.notes)

    def test_14_complete_physical_verification_not_verified(self):
        # Schedule first
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/physical-verification",
            json={
                "scheduled_date": "2026-10-15",
                "scheduled_time": "11:00 AM",
                "venue": "Desk 4",
                "purpose": "Verify",
                "instructions": "Originals",
            },
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )

        # Complete with NOT_VERIFIED
        comp_payload = {
            "result": "NOT_VERIFIED",
            "remarks": "Student failed to present genuine original income certificate.",
        }
        res = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/physical-verification/complete",
            json=comp_payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "NEEDS_REVIEW")
        self.assertEqual(data["verification_status"], "NEEDS_REVIEW")

    # --------------------------------------------------------------------------
    # 4. REJECT TESTS
    # --------------------------------------------------------------------------
    def test_15_admin_reject_application_success(self):
        payload = {
            "reason": "Income certificate found to be fraudulent upon physical verification.",
            "notes": "Forwarded to disciplinary committee.",
        }
        response = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/reject",
            json=payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "REJECTED")
        self.assertEqual(data["verification_status"], "REJECTED")

        # Issues should have the rejection reason
        self.assertTrue(any("Rejection reason" in issue for issue in data["issues"]))

        # History check
        history = data["extracted_data"]["review_history"]
        last_hist = history[-1]
        self.assertEqual(last_hist["action"], "REJECT")
        self.assertEqual(last_hist["reason"], payload["reason"])

        # DB check
        app = self.db.query(ScholarshipApplication).filter(ScholarshipApplication.id == self.app1_id).first()
        self.assertEqual(app.status, ApplicationStatus.REJECTED)

    def test_16_reject_fails_without_sufficient_reason(self):
        payload = {"reason": "No"}  # < 5 chars
        response = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/reject",
            json=payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )
        self.assertEqual(response.status_code, 422)

    def test_17_cross_college_admin_cannot_reject(self):
        response = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/reject",
            json={"reason": "Cross college rejection attempt"},
            headers={"Authorization": f"Bearer {self.admin2_token}"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cross-college", response.json()["detail"])

    def test_18_student_replaces_correction_document_resolves_request(self):
        # 1. Admin requests correction for INCOME_CERTIFICATE
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/request-correction",
            json={
                "document_types": ["INCOME_CERTIFICATE"],
                "reason": "Income certificate is blurry, please provide clear scan.",
            },
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )

        # 2. Student uploads replacement document for INCOME_CERTIFICATE
        valid_pdf = b"%PDF-1.4 Fake valid PDF replacement..."
        files = {
            "file": ("new_income_cert.pdf", io.BytesIO(valid_pdf), "application/pdf")
        }
        data = {"document_type": "INCOME_CERTIFICATE"}

        upload_res = self.client.post(
            f"/api/v1/applications/{self.app1_id}/documents",
            headers={"Authorization": f"Bearer {self.student1_token}"},
            data=data,
            files=files,
        )
        self.assertEqual(upload_res.status_code, 200)

        # 3. Retrieve application details and verify correction status is RESOLVED
        get_res = self.client.get(
            f"/api/v1/applications/{self.app1_id}",
            headers={"Authorization": f"Bearer {self.student1_token}"},
        )
        self.assertEqual(get_res.status_code, 200)
        app_data = get_res.json()
        self.assertIn("correction_request", app_data)
        corr = app_data["correction_request"]
        self.assertIn("INCOME_CERTIFICATE", corr["resolved_documents"])
        self.assertEqual(corr["status"], "RESOLVED")

    def test_19_complete_physical_verification_fails_if_none_scheduled(self):
        comp_payload = {
            "result": "VERIFIED",
            "remarks": "Attempting completion without prior scheduling",
        }
        res = self.client.post(
            f"/api/v1/applications/{self.app1_id}/admin-review/physical-verification/complete",
            json=comp_payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("No scheduled physical verification appointment", res.json()["detail"])

    def test_20_schedule_physical_verification_nonexistent_application(self):
        non_existent_id = uuid.uuid4()
        payload = {
            "scheduled_date": "2026-10-15",
            "scheduled_time": "10:30 AM",
            "venue": "Room 101",
            "purpose": "Test",
            "instructions": "Bring original certificates",
        }
        response = self.client.post(
            f"/api/v1/applications/{non_existent_id}/admin-review/physical-verification",
            json=payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("Scholarship application not found", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
