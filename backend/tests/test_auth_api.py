import unittest
import uuid
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.models.college import College
from app.db.models.student import Student
from app.db.models.admin_officer import AdminOfficer
from app.core.security import get_password_hash

# Create SQLite in-memory test database engine for API integration tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

class TestAuthAPIEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create all tables in SQLite test database
        Base.metadata.create_all(bind=test_engine)
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=test_engine)
        app.dependency_overrides.clear()

    def setUp(self):
        # Clear database between tests & seed demo college
        db = TestingSessionLocal()
        db.query(Student).delete()
        db.query(AdminOfficer).delete()
        db.query(College).delete()
        
        college = College(
            college_name="Demo Engineering College",
            college_code="DEMO001",
            email="info@demo001.edu",
            is_active=True
        )
        db.add(college)
        db.commit()
        db.refresh(college)
        self.college_id = college.id
        db.close()

    def test_student_registration_success(self):
        """POST /api/v1/auth/student/register creates student and returns safe response"""
        payload = {
            "college_code": "DEMO001",
            "full_name": "Rahul Sharma",
            "email": "rahul.sharma@example.edu",
            "password": "Password123!",
            "phone_number": "+919876543210",
            "address": "Pune, MH"
        }
        res = self.client.post("/api/v1/auth/student/register", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["full_name"], "Rahul Sharma")
        self.assertEqual(data["email"], "rahul.sharma@example.edu")
        self.assertEqual(data["college_id"], str(self.college_id))
        self.assertIn("id", data)
        self.assertNotIn("password", data)
        self.assertNotIn("password_hash", data)

    def test_student_registration_invalid_college_code_fails(self):
        """Student registration with invalid college code returns 400 Bad Request"""
        payload = {
            "college_code": "INVALID_CODE",
            "full_name": "Test Student",
            "email": "invalid@example.edu",
            "password": "Password123!"
        }
        res = self.client.post("/api/v1/auth/student/register", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid college code", res.json()["detail"])

    def test_student_registration_duplicate_email_fails(self):
        """Duplicate registration email returns 400 Bad Request"""
        payload = {
            "college_code": "DEMO001",
            "full_name": "Rahul Sharma",
            "email": "rahul.sharma@example.edu",
            "password": "Password123!"
        }
        res1 = self.client.post("/api/v1/auth/student/register", json=payload)
        self.assertEqual(res1.status_code, 201)

        res2 = self.client.post("/api/v1/auth/student/register", json=payload)
        self.assertEqual(res2.status_code, 400)
        self.assertIn("already registered", res2.json()["detail"])

    def test_student_login_with_college_code_succeeds(self):
        """POST /api/v1/auth/login authenticates Student even if optional college_code DEMO001 is present"""
        # Register student
        self.client.post("/api/v1/auth/student/register", json={
            "college_code": "DEMO001",
            "full_name": "Amit Patil",
            "email": "amit.patil@example.edu",
            "password": "SecretPassword123"
        })

        # Login with college_code DEMO001 provided
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": "amit.patil@example.edu",
            "password": "SecretPassword123",
            "college_code": "DEMO001"
        })
        self.assertEqual(login_res.status_code, 200)
        data = login_res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["role"], "STUDENT")
        self.assertEqual(data["email"], "amit.patil@example.edu")
        self.assertEqual(data["college_id"], str(self.college_id))

    def test_student_login_without_college_code_succeeds(self):
        """POST /api/v1/auth/login authenticates Student without college_code"""
        # Register student
        self.client.post("/api/v1/auth/student/register", json={
            "college_code": "DEMO001",
            "full_name": "Amit Patil",
            "email": "amit.patil@example.edu",
            "password": "SecretPassword123"
        })

        # Login without college_code
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": "amit.patil@example.edu",
            "password": "SecretPassword123"
        })
        self.assertEqual(login_res.status_code, 200)
        data = login_res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["role"], "STUDENT")
        self.assertEqual(data["email"], "amit.patil@example.edu")
        self.assertEqual(data["college_id"], str(self.college_id))

    def test_admin_login_success(self):
        """POST /api/v1/auth/admin/login authenticates AdminOfficer with college_code + email + password"""
        # Seed Admin officer in test DB
        db = TestingSessionLocal()
        admin = AdminOfficer(
            college_id=self.college_id,
            full_name="Dr. V. K. Deshmukh",
            email="admin@vericampus.edu",
            password_hash=get_password_hash("AdminPass123!"),
            department="Scholarship Cell",
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.close()

        # Login as Admin via /auth/admin/login
        login_res = self.client.post("/api/v1/auth/admin/login", json={
            "college_code": "DEMO001",
            "email": "admin@vericampus.edu",
            "password": "AdminPass123!"
        })
        self.assertEqual(login_res.status_code, 200)
        data = login_res.json()
        self.assertEqual(data["role"], "ADMIN")
        self.assertEqual(data["email"], "admin@vericampus.edu")
        self.assertEqual(data["college_id"], str(self.college_id))

    def test_admin_login_without_college_code_fails(self):
        """Admin login without college_code returns 401 Unauthorized"""
        db = TestingSessionLocal()
        admin = AdminOfficer(
            college_id=self.college_id,
            full_name="Dr. V. K. Deshmukh",
            email="admin@vericampus.edu",
            password_hash=get_password_hash("AdminPass123!"),
            department="Scholarship Cell",
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.close()

        login_res = self.client.post("/api/v1/auth/login", json={
            "email": "admin@vericampus.edu",
            "password": "AdminPass123!"
        })
        self.assertEqual(login_res.status_code, 401)
        self.assertIn("College code is required for admin login", login_res.json()["detail"])

    def test_admin_login_wrong_college_code_fails(self):
        """Admin login with wrong college_code returns 401 Unauthorized"""
        db = TestingSessionLocal()
        admin = AdminOfficer(
            college_id=self.college_id,
            full_name="Dr. V. K. Deshmukh",
            email="admin@vericampus.edu",
            password_hash=get_password_hash("AdminPass123!"),
            department="Scholarship Cell",
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.close()

        login_res = self.client.post("/api/v1/auth/admin/login", json={
            "college_code": "WRONG_CODE_999",
            "email": "admin@vericampus.edu",
            "password": "AdminPass123!"
        })
        self.assertEqual(login_res.status_code, 401)
        self.assertIn("Invalid college code, email, or password", login_res.json()["detail"])

    def test_login_invalid_password_fails(self):
        """Login with incorrect password returns 401 Unauthorized"""
        self.client.post("/api/v1/auth/student/register", json={
            "college_code": "DEMO001",
            "full_name": "Test Student",
            "email": "test@example.edu",
            "password": "CorrectPassword"
        })

        res = self.client.post("/api/v1/auth/login", json={
            "email": "test@example.edu",
            "password": "WrongPassword"
        })
        self.assertEqual(res.status_code, 401)
        self.assertIn("Invalid email or password", res.json()["detail"])

    def test_get_current_user_profile_me_endpoint(self):
        """GET /api/v1/auth/me returns authenticated user profile with college_id"""
        # Register student & login
        self.client.post("/api/v1/auth/student/register", json={
            "college_code": "DEMO001",
            "full_name": "Sneha Kulkarni",
            "email": "sneha@example.edu",
            "password": "Password123!"
        })
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": "sneha@example.edu",
            "password": "Password123!"
        })
        token = login_res.json()["access_token"]

        # Call /api/v1/auth/me
        me_res = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(me_res.status_code, 200)
        profile = me_res.json()
        self.assertEqual(profile["full_name"], "Sneha Kulkarni")
        self.assertEqual(profile["email"], "sneha@example.edu")
        self.assertEqual(profile["role"], "STUDENT")
        self.assertEqual(profile["college_id"], str(self.college_id))
        self.assertNotIn("password", profile)
        self.assertNotIn("password_hash", profile)

    def test_get_current_user_me_without_token_fails(self):
        """GET /api/v1/auth/me without Bearer header returns 403 / 401"""
        res = self.client.get("/api/v1/auth/me")
        self.assertTrue(res.status_code in (401, 403))

    def test_inactive_user_login_fails(self):
        """Login attempt by an inactive user returns 401 Unauthorized"""
        db = TestingSessionLocal()
        inactive_student = Student(
            college_id=self.college_id,
            full_name="Inactive User",
            email="inactive@example.edu",
            password_hash=get_password_hash("Password123!"),
            is_active=False
        )
        db.add(inactive_student)
        db.commit()
        db.close()

        res = self.client.post("/api/v1/auth/login", json={
            "email": "inactive@example.edu",
            "password": "Password123!"
        })
        self.assertEqual(res.status_code, 401)
        self.assertIn("inactive", res.json()["detail"].lower())

if __name__ == "__main__":
    unittest.main()
