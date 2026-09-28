import io
import sys
import unittest
import uuid
from datetime import date, datetime, timezone
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
from app.db.models.appointment import PhysicalVerificationAppointment
from app.db.models.enums import (
    UserRole,
    ApplicationStatus,
    DocumentType,
    UploadStatus,
    VerificationStatus,
    AppointmentStatus,
)
from app.core.security import get_password_hash

# Isolated in-memory database for clean, deterministic E2E test execution
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


class TestEndToEndLifecycle(unittest.TestCase):
    """
    Complete End-to-End Integration Test for VeriCampus AI:
    Tests the real student -> upload -> AI verification -> admin review ->
    correction -> replacement -> re-verification -> physical verification ->
    final decision workflow.
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

        # Seed College 1 (DEMO001) & College 2 (DEMO002)
        self.college1_id = uuid.uuid4()
        self.college2_id = uuid.uuid4()

        c1 = College(
            id=self.college1_id,
            college_name="Demo Engineering College",
            college_code="DEMO001",
            email="contact@demo001.edu",
            is_active=True,
        )
        c2 = College(
            id=self.college2_id,
            college_name="Demo Institute of Technology",
            college_code="DEMO002",
            email="contact@demo002.edu",
            is_active=True,
        )
        self.db.add_all([c1, c2])

        # Seed Admin for College 1
        self.admin1_id = uuid.uuid4()
        admin1 = AdminOfficer(
            id=self.admin1_id,
            college_id=self.college1_id,
            full_name="Chief Admin DEMO001",
            email="admin@demo001.edu",
            password_hash=get_password_hash("AdminPassword123!"),
            department="Scholarship Cell",
            designation="Chief Verification Officer",
            is_active=True,
        )
        # Seed Admin for College 2 (Cross-College isolation check)
        self.admin2_id = uuid.uuid4()
        admin2 = AdminOfficer(
            id=self.admin2_id,
            college_id=self.college2_id,
            full_name="Chief Admin DEMO002",
            email="admin@demo002.edu",
            password_hash=get_password_hash("AdminPassword123!"),
            department="Scholarship Cell",
            designation="Verification Officer",
            is_active=True,
        )
        self.db.add_all([admin1, admin2])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def log_step(self, step_num, title, details=""):
        print(f"\n[{step_num:02d}] {title}")
        if details:
            print(f"     -> {details}")

    def test_complete_e2e_lifecycle(self):
        """
        Executes the entire student-to-admin scholarship lifecycle step by step.
        """
        print("\n" + "=" * 80)
        print("STARTING COMPLETE END-TO-END VERIFICATION LIFECYCLE TEST")
        print("=" * 80)

        # ---------------------------------------------------------------------
        # STEP 1: Student Registration
        # ---------------------------------------------------------------------
        self.log_step(1, "Student Registration (POST /api/v1/auth/student/register)")
        student_reg_data = {
            "college_code": "DEMO001",
            "full_name": "Rajesh Kumar Patil",
            "email": "rajesh.patil@example.edu",
            "password": "StudentPassword123!",
            "phone_number": "9876543210",
            "government_id_number": "1234-5678-9012",
            "date_of_birth": "2004-05-14",
            "address": "Pune, Maharashtra, India",
        }
        res = self.client.post("/api/v1/auth/student/register", json=student_reg_data)
        self.assertEqual(res.status_code, 201, f"Registration failed: {res.text}")
        reg_json = res.json()
        self.assertEqual(reg_json["email"], "rajesh.patil@example.edu")
        self.assertEqual(reg_json["full_name"], "Rajesh Kumar Patil")
        print(f"     Status: HTTP {res.status_code} | Student ID: {reg_json['id']}")

        # ---------------------------------------------------------------------
        # STEP 2: Student Login
        # ---------------------------------------------------------------------
        self.log_step(2, "Student Login (POST /api/v1/auth/login)")
        login_data = {
            "email": "rajesh.patil@example.edu",
            "password": "StudentPassword123!",
            "college_code": "DEMO001",
        }
        res = self.client.post("/api/v1/auth/login", json=login_data)
        self.assertEqual(res.status_code, 200, f"Login failed: {res.text}")
        token_data = res.json()
        self.assertIn("access_token", token_data)
        student_token = token_data["access_token"]
        student_headers = {"Authorization": f"Bearer {student_token}"}
        print(f"     Status: HTTP {res.status_code} | Bearer Token Issued")

        # Verify Student Profile (/auth/me)
        res = self.client.get("/api/v1/auth/me", headers=student_headers)
        self.assertEqual(res.status_code, 200)
        profile = res.json()
        self.assertEqual(profile["role"], "STUDENT")
        self.assertEqual(profile["email"], "rajesh.patil@example.edu")
        print(f"     Identity Confirmed: {profile['full_name']} (Role: {profile['role']})")

        # ---------------------------------------------------------------------
        # STEP 3: Available Scholarship Schemes & Application Creation
        # ---------------------------------------------------------------------
        self.log_step(3, "Browse Schemes & Create Application (POST /api/v1/applications)")
        res = self.client.get("/api/v1/applications/schemes")
        self.assertEqual(res.status_code, 200)
        schemes = res.json()["schemes"]
        self.assertGreater(len(schemes), 0)
        selected_scheme = schemes[0]
        print(f"     Retrieved {len(schemes)} official schemes. Selected: '{selected_scheme}'")

        # Create Application
        res = self.client.post(
            "/api/v1/applications",
            headers=student_headers,
            json={"scholarship_name": selected_scheme},
        )
        self.assertIn(res.status_code, [200, 201], f"Application creation failed: {res.text}")
        app_data = res.json()
        app_id = app_data["id"]
        app_number = app_data["application_number"]
        self.assertEqual(app_data["status"], "DRAFT")
        self.assertEqual(app_data["documents_uploaded_count"], 0)
        print(f"     Status: HTTP {res.status_code} | App ID: {app_id} | App Number: {app_number} (DRAFT)")

        # ---------------------------------------------------------------------
        # STEP 4: Upload All 4 Core Required Documents
        # ---------------------------------------------------------------------
        self.log_step(4, "Upload 4 Core Documents (POST /api/v1/applications/{id}/documents)")
        doc_specs = [
            ("GOVERNMENT_ID", "aadhaar_card.pdf", b"%PDF-1.4 Fake Government Aadhaar Card for Testing", "application/pdf"),
            ("MARKSHEET", "hsc_marksheet.png", b"\x89PNG\r\n\x1a\nFake PNG Marksheet Content", "image/png"),
            ("INCOME_CERTIFICATE", "income_cert.pdf", b"%PDF-1.4 Fake Tahsildar Income Certificate", "application/pdf"),
            ("DOMICILE_CERTIFICATE", "domicile.jpg", b"\xff\xd8\xffFake JPEG Domicile Certificate", "image/jpeg"),
        ]

        uploaded_doc_ids = {}
        for doc_type, fname, content, ctype in doc_specs:
            files = {"file": (fname, io.BytesIO(content), ctype)}
            data = {"document_type": doc_type}
            res = self.client.post(
                f"/api/v1/applications/{app_id}/documents",
                headers=student_headers,
                data=data,
                files=files,
            )
            self.assertEqual(res.status_code, 200, f"Upload of {doc_type} failed: {res.text}")
            resp_data = res.json()
            # Find the uploaded document
            matching_doc = next(d for d in resp_data["documents"] if d["document_type"] == doc_type)
            uploaded_doc_ids[doc_type] = matching_doc["id"]
            print(f"     Uploaded {doc_type:20} -> {fname:20} | ID: {matching_doc['id']}")

        # Confirm all 4 documents uploaded
        res = self.client.get("/api/v1/applications/my-application", headers=student_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["documents_uploaded_count"], 4)
        print(f"     Documents Count: 4 / 4 Complete")

        # ---------------------------------------------------------------------
        # STEP 5: Trigger AI Verification Pipeline
        # ---------------------------------------------------------------------
        self.log_step(5, "Execute AI Verification Pipeline (POST /api/v1/applications/{id}/verify)")
        res = self.client.post(f"/api/v1/applications/{app_id}/verify", headers=student_headers)
        self.assertEqual(res.status_code, 200, f"Verification failed: {res.text}")
        ver_resp = res.json()
        overall_score = ver_resp.get("overall_score")
        ver_status = ver_resp.get("verification_status")
        self.assertIsNotNone(overall_score)
        self.assertIn(ver_status, ["NEEDS_REVIEW", "VERIFIED"])
        print(f"     Status: HTTP {res.status_code} | AI Status: {ver_status} | Overall Score: {overall_score:.1f}%")

        # Inspect Verification Result
        res = self.client.get(f"/api/v1/applications/{app_id}/verification-result", headers=student_headers)
        self.assertEqual(res.status_code, 200)
        ver_result_data = res.json()
        self.assertIn("field_checks", ver_result_data)
        self.assertIn("extracted_data", ver_result_data)

        # Confirm Risk Analysis is present and non-empty
        risk = ver_result_data.get("extracted_data", {}).get("risk_analysis")
        self.assertIsNotNone(risk)
        self.assertIn("risk_score", risk)
        self.assertIn("risk_level", risk)
        print(f"     Risk Analysis Model: Risk Score={risk['risk_score']}/100 (Level: {risk['risk_level']})")

        # Verify No Storage Path Leakage
        res_str = res.text
        self.assertNotIn("storage/applications", res_str)
        self.assertNotIn("storage_path", res_str)
        print(f"     Security Check: No internal filesystem storage paths leaked in response")

        # ---------------------------------------------------------------------
        # STEP 6: Admin Login & Application Queue Review
        # ---------------------------------------------------------------------
        self.log_step(6, "Admin Login & Applications Queue Review (GET /api/v1/applications)")
        admin_login_data = {
            "email": "admin@demo001.edu",
            "password": "AdminPassword123!",
            "college_code": "DEMO001",
        }
        res = self.client.post("/api/v1/auth/admin/login", json=admin_login_data)
        self.assertEqual(res.status_code, 200, f"Admin login failed: {res.text}")
        admin_token = res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print(f"     Status: HTTP {res.status_code} | Admin Bearer Token Issued")

        # List College Applications
        res = self.client.get("/api/v1/applications", headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        college_apps = res.json()
        self.assertGreaterEqual(len(college_apps), 1)
        found_app = next((a for a in college_apps if a["id"] == app_id), None)
        self.assertIsNotNone(found_app, "Submitted application not found in Admin college queue")
        self.assertEqual(found_app["application_number"], app_number)
        self.assertEqual(found_app["student_name"], "Rajesh Kumar Patil")
        print(f"     Queue Verified: Application {app_number} found in College DEMO001 queue")

        # Admin View Application Details
        res = self.client.get(f"/api/v1/applications/{app_id}", headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["documents"]), 4)

        # Admin Stream Authenticated Document Binary Blob
        first_doc_id = uploaded_doc_ids["GOVERNMENT_ID"]
        res = self.client.get(f"/api/v1/applications/{app_id}/documents/{first_doc_id}/file", headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.content.startswith(b"%PDF-1.4"))
        self.assertEqual(res.headers.get("content-type"), "application/pdf")
        print(f"     Document Streaming Verified: {len(res.content)} bytes streamed securely via binary blob")

        # ---------------------------------------------------------------------
        # STEP 7: Admin Requests Document Correction (Human-in-the-Loop Action 1)
        # ---------------------------------------------------------------------
        self.log_step(7, "Admin Requests Document Correction (POST /api/v1/applications/{id}/admin-review/request-correction)")
        correction_payload = {
            "document_types": ["MARKSHEET", "INCOME_CERTIFICATE"],
            "reason": "Income certificate has expired; Marksheet image is blurred and illegible.",
        }
        res = self.client.post(
            f"/api/v1/applications/{app_id}/admin-review/request-correction",
            headers=admin_headers,
            json=correction_payload,
        )
        self.assertEqual(res.status_code, 200, f"Correction request failed: {res.text}")
        cor_resp = res.json()
        self.assertEqual(cor_resp["status"], "NEEDS_REVIEW")
        cr_info = cor_resp["correction_request"]
        self.assertEqual(cr_info["status"], "PENDING")
        self.assertIn("MARKSHEET", cr_info["document_types"])
        self.assertIn("INCOME_CERTIFICATE", cr_info["document_types"])
        print(f"     Status: HTTP {res.status_code} | App Status -> NEEDS_REVIEW | Flagged: {cr_info['document_types']}")

        # Student checks application -> sees active correction request
        res = self.client.get("/api/v1/applications/my-application", headers=student_headers)
        self.assertEqual(res.status_code, 200)
        stu_app = res.json()
        self.assertIsNotNone(stu_app.get("correction_request"))
        self.assertEqual(stu_app["correction_request"]["status"], "PENDING")
        print(f"     Student Visibility Confirmed: Student sees correction request with reason: '{cr_info['reason']}'")

        # ---------------------------------------------------------------------
        # STEP 8: Student Replaces Flagged Documents & Auto-Resolution Tracking
        # ---------------------------------------------------------------------
        self.log_step(8, "Student Replaces Flagged Documents & Auto-Resolution Tracking")

        # Replace Document 1: MARKSHEET
        rescan_marksheet = b"\x89PNG\r\n\x1a\nUpdated Crystal Clear Marksheet Scan Content"
        files = {"file": ("marksheet_rescanned.png", io.BytesIO(rescan_marksheet), "image/png")}
        data = {"document_type": "MARKSHEET"}
        res = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers=student_headers,
            data=data,
            files=files,
        )
        self.assertEqual(res.status_code, 200)
        print("     Uploaded replacement MARKSHEET")

        # Check partial resolution state
        res = self.client.get("/api/v1/applications/my-application", headers=student_headers)
        stu_app = res.json()
        cr = stu_app["correction_request"]
        self.assertEqual(cr["status"], "PENDING", "Should remain PENDING because INCOME_CERTIFICATE is still pending")
        self.assertIn("MARKSHEET", cr.get("resolved_documents", []))
        print(f"     Partial Resolution Tracked: Resolved={cr.get('resolved_documents')} | Status: {cr['status']}")

        # Replace Document 2: INCOME_CERTIFICATE
        updated_income = b"%PDF-1.4 Valid Updated Income Certificate for FY 2026-2027"
        files = {"file": ("income_cert_2026.pdf", io.BytesIO(updated_income), "application/pdf")}
        data = {"document_type": "INCOME_CERTIFICATE"}
        res = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers=student_headers,
            data=data,
            files=files,
        )
        self.assertEqual(res.status_code, 200)
        print("     Uploaded replacement INCOME_CERTIFICATE")

        # Check full resolution state -> MUST be RESOLVED!
        res = self.client.get("/api/v1/applications/my-application", headers=student_headers)
        stu_app = res.json()
        cr = stu_app["correction_request"]
        self.assertEqual(cr["status"], "RESOLVED", "Should automatically transition to RESOLVED when all flagged documents are replaced!")
        self.assertIn("MARKSHEET", cr.get("resolved_documents", []))
        self.assertIn("INCOME_CERTIFICATE", cr.get("resolved_documents", []))
        print(f"     Full Auto-Resolution Confirmed: Status -> RESOLVED | Replaced: {cr['resolved_documents']}")

        # ---------------------------------------------------------------------
        # STEP 9: Re-Verification After Replacements
        # ---------------------------------------------------------------------
        self.log_step(9, "Re-run AI Verification on Updated Documents (POST /api/v1/applications/{id}/verify)")
        res = self.client.post(f"/api/v1/applications/{app_id}/verify", headers=student_headers)
        self.assertEqual(res.status_code, 200)
        re_ver = res.json()
        print(f"     Re-verification Completed: Score={re_ver['overall_score']:.1f}% | Status: {re_ver['verification_status']}")

        # ---------------------------------------------------------------------
        # STEP 10: Admin Requires Physical Verification (Human-in-the-Loop Action 2)
        # ---------------------------------------------------------------------
        self.log_step(10, "Admin Schedules Physical Verification Meeting (POST /api/v1/applications/{id}/admin-review/physical-verification)")
        phys_payload = {
            "scheduled_date": "2026-09-25",
            "scheduled_time": "10:30",
            "venue": "Administrative Block, Room 204, Main Campus",
            "purpose": "Verify original certificates & signature check",
            "instructions": "Bring original Government ID, 10th/12th Marksheets, Tahsildar Income, and Domicile Certificate.",
        }
        res = self.client.post(
            f"/api/v1/applications/{app_id}/admin-review/physical-verification",
            headers=admin_headers,
            json=phys_payload,
        )
        self.assertEqual(res.status_code, 200, f"Scheduling physical verification failed: {res.text}")
        phys_resp = res.json()
        self.assertEqual(phys_resp["application_status"], "PHYSICAL_VERIFICATION_REQUIRED")
        self.assertEqual(phys_resp["status"], "SCHEDULED")
        self.assertEqual(phys_resp["scheduled_date"], "2026-09-25")
        self.assertEqual(phys_resp["scheduled_time"], "10:30")
        print(f"     Status: HTTP {res.status_code} | App Status -> PHYSICAL_VERIFICATION_REQUIRED | Date: {phys_resp['scheduled_date']} at {phys_resp['scheduled_time']}")

        # Student Retrieves Appointment (/my-application/physical-verification)
        res = self.client.get("/api/v1/applications/my-application/physical-verification", headers=student_headers)
        self.assertEqual(res.status_code, 200)
        stu_appt = res.json()
        self.assertEqual(stu_appt["venue"], phys_payload["venue"])
        self.assertEqual(stu_appt["status"], "SCHEDULED")
        print(f"     Student Appointment Access Confirmed: Venue '{stu_appt['venue']}'")

        # Admin Retrieves Appointment (/applications/{id}/physical-verification)
        res = self.client.get(f"/api/v1/applications/{app_id}/physical-verification", headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], stu_appt["id"])
        print(f"     Admin Appointment Access Confirmed: Match Appointment ID {stu_appt['id']}")

        # ---------------------------------------------------------------------
        # STEP 11: Admin Records Physical Verification Completion
        # ---------------------------------------------------------------------
        self.log_step(11, "Admin Records Physical Verification Outcome (POST .../complete)")
        comp_payload = {
            "result": "VERIFIED",
            "remarks": "Original Government ID, Marksheet, Tahsildar Income Certificate, and Maharashtra Domicile inspected in person and found authentic.",
        }
        res = self.client.post(
            f"/api/v1/applications/{app_id}/admin-review/physical-verification/complete",
            headers=admin_headers,
            json=comp_payload,
        )
        self.assertEqual(res.status_code, 200, f"Complete physical verification failed: {res.text}")
        comp_resp = res.json()
        self.assertEqual(comp_resp["status"], "PHYSICAL_VERIFICATION_COMPLETED")
        self.assertEqual(comp_resp["appointment"]["status"], "COMPLETED")
        print(f"     Status: HTTP {res.status_code} | Appointment -> COMPLETED | App Status -> PHYSICAL_VERIFICATION_COMPLETED")

        # ---------------------------------------------------------------------
        # STEP 12: Admin Approves Application (Final Decision - Action 3)
        # ---------------------------------------------------------------------
        self.log_step(12, "Admin Final Approval (POST /api/v1/applications/{id}/admin-review/approve)")
        approve_payload = {
            "remarks": "All eligibility criteria satisfied, corrections verified, and physical inspection completed. Application officially approved.",
            "notes": "Approved for 2026 academic scholarship award.",
        }
        res = self.client.post(
            f"/api/v1/applications/{app_id}/admin-review/approve",
            headers=admin_headers,
            json=approve_payload,
        )
        self.assertEqual(res.status_code, 200, f"Approval failed: {res.text}")
        appr_resp = res.json()
        self.assertEqual(appr_resp["status"], "VERIFIED")
        self.assertEqual(appr_resp["verification_status"], "VERIFIED")
        print(f"     Status: HTTP {res.status_code} | App Status -> VERIFIED | Verification Status -> VERIFIED")

        # Student Confirms Final Status
        res = self.client.get("/api/v1/applications/my-application", headers=student_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "VERIFIED")
        print(f"     Student Confirms Final Approval: Status == 'VERIFIED'")

        # ---------------------------------------------------------------------
        # STEP 13: Comprehensive Audit Trail Verification
        # ---------------------------------------------------------------------
        self.log_step(13, "Inspect Administrative Review Audit Trail")
        res = self.client.get(f"/api/v1/applications/{app_id}/verification-result", headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        vr_data = res.json()
        review_history = vr_data.get("extracted_data", {}).get("review_history", [])
        self.assertGreaterEqual(len(review_history), 4, "Should have at least 4 audit events")

        action_types = [entry["action"] for entry in review_history]
        self.assertIn("REQUEST_CORRECTION", action_types)
        self.assertIn("REQUIRE_PHYSICAL_VERIFICATION", action_types)
        self.assertIn("COMPLETE_PHYSICAL_VERIFICATION", action_types)
        self.assertIn("APPROVE", action_types)
        print(f"     Audit Trail Verified: {len(review_history)} events logged chronologically:")
        for entry in review_history:
            print(f"       • [{entry.get('timestamp')}] Action: {entry.get('action')} by Admin {entry.get('admin_id')}")

        # ---------------------------------------------------------------------
        # STEP 14: Tenant Isolation & Security Verification
        # ---------------------------------------------------------------------
        self.log_step(14, "Multi-College Tenant Isolation & Peer Access Control Checks")

        # Login as Admin 2 (College DEMO002)
        admin2_login = {
            "email": "admin@demo002.edu",
            "password": "AdminPassword123!",
            "college_code": "DEMO002",
        }
        res = self.client.post("/api/v1/auth/admin/login", json=admin2_login)
        self.assertEqual(res.status_code, 200)
        admin2_token = res.json()["access_token"]
        admin2_headers = {"Authorization": f"Bearer {admin2_token}"}

        # Cross-College Admin Attempts Access to College 1 Application
        res = self.client.get(f"/api/v1/applications/{app_id}", headers=admin2_headers)
        self.assertEqual(res.status_code, 403, "Cross-college admin MUST NOT view another college's application")

        # Cross-College Admin Attempts Approval
        res = self.client.post(
            f"/api/v1/applications/{app_id}/admin-review/approve",
            headers=admin2_headers,
            json={"remarks": "Malicious cross-college approval"},
        )
        self.assertEqual(res.status_code, 403, "Cross-college admin MUST NOT approve another college's application")

        # Cross-College Admin Attempts to View Physical Appointment
        res = self.client.get(f"/api/v1/applications/{app_id}/physical-verification", headers=admin2_headers)
        self.assertEqual(res.status_code, 403, "Cross-college admin MUST NOT view another college's appointment")
        print("     Cross-College Isolation: HTTP 403 Forbidden verified on all endpoints")

        # Peer Student Isolation Check: Register Student 2
        student2_reg = {
            "college_code": "DEMO001",
            "full_name": "Sneha Patil",
            "email": "sneha.patil@example.edu",
            "password": "Password123!",
        }
        res = self.client.post("/api/v1/auth/student/register", json=student2_reg)
        self.assertEqual(res.status_code, 201)

        res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "sneha.patil@example.edu", "password": "Password123!", "college_code": "DEMO001"},
        )
        student2_token = res.json()["access_token"]
        student2_headers = {"Authorization": f"Bearer {student2_token}"}

        # Peer student attempts to view Rajesh's application
        res = self.client.get(f"/api/v1/applications/{app_id}", headers=student2_headers)
        self.assertEqual(res.status_code, 403, "Student MUST NOT view peer student's application")

        # Peer student attempts to view Rajesh's appointment
        res = self.client.get(f"/api/v1/applications/{app_id}/physical-verification", headers=student2_headers)
        self.assertEqual(res.status_code, 403, "Student MUST NOT view peer student's appointment")
        print("     Peer Student Isolation: HTTP 403 Forbidden verified on peer access attempts")

        print("\n" + "=" * 80)
        print("ALL 14 END-TO-END LIFECYCLE STEPS PASSED SUCCESSFULLY WITH 100% SUCCESS RATE")
        print("=" * 80)

    def test_e2e_rejection_lifecycle(self):
        """
        Executes an alternative lifecycle ending in administrative rejection.
        """
        print("\n" + "=" * 80)
        print("TESTING ADMINISTRATIVE REJECTION LIFECYCLE")
        print("=" * 80)

        # Register Student
        student_data = {
            "college_code": "DEMO001",
            "full_name": "Pooja Sharma",
            "email": "pooja.sharma@example.edu",
            "password": "Password123!",
        }
        res = self.client.post("/api/v1/auth/student/register", json=student_data)
        self.assertEqual(res.status_code, 201)

        res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "pooja.sharma@example.edu", "password": "Password123!", "college_code": "DEMO001"},
        )
        student_token = res.json()["access_token"]
        student_headers = {"Authorization": f"Bearer {student_token}"}

        # Create Application
        schemes = self.client.get("/api/v1/applications/schemes").json()["schemes"]
        res = self.client.post(
            "/api/v1/applications",
            headers=student_headers,
            json={"scholarship_name": schemes[0]},
        )
        self.assertIn(res.status_code, [200, 201])
        app_id = res.json()["id"]

        # Upload 4 documents
        doc_specs = [
            ("GOVERNMENT_ID", "aadhaar.pdf", b"%PDF-1.4 Fake Aadhaar", "application/pdf"),
            ("MARKSHEET", "marks.png", b"\x89PNG\r\n\x1a\nFake Marksheet", "image/png"),
            ("INCOME_CERTIFICATE", "income.pdf", b"%PDF-1.4 Fake Income", "application/pdf"),
            ("DOMICILE_CERTIFICATE", "domicile.jpg", b"\xff\xd8\xffFake Domicile", "image/jpeg"),
        ]
        for dtype, fname, content, ctype in doc_specs:
            self.client.post(
                f"/api/v1/applications/{app_id}/documents",
                headers=student_headers,
                data={"document_type": dtype},
                files={"file": (fname, io.BytesIO(content), ctype)},
            )

        # Run AI Verification
        res = self.client.post(f"/api/v1/applications/{app_id}/verify", headers=student_headers)
        self.assertEqual(res.status_code, 200)

        # Admin Login
        res = self.client.post(
            "/api/v1/auth/admin/login",
            json={"email": "admin@demo001.edu", "password": "AdminPassword123!", "college_code": "DEMO001"},
        )
        admin_token = res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Admin Rejects Application
        reject_payload = {
            "reason": "Family annual income exceeds statutory eligibility threshold of Rs. 2,50,000.",
            "notes": "Disqualified under scheme guidelines section 4.2.",
        }
        res = self.client.post(
            f"/api/v1/applications/{app_id}/admin-review/reject",
            headers=admin_headers,
            json=reject_payload,
        )
        self.assertEqual(res.status_code, 200)
        rej_resp = res.json()
        self.assertEqual(rej_resp["status"], "REJECTED")
        self.assertEqual(rej_resp["verification_status"], "REJECTED")
        print(f"     Status: HTTP {res.status_code} | App Status -> REJECTED | Reason: {reject_payload['reason']}")

        # Student checks application -> sees REJECTED
        res = self.client.get("/api/v1/applications/my-application", headers=student_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "REJECTED")
        print(f"     Student Confirms Rejection Status: Status == 'REJECTED'")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    unittest.main()
