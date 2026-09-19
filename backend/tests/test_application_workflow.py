import unittest
import uuid
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
from app.core.security import get_password_hash

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


class TestApplicationWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    def setUp(self):
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()

        # 1. Create College A & Admin A & Student A
        self.college_a_id = uuid.uuid4()
        college_a = College(
            id=self.college_a_id,
            college_name="College Alpha",
            college_code="ALPHA01",
            is_active=True
        )
        db.add(college_a)

        self.admin_a_id = uuid.uuid4()
        admin_a = AdminOfficer(
            id=self.admin_a_id,
            college_id=self.college_a_id,
            full_name="Admin Alpha",
            email="admin@alpha.edu",
            password_hash=get_password_hash("AdminPass123!"),
            is_active=True
        )
        db.add(admin_a)

        self.student_a_id = uuid.uuid4()
        student_a = Student(
            id=self.student_a_id,
            college_id=self.college_a_id,
            full_name="Student Alpha",
            email="student@alpha.edu",
            password_hash=get_password_hash("StudentPass123!"),
            is_active=True
        )
        db.add(student_a)

        # 2. Create College B & Admin B & Student B
        self.college_b_id = uuid.uuid4()
        college_b = College(
            id=self.college_b_id,
            college_name="College Beta",
            college_code="BETA01",
            is_active=True
        )
        db.add(college_b)

        self.admin_b_id = uuid.uuid4()
        admin_b = AdminOfficer(
            id=self.admin_b_id,
            college_id=self.college_b_id,
            full_name="Admin Beta",
            email="admin@beta.edu",
            password_hash=get_password_hash("AdminPass123!"),
            is_active=True
        )
        db.add(admin_b)

        self.student_b_id = uuid.uuid4()
        student_b = Student(
            id=self.student_b_id,
            college_id=self.college_b_id,
            full_name="Student Beta",
            email="student@beta.edu",
            password_hash=get_password_hash("StudentPass123!"),
            is_active=True
        )
        db.add(student_b)

        db.commit()
        db.close()

        # Login Student A
        res_stu_a = self.client.post("/api/v1/auth/login", json={
            "email": "student@alpha.edu",
            "password": "StudentPass123!",
            "role": "STUDENT"
        })
        self.token_student_a = res_stu_a.json()["access_token"]

        # Login Student B
        res_stu_b = self.client.post("/api/v1/auth/login", json={
            "email": "student@beta.edu",
            "password": "StudentPass123!",
            "role": "STUDENT"
        })
        self.token_student_b = res_stu_b.json()["access_token"]

        # Login Admin A
        res_adm_a = self.client.post("/api/v1/auth/admin/login", json={
            "college_code": "ALPHA01",
            "email": "admin@alpha.edu",
            "password": "AdminPass123!"
        })
        self.token_admin_a = res_adm_a.json()["access_token"]

        # Login Admin B
        res_adm_b = self.client.post("/api/v1/auth/admin/login", json={
            "college_code": "BETA01",
            "email": "admin@beta.edu",
            "password": "AdminPass123!"
        })
        self.token_admin_b = res_adm_b.json()["access_token"]

    def tearDown(self):
        Base.metadata.drop_all(bind=engine)

    def test_1_get_schemes_single_source_of_truth(self):
        """GET /api/v1/applications/schemes returns the official 8 MahaDBT schemes"""
        res = self.client.get("/api/v1/applications/schemes")
        self.assertEqual(res.status_code, 200)
        schemes = res.json()["schemes"]
        self.assertEqual(len(schemes), 8)
        self.assertIn("Post Matric Scholarship to VJNT Students", schemes)

    def test_2_create_application_and_verify_initial_draft_state(self):
        """Student creates application: status=DRAFT, documents=0 rows"""
        res = self.client.post(
            "/api/v1/applications",
            json={"scholarship_name": "Post Matric Scholarship to VJNT Students"},
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "DRAFT")
        self.assertEqual(data["documents_uploaded_count"], 0)
        self.assertEqual(len(data["documents"]), 0)
        self.assertEqual(data["scholarship_name"], "Post Matric Scholarship to VJNT Students")

    def test_3_one_student_one_application_rule_idempotent(self):
        """Student attempting to create a second application returns the existing application"""
        # Create App 1
        res1 = self.client.post(
            "/api/v1/applications",
            json={"scholarship_name": "Post Matric Scholarship to VJNT Students"},
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        app_id_1 = res1.json()["id"]

        # Attempt creating App 2 with different scheme
        res2 = self.client.post(
            "/api/v1/applications",
            json={"scholarship_name": "Post Matric Scholarship to OBC Students"},
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        self.assertEqual(res2.status_code, 200)
        app_id_2 = res2.json()["id"]
        self.assertEqual(app_id_1, app_id_2)

    def test_4_invalid_scholarship_scheme_rejected(self):
        """Backend rejects invalid/unsupported scholarship scheme names with 400"""
        res = self.client.post(
            "/api/v1/applications",
            json={"scholarship_name": "Fake Unapproved Scholarship"},
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Must be one of the official MahaDBT schemes", res.json()["detail"])

    def test_5_unsupported_document_type_rejected(self):
        """Document upload rejects unsupported document types (e.g. CASTE_CERTIFICATE) with 400"""
        # Create App
        res_app = self.client.post(
            "/api/v1/applications",
            json={"scholarship_name": "Post Matric Scholarship to VJNT Students"},
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        app_id = res_app.json()["id"]

        # Upload invalid document type
        import io
        res_doc = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            data={"document_type": "CASTE_CERTIFICATE"},
            files={"file": ("caste.pdf", io.BytesIO(b"%PDF-1.4 Caste"), "application/pdf")},
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        self.assertEqual(res_doc.status_code, 400)
        self.assertIn("Invalid document type", res_doc.json()["detail"])

    def test_6_document_upload_and_replacement(self):
        """Uploading document inserts row; re-uploading same type replaces row without duplicate"""
        import io
        res_app = self.client.post(
            "/api/v1/applications",
            json={"scholarship_name": "Post Matric Scholarship to VJNT Students"},
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        app_id = res_app.json()["id"]

        # Upload 1: GOVERNMENT_ID
        res_up1 = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            data={"document_type": "GOVERNMENT_ID"},
            files={"file": ("aadhaar_v1.pdf", io.BytesIO(b"%PDF-1.4 Aadhaar V1"), "application/pdf")},
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        self.assertEqual(res_up1.status_code, 200)
        self.assertEqual(res_up1.json()["documents_uploaded_count"], 1)

        # Upload 2: GOVERNMENT_ID again (replacement)
        res_up2 = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            data={"document_type": "GOVERNMENT_ID"},
            files={"file": ("aadhaar_v2.pdf", io.BytesIO(b"%PDF-1.4 Aadhaar V2"), "application/pdf")},
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        self.assertEqual(res_up2.status_code, 200)
        # Total uploaded count remains 1
        self.assertEqual(res_up2.json()["documents_uploaded_count"], 1)

    def test_7_cross_college_tenant_isolation(self):
        """Cross-college access by Student B or Admin B to Application A returns 403 Forbidden"""
        # Create Application A under College A
        res_app = self.client.post(
            "/api/v1/applications",
            json={"scholarship_name": "Post Matric Scholarship to VJNT Students"},
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        app_a_id = res_app.json()["id"]

        # 1. Student B tries to access Application A -> 403 Forbidden
        res_stu_b_access = self.client.get(
            f"/api/v1/applications/{app_a_id}",
            headers={"Authorization": f"Bearer {self.token_student_b}"}
        )
        self.assertEqual(res_stu_b_access.status_code, 403)

        # 2. Admin B tries to access Application A -> 403 Forbidden
        res_adm_b_access = self.client.get(
            f"/api/v1/applications/{app_a_id}",
            headers={"Authorization": f"Bearer {self.token_admin_b}"}
        )
        self.assertEqual(res_adm_b_access.status_code, 403)

        # 3. Admin A can access Application A -> 200 OK
        res_adm_a_access = self.client.get(
            f"/api/v1/applications/{app_a_id}",
            headers={"Authorization": f"Bearer {self.token_admin_a}"}
        )
        self.assertEqual(res_adm_a_access.status_code, 200)

        # 4. Admin B lists applications -> Application A is excluded (count = 0)
        res_adm_b_list = self.client.get(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {self.token_admin_b}"}
        )
        self.assertEqual(res_adm_b_list.status_code, 200)
        self.assertEqual(len(res_adm_b_list.json()), 0)

        # 5. Admin A lists applications -> Application A is included (count = 1)
        res_adm_a_list = self.client.get(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {self.token_admin_a}"}
        )
        self.assertEqual(res_adm_a_list.status_code, 200)
        self.assertEqual(len(res_adm_a_list.json()), 1)
