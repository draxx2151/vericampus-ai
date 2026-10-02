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
import io
from datetime import date, time
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
from app.db.models.notification import Notification
from app.db.models.enums import UserRole, ApplicationStatus, DocumentType
from app.core.security import create_access_token, get_password_hash
from app.schemas.application import MAHADBT_SCHEMES

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


class TestNotificationsWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()

        code_a = f"NOTIF-A-{uuid.uuid4().hex[:4].upper()}"
        code_b = f"NOTIF-B-{uuid.uuid4().hex[:4].upper()}"

        # Setup College A and College B
        self.college_a = College(id=uuid.uuid4(), college_name="College A", college_code=code_a, is_active=True)
        self.college_b = College(id=uuid.uuid4(), college_name="College B", college_code=code_b, is_active=True)
        self.db.add_all([self.college_a, self.college_b])
        self.db.commit()

        # Setup Student A (College A)
        self.student_a = Student(
            id=uuid.uuid4(),
            college_id=self.college_a.id,
            full_name="Aarav Sharma",
            email="aarav.sharma@example.edu",
            password_hash=get_password_hash("StudentPass123!"),
            is_active=True
        )
        # Setup Student B (College B)
        self.student_b = Student(
            id=uuid.uuid4(),
            college_id=self.college_b.id,
            full_name="Ananya Patil",
            email="ananya.patil@example.edu",
            password_hash=get_password_hash("StudentPass123!"),
            is_active=True
        )
        # Setup Admin A (College A)
        self.admin_a = AdminOfficer(
            id=uuid.uuid4(),
            college_id=self.college_a.id,
            full_name="Admin Officer A",
            email="admin.notif.a@example.edu",
            password_hash=get_password_hash("AdminPass123!"),
            is_active=True
        )
        # Setup Admin B (College B)
        self.admin_b = AdminOfficer(
            id=uuid.uuid4(),
            college_id=self.college_b.id,
            full_name="Admin Officer B",
            email="admin.notif.b@example.edu",
            password_hash=get_password_hash("AdminPass123!"),
            is_active=True
        )
        self.db.add_all([self.student_a, self.student_b, self.admin_a, self.admin_b])
        self.db.commit()

        # Setup Tokens
        self.token_student_a = create_access_token(
            subject=str(self.student_a.id),
            role=UserRole.STUDENT,
            college_id=str(self.college_a.id)
        )
        self.token_student_b = create_access_token(
            subject=str(self.student_b.id),
            role=UserRole.STUDENT,
            college_id=str(self.college_b.id)
        )
        self.token_admin_a = create_access_token(
            subject=str(self.admin_a.id),
            role=UserRole.ADMIN,
            college_id=str(self.college_a.id)
        )
        self.token_admin_b = create_access_token(
            subject=str(self.admin_b.id),
            role=UserRole.ADMIN,
            college_id=str(self.college_b.id)
        )

    def tearDown(self):
        self.db.close()

    def test_01_application_submission_generates_notifications(self):
        """Student creating an application generates real notifications for student and college admin."""
        res_app = self.client.post(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {self.token_student_a}"},
            json={"scholarship_name": MAHADBT_SCHEMES[0]}
        )
        self.assertEqual(res_app.status_code, 200)

        # Check Student A notifications
        res_student_notifs = self.client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        self.assertEqual(res_student_notifs.status_code, 200)
        data_s = res_student_notifs.json()
        self.assertGreaterEqual(data_s["total_count"], 1)
        self.assertEqual(data_s["notifications"][0]["event_type"], "APPLICATION_SUBMITTED")
        self.assertEqual(data_s["notifications"][0]["recipient_role"], "STUDENT")

        # Check Admin A notifications
        res_admin_notifs = self.client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {self.token_admin_a}"}
        )
        self.assertEqual(res_admin_notifs.status_code, 200)
        data_a = res_admin_notifs.json()
        self.assertGreaterEqual(data_a["total_count"], 1)
        self.assertEqual(data_a["notifications"][0]["event_type"], "APPLICATION_SUBMITTED")
        self.assertEqual(data_a["notifications"][0]["recipient_role"], "ADMIN")

        # Check Admin B (College B) receives NO notifications from College A (tenant isolation)
        res_admin_b_notifs = self.client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {self.token_admin_b}"}
        )
        self.assertEqual(res_admin_b_notifs.status_code, 200)
        self.assertEqual(res_admin_b_notifs.json()["total_count"], 0)

    def test_02_full_workflow_notification_lifecycle(self):
        """
        Covers the complete notification lifecycle:
        - Application submission
        - Verification completed
        - Correction requested
        - Document replacement
        - Physical verification scheduled
        - Physical verification completed
        - Application approved
        """
        # 1. Submit application
        res_app = self.client.post(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {self.token_student_a}"},
            json={"scholarship_name": MAHADBT_SCHEMES[0]}
        )
        app_id = res_app.json()["id"]

        # 2. Upload 4 documents
        for dtype in ["GOVERNMENT_ID", "MARKSHEET", "INCOME_CERTIFICATE", "DOMICILE_CERTIFICATE"]:
            self.client.post(
                f"/api/v1/applications/{app_id}/documents",
                headers={"Authorization": f"Bearer {self.token_student_a}"},
                data={"document_type": dtype},
                files={"file": (f"{dtype.lower()}.pdf", io.BytesIO(b"%PDF-1.4 sample content"), "application/pdf")}
            )

        # 3. Trigger verification
        self.client.post(
            f"/api/v1/applications/{app_id}/verify",
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )

        # 4. Request correction
        self.client.post(
            f"/api/v1/applications/{app_id}/admin-review/request-correction",
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
            json={"document_types": ["INCOME_CERTIFICATE"], "reason": "Income certificate validity expired"}
        )

        # 5. Student replaces document
        self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {self.token_student_a}"},
            data={"document_type": "INCOME_CERTIFICATE"},
            files={"file": ("income_renewed.pdf", io.BytesIO(b"%PDF-1.4 renewed content"), "application/pdf")}
        )

        # 6. Admin schedules physical verification
        res_pv = self.client.post(
            f"/api/v1/applications/{app_id}/admin-review/physical-verification",
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
            json={
                "scheduled_date": "2026-10-15",
                "scheduled_time": "11:00",
                "venue": "Room 302, Academic Block",
                "instructions": "Bring original income certificate"
            }
        )
        self.assertEqual(res_pv.status_code, 200)

        # 7. Admin records physical verification completed
        res_pvc = self.client.post(
            f"/api/v1/applications/{app_id}/admin-review/physical-verification/complete",
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
            json={"result": "VERIFIED", "remarks": "Original documents verified in person"}
        )
        self.assertEqual(res_pvc.status_code, 200)

        # 8. Admin approves application
        self.client.post(
            f"/api/v1/applications/{app_id}/admin-review/approve",
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
            json={"remarks": "All documents verified and eligible"}
        )

        # Inspect Student A notifications
        res_s = self.client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        notifs_s = res_s.json()["notifications"]
        event_types_s = [n["event_type"] for n in notifs_s]

        expected_events = [
            "APPLICATION_APPROVED",
            "PHYSICAL_VERIFICATION_COMPLETED",
            "PHYSICAL_VERIFICATION_SCHEDULED",
            "DOCUMENT_REPLACED",
            "CORRECTION_REQUESTED",
            "VERIFICATION_COMPLETED",
            "APPLICATION_SUBMITTED"
        ]
        for ev in expected_events:
            self.assertIn(ev, event_types_s, f"Expected event {ev} in student notifications")

        # Inspect Admin A notifications
        res_a = self.client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {self.token_admin_a}"}
        )
        notifs_a = res_a.json()["notifications"]
        event_types_a = [n["event_type"] for n in notifs_a]
        for ev in expected_events:
            self.assertIn(ev, event_types_a, f"Expected event {ev} in admin notifications")

    def test_03_mark_as_read_and_mark_all_read(self):
        """Tests individual notification read status update and bulk mark-all-read."""
        # Create application to trigger notification
        self.client.post(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {self.token_student_a}"},
            json={"scholarship_name": MAHADBT_SCHEMES[0]}
        )

        res_notifs = self.client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        data = res_notifs.json()
        notif_id = data["notifications"][0]["id"]
        self.assertFalse(data["notifications"][0]["is_read"])
        self.assertGreater(data["unread_count"], 0)

        # Mark individual notification as read
        res_read = self.client.patch(
            f"/api/v1/notifications/{notif_id}/read",
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        self.assertEqual(res_read.status_code, 200)
        self.assertTrue(res_read.json()["is_read"])
        self.assertIsNotNone(res_read.json()["read_at"])

        # Mark all as read
        res_mark_all = self.client.post(
            "/api/v1/notifications/mark-all-read",
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        self.assertEqual(res_mark_all.status_code, 200)

        # Verify unread count is 0
        res_after = self.client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        self.assertEqual(res_after.json()["unread_count"], 0)

    def test_04_tenant_and_ownership_isolation_on_read(self):
        """Unauthorized attempt to read other user's or college's notification fails with 403."""
        # Student A notification
        self.client.post(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {self.token_student_a}"},
            json={"scholarship_name": MAHADBT_SCHEMES[0]}
        )
        res_notifs = self.client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        notif_id = res_notifs.json()["notifications"][0]["id"]

        # Student B attempts to mark Student A's notification as read
        res_bad_s = self.client.patch(
            f"/api/v1/notifications/{notif_id}/read",
            headers={"Authorization": f"Bearer {self.token_student_b}"}
        )
        self.assertEqual(res_bad_s.status_code, 403)

        # Admin B (College B) attempts to mark Student A's notification as read
        res_bad_admin = self.client.patch(
            f"/api/v1/notifications/{notif_id}/read",
            headers={"Authorization": f"Bearer {self.token_admin_b}"}
        )
        self.assertEqual(res_bad_admin.status_code, 403)


if __name__ == "__main__":
    unittest.main()
