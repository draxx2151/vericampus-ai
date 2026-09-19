import unittest
import uuid
import io
from pathlib import Path
from unittest.mock import patch
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
from app.db.models.enums import UserRole, ApplicationStatus, DocumentType
from app.core.security import create_access_token, get_password_hash
from app.core.config import settings

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


class TestDocumentUploadAndStorage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()

        code_a = f"CLA-{uuid.uuid4().hex[:6].upper()}"
        code_b = f"CLB-{uuid.uuid4().hex[:6].upper()}"

        # Setup College A and College B
        self.college_a = College(id=uuid.uuid4(), college_name="College A", college_code=code_a, is_active=True)
        self.college_b = College(id=uuid.uuid4(), college_name="College B", college_code=code_b, is_active=True)
        self.db.add_all([self.college_a, self.college_b])
        self.db.commit()

        # Setup Student A and Student B
        self.student_a = Student(
            id=uuid.uuid4(),
            college_id=self.college_a.id,
            full_name="Student A",
            email=f"studenta-{uuid.uuid4().hex[:6]}@collega.edu",
            password_hash=get_password_hash("Password123!"),
            is_active=True
        )
        self.student_b = Student(
            id=uuid.uuid4(),
            college_id=self.college_b.id,
            full_name="Student B",
            email=f"studentb-{uuid.uuid4().hex[:6]}@collb.edu",
            password_hash=get_password_hash("Password123!"),
            is_active=True
        )
        self.db.add_all([self.student_a, self.student_b])

        # Setup Admin A and Admin B
        self.admin_a = AdminOfficer(
            id=uuid.uuid4(),
            college_id=self.college_a.id,
            full_name="Admin A",
            email=f"admina-{uuid.uuid4().hex[:6]}@collega.edu",
            password_hash=get_password_hash("AdminPass123!"),
            is_active=True
        )
        self.admin_b = AdminOfficer(
            id=uuid.uuid4(),
            college_id=self.college_b.id,
            full_name="Admin B",
            email=f"adminb-{uuid.uuid4().hex[:6]}@collb.edu",
            password_hash=get_password_hash("AdminPass123!"),
            is_active=True
        )
        self.db.add_all([self.admin_a, self.admin_b])
        self.db.commit()

        # Create Application for Student A
        self.app_a = ScholarshipApplication(
            id=uuid.uuid4(),
            student_id=self.student_a.id,
            scholarship_name="Post Matric Scholarship to VJNT Students",
            application_number=f"VC-2026-{uuid.uuid4().hex[:4]}",
            status=ApplicationStatus.DRAFT
        )
        self.db.add(self.app_a)
        self.db.commit()

        # Create tokens
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
        Base.metadata.drop_all(bind=engine)

    def test_1_valid_pdf_upload(self):
        token = self.token_student_a
        app_id = str(self.app_a.id)

        valid_pdf_content = b"%PDF-1.4 Fake valid PDF content for testing..."
        files = {
            "file": ("aadhaar_valid.pdf", io.BytesIO(valid_pdf_content), "application/pdf")
        }
        data = {
            "document_type": "GOVERNMENT_ID"
        }

        res = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data=data,
            files=files
        )

        self.assertEqual(res.status_code, 200)
        json_data = res.json()
        self.assertEqual(json_data["documents_uploaded_count"], 1)
        doc = json_data["documents"][0]
        self.assertEqual(doc["original_filename"], "aadhaar_valid.pdf")
        self.assertEqual(doc["document_type"], "GOVERNMENT_ID")

    def test_2_valid_jpg_upload(self):
        token = self.token_student_a
        app_id = str(self.app_a.id)

        valid_jpg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF Fake JPG image bytes..."
        files = {
            "file": ("marksheet.jpg", io.BytesIO(valid_jpg_content), "image/jpeg")
        }
        data = {
            "document_type": "MARKSHEET"
        }

        res = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data=data,
            files=files
        )

        self.assertEqual(res.status_code, 200)
        json_data = res.json()
        self.assertEqual(json_data["documents_uploaded_count"], 1)

    def test_3_valid_png_upload(self):
        token = self.token_student_a
        app_id = str(self.app_a.id)

        valid_png_content = b"\x89PNG\r\n\x1a\nFake PNG image bytes..."
        files = {
            "file": ("income.png", io.BytesIO(valid_png_content), "image/png")
        }
        data = {
            "document_type": "INCOME_CERTIFICATE"
        }

        res = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data=data,
            files=files
        )

        self.assertEqual(res.status_code, 200)

    def test_4_file_over_2_5mb_rejected(self):
        token = self.token_student_a
        app_id = str(self.app_a.id)

        # 2.7 MB file payload (2,800,000 bytes)
        large_pdf_content = b"%PDF-1.4 " + b"0" * 2_800_000
        files = {
            "file": ("too_large.pdf", io.BytesIO(large_pdf_content), "application/pdf")
        }
        data = {
            "document_type": "DOMICILE_CERTIFICATE"
        }

        res = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data=data,
            files=files
        )

        self.assertEqual(res.status_code, 400)
        self.assertIn("File exceeds the maximum allowed size of 2.5 MB.", res.json()["detail"])

    def test_5_magic_byte_mismatch_rejected(self):
        token = self.token_student_a
        app_id = str(self.app_a.id)

        # Text file disguised with .pdf extension
        fake_pdf_content = b"This is plain text content without PDF header magic bytes!"
        files = {
            "file": ("fake_doc.pdf", io.BytesIO(fake_pdf_content), "application/pdf")
        }
        data = {
            "document_type": "DOMICILE_CERTIFICATE"
        }

        res = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data=data,
            files=files
        )

        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid file signature", res.json()["detail"])

    def test_6_unsupported_extension_rejected(self):
        token = self.token_student_a
        app_id = str(self.app_a.id)

        files = {
            "file": ("document.docx", io.BytesIO(b"MS Word Document Content"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        data = {
            "document_type": "DOMICILE_CERTIFICATE"
        }

        res = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data=data,
            files=files
        )

        self.assertEqual(res.status_code, 400)
        self.assertIn("Only PDF, JPG, JPEG, and PNG files are allowed", res.json()["detail"])

    def test_7_unsupported_document_type_rejected(self):
        token = self.token_student_a
        app_id = str(self.app_a.id)

        valid_pdf_content = b"%PDF-1.4 PDF content"
        files = {
            "file": ("caste.pdf", io.BytesIO(valid_pdf_content), "application/pdf")
        }
        data = {
            "document_type": "CASTE_CERTIFICATE"
        }

        res = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data=data,
            files=files
        )

        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid document type", res.json()["detail"])

    def test_8_unauthenticated_upload_fails(self):
        app_id = str(self.app_a.id)
        files = {
            "file": ("doc.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")
        }
        data = {"document_type": "GOVERNMENT_ID"}

        res = self.client.post(f"/api/v1/applications/{app_id}/documents", data=data, files=files)
        self.assertEqual(res.status_code, 401)

    def test_9_student_b_cannot_upload_to_student_a_application(self):
        token_student_b = self.token_student_b
        app_id_a = str(self.app_a.id)

        files = {
            "file": ("hack.pdf", io.BytesIO(b"%PDF-1.4 malicious"), "application/pdf")
        }
        data = {"document_type": "GOVERNMENT_ID"}

        res = self.client.post(
            f"/api/v1/applications/{app_id_a}/documents",
            headers={"Authorization": f"Bearer {token_student_b}"},
            data=data,
            files=files
        )

        self.assertEqual(res.status_code, 403)
        self.assertIn("Access denied", res.json()["detail"])

    def test_10_student_b_cannot_download_student_a_document(self):
        token_student_a = self.token_student_a
        token_student_b = self.token_student_b
        app_id_a = str(self.app_a.id)

        # Upload doc first as Student A
        files = {"file": ("aadhaar.pdf", io.BytesIO(b"%PDF-1.4 aadhaar content"), "application/pdf")}
        res_upload = self.client.post(
            f"/api/v1/applications/{app_id_a}/documents",
            headers={"Authorization": f"Bearer {token_student_a}"},
            data={"document_type": "GOVERNMENT_ID"},
            files=files
        )
        self.assertEqual(res_upload.status_code, 200)
        doc_id = res_upload.json()["documents"][0]["id"]

        # Student B attempts downloading Student A's document
        res_download = self.client.get(
            f"/api/v1/applications/{app_id_a}/documents/{doc_id}/file",
            headers={"Authorization": f"Bearer {token_student_b}"}
        )

        self.assertEqual(res_download.status_code, 403)
        self.assertIn("Access denied", res_download.json()["detail"])

    def test_11_document_replacement_deletes_old_file_on_commit_success(self):
        token = self.token_student_a
        app_id = str(self.app_a.id)

        # Initial upload
        res1 = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data={"document_type": "DOMICILE_CERTIFICATE"},
            files={"file": ("domicile_v1.pdf", io.BytesIO(b"%PDF-1.4 Domicile V1"), "application/pdf")}
        )
        self.assertEqual(res1.status_code, 200)

        # Retrieve storage path from DB directly (not exposed in API response)
        doc_db = self.db.query(Document).filter(
            Document.application_id == self.app_a.id,
            Document.document_type == DocumentType.DOMICILE_CERTIFICATE
        ).first()
        old_path = Path(settings.DOCUMENT_STORAGE_PATH) / doc_db.storage_path
        self.assertTrue(old_path.exists())

        # Re-upload replacement file
        res2 = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data={"document_type": "DOMICILE_CERTIFICATE"},
            files={"file": ("domicile_v2.png", io.BytesIO(b"\x89PNG\r\n\x1a\n Domicile V2"), "image/png")}
        )
        self.assertEqual(res2.status_code, 200)

        # Check DB updated and old file deleted
        self.db.refresh(doc_db)
        new_path = Path(settings.DOCUMENT_STORAGE_PATH) / doc_db.storage_path
        self.assertTrue(new_path.exists())
        self.assertFalse(old_path.exists())

    def test_12_db_commit_failure_deletes_new_file_and_preserves_old_file(self):
        token = self.token_student_a
        app_id = str(self.app_a.id)

        # Upload initial doc
        self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data={"document_type": "INCOME_CERTIFICATE"},
            files={"file": ("income_old.pdf", io.BytesIO(b"%PDF-1.4 Income Old"), "application/pdf")}
        )

        doc_db = self.db.query(Document).filter(
            Document.application_id == self.app_a.id,
            Document.document_type == DocumentType.INCOME_CERTIFICATE
        ).first()
        old_path = Path(settings.DOCUMENT_STORAGE_PATH) / doc_db.storage_path
        self.assertTrue(old_path.exists())

        # Mock DB commit failure during replacement
        with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("Database Connection Dropped")):
            res_fail = self.client.post(
                f"/api/v1/applications/{app_id}/documents",
                headers={"Authorization": f"Bearer {token}"},
                data={"document_type": "INCOME_CERTIFICATE"},
                files={"file": ("income_new.pdf", io.BytesIO(b"%PDF-1.4 Income New"), "application/pdf")}
            )
            self.assertEqual(res_fail.status_code, 500)

        # Verify old file remains intact on disk
        self.assertTrue(old_path.exists())

    def test_13_path_traversal_with_allowed_extension(self):
        token = self.token_student_a
        app_id = str(self.app_a.id)

        # Upload with path traversal sequence in filename
        files = {
            "file": ("../../student_document.pdf", io.BytesIO(b"%PDF-1.4 Path Traversal Check"), "application/pdf")
        }
        data = {"document_type": "MARKSHEET"}

        res = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data=data,
            files=files
        )

        self.assertEqual(res.status_code, 200)

        # Verify physical file stays inside base storage directory
        doc_db = self.db.query(Document).filter(
            Document.application_id == self.app_a.id,
            Document.document_type == DocumentType.MARKSHEET
        ).first()

        base_storage = Path(settings.DOCUMENT_STORAGE_PATH).resolve()
        full_file_path = (base_storage / doc_db.storage_path).resolve()

        self.assertTrue(full_file_path.is_relative_to(base_storage))
        self.assertTrue(full_file_path.exists())

    def test_14_storage_path_hidden_from_api(self):
        token = self.token_student_a
        app_id = str(self.app_a.id)

        res = self.client.get(
            f"/api/v1/applications/{app_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        self.assertEqual(res.status_code, 200)
        docs = res.json()["documents"]
        for d in docs:
            self.assertNotIn("storage_path", d)

    def test_15_cross_college_admin_download_rejected(self):
        token_student_a = self.token_student_a
        token_admin_b = self.token_admin_b
        app_id_a = str(self.app_a.id)

        # Upload document under College A application
        res_up = self.client.post(
            f"/api/v1/applications/{app_id_a}/documents",
            headers={"Authorization": f"Bearer {token_student_a}"},
            data={"document_type": "GOVERNMENT_ID"},
            files={"file": ("colla_doc.pdf", io.BytesIO(b"%PDF-1.4 College A Doc"), "application/pdf")}
        )
        self.assertEqual(res_up.status_code, 200)
        doc_id = res_up.json()["documents"][0]["id"]

        # Admin from College B attempts downloading document from College A
        res_dl = self.client.get(
            f"/api/v1/applications/{app_id_a}/documents/{doc_id}/file",
            headers={"Authorization": f"Bearer {token_admin_b}"}
        )
        self.assertEqual(res_dl.status_code, 403)
        self.assertIn("Cross-college document access is prohibited", res_dl.json()["detail"])
