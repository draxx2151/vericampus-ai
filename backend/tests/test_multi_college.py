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
from app.core.security import get_password_hash, decode_access_token
from app.services.auth_service import AuthService

# Create SQLite in-memory test database engine
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

class TestMultiCollegeArchitecture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=test_engine)
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=test_engine)
        app.dependency_overrides.clear()

    def setUp(self):
        db = TestingSessionLocal()
        db.query(Student).delete()
        db.query(AdminOfficer).delete()
        db.query(College).delete()
        db.commit()

        # Seed College A
        college_a, admin_a = AuthService.create_college_with_admin(
            db=db,
            college_name="Demo Engineering College",
            college_code="DEMO001",
            admin_full_name="Admin Officer A",
            admin_email="admin@demo001.edu",
            admin_password="PasswordA123!"
        )
        self.college_a_id = college_a.id

        # Seed College B
        college_b, admin_b = AuthService.create_college_with_admin(
            db=db,
            college_name="Demo Institute of Technology",
            college_code="DEMO002",
            admin_full_name="Admin Officer B",
            admin_email="admin@demo002.edu",
            admin_password="PasswordB123!"
        )
        self.college_b_id = college_b.id
        db.close()

    def test_A_college_creation_and_model_behavior(self):
        """A. College model creation and one-admin-per-college rule"""
        db = TestingSessionLocal()
        c_a = db.query(College).filter(College.college_code == "DEMO001").first()
        self.assertIsNotNone(c_a)
        self.assertEqual(c_a.college_name, "Demo Engineering College")
        self.assertIsNotNone(c_a.admin_officer)
        self.assertEqual(c_a.admin_officer.email, "admin@demo001.edu")
        db.close()

    def test_B_student_registration_valid_college_code(self):
        """B. Student registration with valid college code"""
        res = self.client.post("/api/v1/auth/student/register", json={
            "college_code": "DEMO001",
            "full_name": "Rahul Sharma",
            "email": "rahul@demo001.edu",
            "password": "Password123!"
        })
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["full_name"], "Rahul Sharma")
        self.assertEqual(data["college_id"], str(self.college_a_id))

    def test_C_student_registration_invalid_college_code_rejected(self):
        """C. Student registration with invalid college code is rejected with 400"""
        res = self.client.post("/api/v1/auth/student/register", json={
            "college_code": "INVALID_COLLEGE_999",
            "full_name": "Ghost Student",
            "email": "ghost@example.com",
            "password": "Password123!"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid college code", res.json()["detail"])

    def test_D_student_receives_correct_college_id(self):
        """D. Student receives correct college_id bound to College B"""
        res = self.client.post("/api/v1/auth/student/register", json={
            "college_code": "DEMO002",
            "full_name": "Amit Patil",
            "email": "amit@demo002.edu",
            "password": "Password123!"
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["college_id"], str(self.college_b_id))

    def test_E_admin_login_success(self):
        """E. Admin login with correct college code + email + password is successful"""
        res = self.client.post("/api/v1/auth/admin/login", json={
            "college_code": "DEMO001",
            "email": "admin@demo001.edu",
            "password": "PasswordA123!"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["role"], "ADMIN")
        self.assertEqual(data["college_id"], str(self.college_a_id))

    def test_F_admin_login_wrong_college_code_rejected(self):
        """F. Admin login with wrong college code is rejected"""
        res = self.client.post("/api/v1/auth/admin/login", json={
            "college_code": "WRONG_CODE",
            "email": "admin@demo001.edu",
            "password": "PasswordA123!"
        })
        self.assertEqual(res.status_code, 401)

    def test_G_admin_login_wrong_password_rejected(self):
        """G. Admin login with correct college but wrong password is rejected"""
        res = self.client.post("/api/v1/auth/admin/login", json={
            "college_code": "DEMO001",
            "email": "admin@demo001.edu",
            "password": "WrongPassword!"
        })
        self.assertEqual(res.status_code, 401)

    def test_H_admin_login_wrong_college_code_for_admin_rejected(self):
        """H. Admin login with Admin A's credentials but College B's code is rejected"""
        res = self.client.post("/api/v1/auth/admin/login", json={
            "college_code": "DEMO002",
            "email": "admin@demo001.edu",
            "password": "PasswordA123!"
        })
        self.assertEqual(res.status_code, 401)

    def test_I_admin_jwt_retains_college_id(self):
        """I. Admin receives JWT containing correct college_id in token payload"""
        res = self.client.post("/api/v1/auth/admin/login", json={
            "college_code": "DEMO001",
            "email": "admin@demo001.edu",
            "password": "PasswordA123!"
        })
        self.assertEqual(res.status_code, 200)
        token = res.json()["access_token"]
        payload = decode_access_token(token)
        self.assertEqual(payload["college_id"], str(self.college_a_id))
        self.assertEqual(payload["role"], "ADMIN")

    def test_J_admin_data_isolation(self):
        """J. Admin data isolation check: Admin A's college_id does not equal Admin B's college_id"""
        db = TestingSessionLocal()
        students_a = db.query(Student).filter(Student.college_id == self.college_a_id).all()
        students_b = db.query(Student).filter(Student.college_id == self.college_b_id).all()
        self.assertNotEqual(self.college_a_id, self.college_b_id)
        admin_a = db.query(AdminOfficer).filter(AdminOfficer.email == "admin@demo001.edu").first()
        admin_b = db.query(AdminOfficer).filter(AdminOfficer.email == "admin@demo002.edu").first()
        self.assertEqual(admin_a.college_id, self.college_a_id)
        self.assertEqual(admin_b.college_id, self.college_b_id)
        db.close()

if __name__ == "__main__":
    unittest.main()
