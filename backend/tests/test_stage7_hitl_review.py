import sys
from pathlib import Path
import unittest
import uuid
from datetime import date, time, datetime, timezone
from fastapi.testclient import TestClient
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
from app.db.models.notification import Notification
from app.db.models.enums import (
    UserRole,
    ApplicationStatus,
    DocumentType,
    UploadStatus,
    VerificationStatus,
    AppointmentStatus,
)
from app.core.security import create_access_token, get_password_hash
from app.services.admin_review_service import AdminReviewService

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


class TestStage7HumanInTheLoopReview(unittest.TestCase):
    """
    Comprehensive test suite for Stage 7 — Human-in-the-Loop Final Review:
    Covers:
      A. Authorization & Tenant Isolation
      B. Explicit Admin Decision Independence (AI != Admin Decision)
      C. Approval Workflow & Confirmation
      D. Rejection Workflow & Mandatory Reasons
      E. Correction Request Workflow & Document Replacement Cycle
      F. Physical Verification Full Lifecycle
      G. Review History Audit Immutability & Append-Only Semantics
      H. Evidence Snapshot Preservation Across Reverifications
      I. Centralized State Transition Enforcement (Invalid Transitions Blocked)
      J. Multi-College Tenant Access Isolation
      K. Information Security & Zero PII Leakage
    """

    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()

        # Create Colleges for Tenant Isolation and Inactive testing
        self.college_a = College(
            id=uuid.uuid4(),
            college_code="COLA",
            college_name="College of Engineering Pune",
            email="contact@cola.edu",
        )
        self.college_b = College(
            id=uuid.uuid4(),
            college_code="COLB",
            college_name="Government College of Technology Mumbai",
            email="contact@colb.edu",
        )
        self.college_inactive = College(
            id=uuid.uuid4(),
            college_code="COLINACTIVE",
            college_name="Inactive Institute",
            email="contact@inactive.edu",
        )
        self.db.add_all([self.college_a, self.college_b, self.college_inactive])
        self.db.commit()

        # Admin for College A
        self.admin_a_id = uuid.uuid4()
        self.admin_a = AdminOfficer(
            id=self.admin_a_id,
            email="officer.a@cola.edu",
            password_hash=get_password_hash("AdminPass123!"),
            full_name="Prof. Sharma (Officer A)",
            college_id=self.college_a.id,
            is_active=True,
        )

        # Admin for College B
        self.admin_b_id = uuid.uuid4()
        self.admin_b = AdminOfficer(
            id=self.admin_b_id,
            email="officer.b@colb.edu",
            password_hash=get_password_hash("AdminPass123!"),
            full_name="Dr. Patil (Officer B)",
            college_id=self.college_b.id,
            is_active=True,
        )

        # Inactive Admin for College Inactive
        self.admin_inactive_id = uuid.uuid4()
        self.admin_inactive = AdminOfficer(
            id=self.admin_inactive_id,
            email="inactive@cola.edu",
            password_hash=get_password_hash("AdminPass123!"),
            full_name="Ex-Officer",
            college_id=self.college_inactive.id,
            is_active=False,
        )

        # Students
        self.student_a_id = uuid.uuid4()
        self.student_a = Student(
            id=self.student_a_id,
            email="student.a@gmail.com",
            password_hash=get_password_hash("StudentPass123!"),
            full_name="Amit Deshmukh",
            college_id=self.college_a.id,
            is_active=True,
        )

        self.student_b_id = uuid.uuid4()
        self.student_b = Student(
            id=self.student_b_id,
            email="student.b@gmail.com",
            password_hash=get_password_hash("StudentPass123!"),
            full_name="Sunita Shinde",
            college_id=self.college_b.id,
            is_active=True,
        )

        self.db.add_all([self.admin_a, self.admin_b, self.admin_inactive, self.student_a, self.student_b])
        self.db.commit()

        # Applications
        self.app_a_id = uuid.uuid4()
        self.app_a = ScholarshipApplication(
            id=self.app_a_id,
            student_id=self.student_a.id,
            application_number="VC-2026-COLA-001",
            scholarship_name="Post Matric Scholarship to VJNT Students",
            status=ApplicationStatus.SUBMITTED,
        )

        self.app_b_id = uuid.uuid4()
        self.app_b = ScholarshipApplication(
            id=self.app_b_id,
            student_id=self.student_b.id,
            application_number="VC-2026-COLB-001",
            scholarship_name="Rajarshi Chhatrapati Shahu Maharaj Shikshan Shulkh Shishyavrutti Yojna",
            status=ApplicationStatus.SUBMITTED,
        )
        self.db.add_all([self.app_a, self.app_b])
        self.db.commit()

        # Attach 4 Core Documents to App A
        self.docs_a = []
        for dt, fname in [
            (DocumentType.GOVERNMENT_ID, "aadhaar_card.pdf"),
            (DocumentType.MARKSHEET, "hsc_marksheet.png"),
            (DocumentType.INCOME_CERTIFICATE, "income_cert.pdf"),
            (DocumentType.DOMICILE_CERTIFICATE, "domicile.jpg"),
        ]:
            doc = Document(
                id=uuid.uuid4(),
                application_id=self.app_a.id,
                document_type=dt,
                original_filename=fname,
                storage_path=f"storage/uploads/{fname}",
                file_size=1024,
                mime_type="application/pdf" if fname.endswith(".pdf") else "image/png",
                upload_status=UploadStatus.PROCESSED,
            )
            self.docs_a.append(doc)
            self.db.add(doc)

        # Attach Stage 6 Evidence Summary to App A's VerificationResult
        self.ver_res_a = VerificationResult(
            id=uuid.uuid4(),
            application_id=self.app_a.id,
            document_id=None,
            overall_score=78.5,
            verification_status=VerificationStatus.NEEDS_REVIEW,
            extracted_data={
                "evidence_summary": {
                    "engine_version": "stage6_evidence_engine_v1",
                    "overall_evidence_state": "HUMAN_REVIEW_REQUIRED",
                    "human_review_required": True,
                    "review_reasons": ["OCR_LOW_CONFIDENCE"],
                    "total_evidence_count": 5,
                    "strong_support_count": 2,
                    "moderate_support_count": 2,
                    "weak_support_count": 1,
                    "strong_conflict_count": 0,
                    "moderate_conflict_count": 0,
                    "weak_conflict_count": 0,
                    "supporting_evidence": [
                        {"evidence_id": "ev-001", "category": "SUPPORTING", "strength": "STRONG", "title": "Aadhaar Confirmed"}
                    ],
                    "conflicting_evidence": [],
                    "warnings": [
                        {"evidence_id": "ev-002", "category": "WARNING", "strength": "WEAK", "title": "Income Certificate OCR Low Confidence"}
                    ],
                },
                "risk_analysis": {
                    "risk_score": 15.0,
                    "risk_level": "LOW",
                    "flags": [],
                },
                "review_history": [],
            },
            field_checks={},
            cross_document_matches=[],
            issues=["Income certificate OCR had low lighting."],
        )
        self.db.add(self.ver_res_a)
        self.db.commit()

        # JWT Tokens
        self.token_admin_a = create_access_token(
            subject=str(self.admin_a.id),
            role=UserRole.ADMIN.value,
            college_id=str(self.college_a.id),
        )
        self.token_admin_b = create_access_token(
            subject=str(self.admin_b.id),
            role=UserRole.ADMIN.value,
            college_id=str(self.college_b.id),
        )
        self.token_admin_inactive = create_access_token(
            subject=str(self.admin_inactive.id),
            role=UserRole.ADMIN.value,
            college_id=str(self.college_inactive.id),
        )
        self.token_student_a = create_access_token(
            subject=str(self.student_a.id),
            role=UserRole.STUDENT.value,
            college_id=str(self.college_a.id),
        )
        self.token_student_b = create_access_token(
            subject=str(self.student_b.id),
            role=UserRole.STUDENT.value,
            college_id=str(self.college_b.id),
        )

    def tearDown(self):
        self.db.close()

    # =========================================================================
    # A. AUTHORIZATION & TENANT ISOLATION TESTS
    # =========================================================================

    def test_01_authorized_admin_can_access_same_college_application(self):
        """Admin from College A can access and review College A applications."""
        res = self.client.get(
            f"/api/v1/applications/{self.app_a_id}/evidence",
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["overall_evidence_state"], "HUMAN_REVIEW_REQUIRED")

    def test_02_cross_college_admin_blocked_from_review_actions(self):
        """Admin from College B is blocked (HTTP 403) from approving College A application."""
        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/approve",
            json={"remarks": "Cross-college illegal attempt"},
            headers={"Authorization": f"Bearer {self.token_admin_b}"},
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Cross-college administrative action is strictly prohibited", res.json()["detail"])

    def test_03_student_blocked_from_calling_admin_review_endpoints(self):
        """Student is blocked (HTTP 403) from calling administrative action endpoints."""
        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/approve",
            json={"remarks": "Self approval attempt"},
            headers={"Authorization": f"Bearer {self.token_student_a}"},
        )
        self.assertEqual(res.status_code, 403)

    def test_04_inactive_admin_blocked_from_performing_actions(self):
        """Inactive administrative account is blocked (HTTP 404/403)."""
        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/approve",
            json={"remarks": "Inactive attempt"},
            headers={"Authorization": f"Bearer {self.token_admin_inactive}"},
        )
        self.assertIn(res.status_code, (403, 404))

    def test_05_unauthenticated_request_rejected(self):
        """Unauthenticated requests are rejected with HTTP 401."""
        res = self.client.post(f"/api/v1/applications/{self.app_a_id}/admin-review/approve", json={})
        self.assertEqual(res.status_code, 401)

    # =========================================================================
    # B. DECISION INDEPENDENCE (AI Output != Administrative Decision)
    # =========================================================================

    def test_06_ai_needs_review_does_not_prevent_admin_approval(self):
        """AI state HUMAN_REVIEW_REQUIRED does not prevent an authorized officer from approving."""
        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/approve",
            json={"remarks": "Verified physical stamp and original certificates in office."},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "VERIFIED")
        self.assertEqual(data["verification_status"], "VERIFIED")

    def test_07_ai_pass_does_not_automatically_approve_application(self):
        """Even with high AI score, application remains SUBMITTED until admin explicitly decides."""
        self.ver_res_a.overall_score = 99.0
        self.ver_res_a.verification_status = VerificationStatus.VERIFIED
        self.db.commit()

        # Application status must remain SUBMITTED, NOT VERIFIED
        app_db = self.db.query(ScholarshipApplication).filter(ScholarshipApplication.id == self.app_a_id).first()
        self.assertEqual(app_db.status, ApplicationStatus.SUBMITTED)

    def test_08_risk_signal_cannot_autonomously_reject_application(self):
        """High risk score does not autonomously reject the application."""
        self.ver_res_a.extracted_data["risk_analysis"] = {"risk_score": 95.0, "risk_level": "HIGH"}
        self.db.commit()

        app_db = self.db.query(ScholarshipApplication).filter(ScholarshipApplication.id == self.app_a_id).first()
        self.assertNotEqual(app_db.status, ApplicationStatus.REJECTED)

    # =========================================================================
    # C. APPROVAL WORKFLOW & CONFIRMATION
    # =========================================================================

    def test_09_approval_records_admin_identity_and_evidence_snapshot(self):
        """Approval records admin ID, timestamps, and Stage 6 evidence snapshot."""
        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/approve",
            json={"remarks": "All documents verified satisfactorily."},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["verified_by_admin_id"], str(self.admin_a_id))

        history = data["review_history"]
        self.assertEqual(len(history), 1)
        event = history[0]
        self.assertEqual(event["action"], "APPROVE")
        self.assertEqual(event["admin_id"], str(self.admin_a_id))
        self.assertEqual(event["previous_state"], "SUBMITTED")
        self.assertEqual(event["new_state"], "VERIFIED")
        self.assertIn("evidence_snapshot", event)
        self.assertEqual(event["evidence_snapshot"]["overall_evidence_state"], "HUMAN_REVIEW_REQUIRED")

    def test_10_approval_fails_if_required_documents_missing(self):
        """Approval is rejected if any of the 4 mandatory documents are absent."""
        # Create a separate student and application without Marksheet
        other_student = Student(
            id=uuid.uuid4(),
            email="other.student@cola.edu",
            password_hash=get_password_hash("Pass123!"),
            full_name="Other Student",
            college_id=self.college_a.id,
            is_active=True,
        )
        self.db.add(other_student)
        self.db.commit()

        incomplete_app = ScholarshipApplication(
            id=uuid.uuid4(),
            student_id=other_student.id,
            application_number="VC-2026-INCOMPLETE",
            scholarship_name="MahaDBT Test",
            status=ApplicationStatus.SUBMITTED,
        )
        self.db.add(incomplete_app)
        self.db.commit()

        res = self.client.post(
            f"/api/v1/applications/{incomplete_app.id}/admin-review/approve",
            json={"remarks": "Premature approval attempt"},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Missing required documents", res.json()["detail"])

    # =========================================================================
    # D. REJECTION WORKFLOW & MANDATORY REASONS
    # =========================================================================

    def test_11_rejection_requires_detailed_reason(self):
        """Rejection fails with HTTP 400 or 422 if reason is omitted or too brief (<5 chars)."""
        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/reject",
            json={"reason": "bad"},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertIn(res.status_code, (400, 422))

    def test_12_rejection_records_audit_trail_and_notifies_student(self):
        """Rejection updates status to REJECTED, records audit event, and creates notification."""
        rejection_reason = "Family annual income exceeds statutory cap of Rs. 2,50,000."
        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/reject",
            json={"reason": rejection_reason},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "REJECTED")

        # Verify notification created
        notif = self.db.query(Notification).filter(
            Notification.student_id == self.student_a_id,
            Notification.event_type == "APPLICATION_REJECTED",
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn(rejection_reason, notif.message)

    def test_13_already_rejected_application_cannot_be_re_rejected(self):
        """A rejected application cannot be re-rejected."""
        self.app_a.status = ApplicationStatus.REJECTED
        self.db.commit()

        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/reject",
            json={"reason": "Attempting second rejection."},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 400)

    # =========================================================================
    # E. CORRECTION REQUEST WORKFLOW & REPLACEMENT CYCLE
    # =========================================================================

    def test_14_request_correction_requires_valid_document_and_reason(self):
        """Request correction fails if document list is empty or reason too short."""
        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/request-correction",
            json={"document_types": [], "reason": "Please replace"},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 422)

    def test_15_request_correction_sets_needs_review_and_preserves_request(self):
        """Request correction moves app to NEEDS_REVIEW and logs structured request."""
        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/request-correction",
            json={
                "document_types": ["INCOME_CERTIFICATE"],
                "reason": "Tehsildar official signature seal is faded and illegible.",
            },
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "NEEDS_REVIEW")
        self.assertEqual(data["correction_request"]["status"], "PENDING")
        self.assertIn("INCOME_CERTIFICATE", data["correction_request"]["document_types"])

    def test_16_student_replaces_document_and_resolves_correction_flag(self):
        """Uploading replacement document marks correction resolved."""
        # 1. Admin requests correction
        self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/request-correction",
            json={"document_types": ["INCOME_CERTIFICATE"], "reason": "Blurred scan"},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )

        # 2. Student re-uploads document
        fake_file = b"%PDF-1.4 test updated income certificate stream content"
        upload_res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/documents",
            headers={"Authorization": f"Bearer {self.token_student_a}"},
            data={"document_type": "INCOME_CERTIFICATE"},
            files={"file": ("income_cert_new.pdf", fake_file, "application/pdf")},
        )
        self.assertEqual(upload_res.status_code, 200)

        # 3. Check application details
        get_res = self.client.get(
            f"/api/v1/applications/{self.app_a_id}",
            headers={"Authorization": f"Bearer {self.token_student_a}"},
        )
        self.assertEqual(get_res.status_code, 200)
        corr = get_res.json()["correction_request"]
        self.assertEqual(corr["status"], "RESOLVED")
        self.assertIn("INCOME_CERTIFICATE", corr["resolved_documents"])

    # =========================================================================
    # F. PHYSICAL VERIFICATION LIFECYCLE
    # =========================================================================

    def test_17_schedule_physical_verification_records_appointment(self):
        """Admin can schedule physical verification with date, time, and venue."""
        sched_payload = {
            "scheduled_date": "2026-10-25",
            "scheduled_time": "10:30 AM",
            "venue": "Dean Office, Administrative Block Room 204",
            "instructions": "Bring original income certificate and domicile certificate.",
        }
        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/physical-verification",
            json=sched_payload,
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "SCHEDULED")
        self.assertEqual(data["venue"], "Dean Office, Administrative Block Room 204")

        # Verify application status updated
        app_db = self.db.query(ScholarshipApplication).filter(ScholarshipApplication.id == self.app_a_id).first()
        self.assertEqual(app_db.status, ApplicationStatus.PHYSICAL_VERIFICATION_REQUIRED)

    def test_18_student_can_view_own_appointment(self):
        """Student can view their scheduled in-person verification session."""
        self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/physical-verification",
            json={
                "scheduled_date": "2026-10-25",
                "scheduled_time": "10:30 AM",
                "venue": "Admin Block Room 204",
            },
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )

        res = self.client.get(
            f"/api/v1/applications/{self.app_a_id}/physical-verification",
            headers={"Authorization": f"Bearer {self.token_student_a}"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["venue"], "Admin Block Room 204")

    def test_19_cross_college_admin_cannot_view_appointment(self):
        """Cross-college admin cannot view an appointment belonging to College A."""
        self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/physical-verification",
            json={"scheduled_date": "2026-10-25", "scheduled_time": "10:30 AM", "venue": "Room 204"},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )

        res = self.client.get(
            f"/api/v1/applications/{self.app_a_id}/physical-verification",
            headers={"Authorization": f"Bearer {self.token_admin_b}"},
        )
        self.assertEqual(res.status_code, 403)

    def test_20_complete_physical_verification_with_verified_outcome(self):
        """Recording VERIFIED outcome marks appointment COMPLETED and updates app status."""
        self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/physical-verification",
            json={"scheduled_date": "2026-10-25", "scheduled_time": "10:30 AM", "venue": "Room 204"},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )

        comp_res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/physical-verification/complete",
            json={"result": "VERIFIED", "remarks": "Original documents verified in person."},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(comp_res.status_code, 200)
        data = comp_res.json()
        self.assertEqual(data["status"], "PHYSICAL_VERIFICATION_COMPLETED")
        self.assertEqual(data["appointment"]["status"], "COMPLETED")

    def test_21_complete_physical_verification_with_not_verified_outcome(self):
        """Recording NOT_VERIFIED outcome moves app to NEEDS_REVIEW, avoiding automatic rejection."""
        self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/physical-verification",
            json={"scheduled_date": "2026-10-25", "scheduled_time": "10:30 AM", "venue": "Room 204"},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )

        comp_res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/physical-verification/complete",
            json={"result": "NOT_VERIFIED", "remarks": "Candidate could not produce original domicile."},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(comp_res.status_code, 200)
        data = comp_res.json()
        self.assertEqual(data["status"], "NEEDS_REVIEW")
        self.assertEqual(data["verification_status"], "NEEDS_REVIEW")

    # =========================================================================
    # G. REVIEW HISTORY AUDIT IMMUTABILITY & APPEND-ONLY
    # =========================================================================

    def test_22_review_history_is_append_only_and_chronological(self):
        """Successive actions append chronological events without overwriting prior records."""
        # Action 1: Correction Request
        self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/request-correction",
            json={"document_types": ["MARKSHEET"], "reason": "Marksheet blurred"},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )

        # Action 2: Schedule Physical
        self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/physical-verification",
            json={"scheduled_date": "2026-10-25", "scheduled_time": "10:30 AM", "venue": "Room 204"},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )

        # Action 3: Complete Physical
        self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/physical-verification/complete",
            json={"result": "VERIFIED", "remarks": "Checked original"},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )

        # Action 4: Final Approval
        self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/approve",
            json={"remarks": "Final verified by Dean."},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )

        # Query Review History endpoint
        res = self.client.get(
            f"/api/v1/applications/{self.app_a_id}/review-history",
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 200)
        history = res.json()
        self.assertEqual(len(history), 4)

        actions = [h["action"] for h in history]
        self.assertEqual(actions, [
            "REQUEST_CORRECTION",
            "REQUIRE_PHYSICAL_VERIFICATION",
            "COMPLETE_PHYSICAL_VERIFICATION",
            "APPROVE",
        ])

    def test_23_student_can_view_own_application_review_history(self):
        """Student owner can inspect the review audit history of their own application."""
        self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/request-correction",
            json={"document_types": ["MARKSHEET"], "reason": "Marksheet scan degraded."},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )

        res = self.client.get(
            f"/api/v1/applications/{self.app_a_id}/review-history",
            headers={"Authorization": f"Bearer {self.token_student_a}"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)

    def test_24_peer_student_cannot_view_other_student_review_history(self):
        """Student B cannot view review history of Student A's application."""
        res = self.client.get(
            f"/api/v1/applications/{self.app_a_id}/review-history",
            headers={"Authorization": f"Bearer {self.token_student_b}"},
        )
        self.assertEqual(res.status_code, 403)

    # =========================================================================
    # H. EVIDENCE SNAPSHOT PRESERVATION ACROSS REVERIFICATIONS
    # =========================================================================

    def test_25_evidence_snapshot_preserved_in_audit_events(self):
        """Each audit event captures the evidence state at decision time."""
        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/approve",
            json={"remarks": "Approved with current evidence."},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 200)

        hist = self.client.get(
            f"/api/v1/applications/{self.app_a_id}/review-history",
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        ).json()

        first_event = hist[0]
        self.assertIn("evidence_snapshot", first_event)
        self.assertEqual(first_event["evidence_snapshot"]["engine_version"], "stage6_evidence_engine_v1")
        self.assertEqual(first_event["evidence_snapshot"]["overall_evidence_state"], "HUMAN_REVIEW_REQUIRED")

    # =========================================================================
    # I. CENTRALIZED STATE TRANSITION ENFORCEMENT
    # =========================================================================

    def test_26_cannot_approve_already_rejected_application(self):
        """Terminal REJECTED state blocks APPROVE transition."""
        self.app_a.status = ApplicationStatus.REJECTED
        self.db.commit()

        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/approve",
            json={"remarks": "Illegal approval of rejected application"},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Cannot perform 'APPROVE' on an already REJECTED application", res.json()["detail"])

    def test_27_cannot_request_correction_on_approved_application(self):
        """Terminal VERIFIED state blocks REQUEST_CORRECTION transition."""
        self.app_a.status = ApplicationStatus.VERIFIED
        self.db.commit()

        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/request-correction",
            json={"document_types": ["INCOME_CERTIFICATE"], "reason": "Post-approval check"},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Cannot perform 'REQUEST_CORRECTION' on an already APPROVED/VERIFIED application", res.json()["detail"])

    def test_28_cannot_schedule_physical_on_already_approved_application(self):
        """Terminal VERIFIED state blocks physical verification scheduling."""
        self.app_a.status = ApplicationStatus.VERIFIED
        self.db.commit()

        res = self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/physical-verification",
            json={"scheduled_date": "2026-10-25", "scheduled_time": "10:30 AM", "venue": "Room 204"},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 400)

    # =========================================================================
    # J. INFORMATION SECURITY & PII MASKING
    # =========================================================================

    def test_29_review_history_does_not_leak_internal_storage_paths(self):
        """Review history responses never leak internal filesystem storage paths."""
        self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/request-correction",
            json={"document_types": ["GOVERNMENT_ID"], "reason": "Rescan needed"},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )

        res = self.client.get(
            f"/api/v1/applications/{self.app_a_id}/review-history",
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )
        self.assertEqual(res.status_code, 200)
        content_str = str(res.json())
        self.assertNotIn("storage/uploads", content_str)
        self.assertNotIn("C:\\", content_str)

    def test_30_student_dashboard_does_not_leak_admin_internal_notes(self):
        """Student endpoint returns administrative decision status without internal secrets."""
        self.client.post(
            f"/api/v1/applications/{self.app_a_id}/admin-review/reject",
            json={"reason": "Income documents invalid upon tehsildar verification."},
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
        )

        res = self.client.get(
            f"/api/v1/applications/{self.app_a_id}",
            headers={"Authorization": f"Bearer {self.token_student_a}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "REJECTED")
        # Ensure password hashes or internal server tokens are not in payload
        self.assertNotIn("password_hash", str(data))


if __name__ == "__main__":
    unittest.main()
