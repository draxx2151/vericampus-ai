import unittest
import uuid
import jwt
from datetime import timedelta, datetime, timezone

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.db.models.enums import UserRole
from app.schemas.auth import LoginRequest, TokenResponse, TokenPayload
from app.schemas.student import StudentResponse
from app.schemas.admin_officer import AdminOfficerResponse

class TestAuthenticationFoundation(unittest.TestCase):

    def test_1_password_hashing_non_plain(self):
        """1. Password hashing produces a non-plain-text hash"""
        raw_pwd = "SecretPassword123!"
        hashed = get_password_hash(raw_pwd)
        self.assertNotEqual(raw_pwd, hashed)
        self.assertTrue(hashed.startswith("$2"))  # Standard bcrypt hash prefix

    def test_2_correct_password_verification(self):
        """2. Correct password verifies successfully"""
        raw_pwd = "SecretPassword123!"
        hashed = get_password_hash(raw_pwd)
        self.assertTrue(verify_password(raw_pwd, hashed))

    def test_3_incorrect_password_verification_fails(self):
        """3. Incorrect password fails verification"""
        raw_pwd = "SecretPassword123!"
        wrong_pwd = "WrongPassword456!"
        hashed = get_password_hash(raw_pwd)
        self.assertFalse(verify_password(wrong_pwd, hashed))

    def test_4_jwt_creation(self):
        """4. JWT token can be created with college_id"""
        user_id = str(uuid.uuid4())
        college_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id, role=UserRole.STUDENT, college_id=college_id)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 20)

    def test_5_jwt_decoding(self):
        """5. JWT token can be decoded successfully with college_id claim"""
        user_id = str(uuid.uuid4())
        college_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id, role=UserRole.ADMIN, college_id=college_id)
        payload = decode_access_token(token)
        self.assertEqual(payload["sub"], user_id)
        self.assertEqual(payload["role"], "ADMIN")
        self.assertEqual(payload["college_id"], college_id)
        self.assertIn("exp", payload)

    def test_6_invalid_jwt_fails_validation(self):
        """6. Invalid JWT fails validation"""
        invalid_token = "invalid.jwt.token.string"
        with self.assertRaises(jwt.PyJWTError):
            decode_access_token(invalid_token)

    def test_7_expired_jwt_rejected(self):
        """7. Expired JWT is rejected with ExpiredSignatureError"""
        user_id = str(uuid.uuid4())
        college_id = str(uuid.uuid4())
        expired_delta = timedelta(seconds=-10)
        expired_token = create_access_token(
            subject=user_id,
            role=UserRole.STUDENT,
            college_id=college_id,
            expires_delta=expired_delta
        )
        with self.assertRaises(jwt.ExpiredSignatureError):
            decode_access_token(expired_token)

    def test_8_auth_schemas_validation(self):
        """8. Auth schemas validate correctly including college fields"""
        login_req = LoginRequest(
            email="student@vericampus.edu",
            password="securePassword123",
            role=UserRole.STUDENT
        )
        self.assertEqual(login_req.email, "student@vericampus.edu")
        self.assertEqual(login_req.role, UserRole.STUDENT)

        u_id = uuid.uuid4()
        c_id = uuid.uuid4()
        token_resp = TokenResponse(
            access_token="mock_access_token",
            user_id=u_id,
            college_id=c_id,
            email="student@vericampus.edu",
            role=UserRole.STUDENT,
            expires_in_seconds=86400
        )
        self.assertEqual(token_resp.access_token, "mock_access_token")
        self.assertEqual(token_resp.college_id, c_id)

        token_payload = TokenPayload(
            sub=str(u_id),
            role=UserRole.STUDENT,
            college_id=c_id,
            exp=1750000000
        )
        self.assertEqual(token_payload.sub, str(u_id))
        self.assertEqual(token_payload.college_id, c_id)

    def test_9_password_hash_never_returned_in_public_schemas(self):
        """9. Password hash is never returned through public response schemas"""
        s_id = uuid.uuid4()
        c_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        student_resp = StudentResponse(
            id=s_id,
            college_id=c_id,
            full_name="Rahul Sharma",
            email="rahul@example.com",
            created_at=now,
            updated_at=now
        )
        resp_dict = student_resp.model_dump()
        self.assertNotIn("password_hash", resp_dict)
        self.assertNotIn("password", resp_dict)

        admin_resp = AdminOfficerResponse(
            id=s_id,
            college_id=c_id,
            full_name="Dr. V. K. Deshmukh",
            email="admin@vericampus.edu",
            created_at=now,
            updated_at=now
        )
        admin_dict = admin_resp.model_dump()
        self.assertNotIn("password_hash", admin_dict)
        self.assertNotIn("password", admin_dict)

if __name__ == "__main__":
    unittest.main()
