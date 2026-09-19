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


class TestAdminSetupFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    def setUp(self):
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()

        # Seed a test college with admin_setup_code and no college_code
        self.college_id = uuid.uuid4()
        test_college = College(
            id=self.college_id,
            college_name="Test Engineering College",
            admin_setup_code="SETUP-TEST-2026",
            is_setup_code_used=False,
            college_code=None,
            is_active=True
        )
        db.add(test_college)
        db.commit()
        db.close()

    def tearDown(self):
        Base.metadata.drop_all(bind=engine)

    def test_1_student_cannot_register_when_no_college_code(self):
        """Student registration fails when college code is not configured"""
        res = self.client.post("/api/v1/auth/student/register", json={
            "college_code": "COLLEGE001",
            "full_name": "Student Test",
            "email": "student@test.com",
            "password": "Password123!"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid college code", res.json()["detail"])

    def test_2_admin_registration_with_valid_setup_code(self):
        """Admin registers using valid setup_code"""
        res = self.client.post("/api/v1/auth/admin/register", json={
            "admin_setup_code": "SETUP-TEST-2026",
            "full_name": "Admin Officer",
            "email": "admin@test.com",
            "password": "AdminPassword123!",
            "department": "Scholarship",
            "designation": "Head Officer"
        })
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["role"], "ADMIN")

    def test_3_admin_setup_code_reuse_fails(self):
        """Reusing the same admin_setup_code fails (one-time-use)"""
        # Register first admin
        res1 = self.client.post("/api/v1/auth/admin/register", json={
            "admin_setup_code": "SETUP-TEST-2026",
            "full_name": "Admin Officer 1",
            "email": "admin1@test.com",
            "password": "AdminPassword123!"
        })
        self.assertEqual(res1.status_code, 201)

        # Attempt registering second admin with same setup code
        res2 = self.client.post("/api/v1/auth/admin/register", json={
            "admin_setup_code": "SETUP-TEST-2026",
            "full_name": "Admin Officer 2",
            "email": "admin2@test.com",
            "password": "AdminPassword123!"
        })
        self.assertEqual(res2.status_code, 400)
        self.assertIn("Invalid or already used Admin Setup Code", res2.json()["detail"])

    def test_4_admin_sets_college_code_and_student_registers(self):
        """Admin configures student college code, enabling student registration"""
        # 1. Register Admin
        res_admin = self.client.post("/api/v1/auth/admin/register", json={
            "admin_setup_code": "SETUP-TEST-2026",
            "full_name": "Admin Officer",
            "email": "admin@test.com",
            "password": "AdminPassword123!"
        })
        token = res_admin.json()["access_token"]

        # 2. Admin sets college_code to COLLEGE001
        res_code = self.client.put(
            "/api/v1/admin/college-code",
            json={"college_code": "COLLEGE001"},
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res_code.status_code, 200)
        self.assertEqual(res_code.json()["college_code"], "COLLEGE001")

        # 3. Student registers using COLLEGE001
        res_student = self.client.post("/api/v1/auth/student/register", json={
            "college_code": "COLLEGE001",
            "full_name": "Student One",
            "email": "student1@test.com",
            "password": "Password123!"
        })
        self.assertEqual(res_student.status_code, 201)
        self.assertEqual(res_student.json()["full_name"], "Student One")
