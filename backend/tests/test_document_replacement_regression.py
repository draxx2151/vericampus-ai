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
from app.db.models.verification_result import VerificationResult
from app.db.models.enums import UserRole, ApplicationStatus, DocumentType
from app.core.security import create_access_token, get_password_hash
from app.core.config import settings
from app.services.verification import VerificationService

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


class TestDocumentReplacementRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()

        code_a = f"REG-A-{uuid.uuid4().hex[:4].upper()}"
        code_b = f"REG-B-{uuid.uuid4().hex[:4].upper()}"

        # Setup College A and College B
        self.college_a = College(id=uuid.uuid4(), college_name="Engineering College A", college_code=code_a, is_active=True)
        self.college_b = College(id=uuid.uuid4(), college_name="Engineering College B", college_code=code_b, is_active=True)
        self.db.add_all([self.college_a, self.college_b])
        self.db.commit()

        # Setup Student A (College A)
        self.student_a = Student(
            id=uuid.uuid4(),
            college_id=self.college_a.id,
            full_name="Rohit Sharma",
            email="rohit.sharma@example.edu",
            password_hash=get_password_hash("StudentPass123!"),
            is_active=True
        )
        # Setup Student B (College B)
        self.student_b = Student(
            id=uuid.uuid4(),
            college_id=self.college_b.id,
            full_name="Virat Kohli",
            email="virat.kohli@example.edu",
            password_hash=get_password_hash("StudentPass123!"),
            is_active=True
        )
        # Setup Admin A (College A)
        self.admin_a = AdminOfficer(
            id=uuid.uuid4(),
            college_id=self.college_a.id,
            full_name="Admin College A",
            email="admin.a@example.edu",
            password_hash=get_password_hash("AdminPass123!"),
            is_active=True
        )
        # Setup Admin B (College B)
        self.admin_b = AdminOfficer(
            id=uuid.uuid4(),
            college_id=self.college_b.id,
            full_name="Admin College B",
            email="admin.b@example.edu",
            password_hash=get_password_hash("AdminPass123!"),
            is_active=True
        )
        self.db.add_all([self.student_a, self.student_b, self.admin_a, self.admin_b])
        self.db.commit()

        # Setup Application A
        self.app_a = ScholarshipApplication(
            id=uuid.uuid4(),
            student_id=self.student_a.id,
            scholarship_name="Rajarshi Chhatrapati Shahu Maharaj Shikshan Shulkh Shishyavrutti Scheme",
            application_number=f"VC-REG-{uuid.uuid4().hex[:4].upper()}",
            status=ApplicationStatus.DRAFT
        )
        self.db.add(self.app_a)
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

    def test_01_document_replacement_flow_and_anti_cache_headers(self):
        """
        Document A is uploaded, then replaced with Document B.
        Proves:
        1. Student retrieval returns Document B content and filename.
        2. Admin retrieval returns Document B content and filename.
        3. Strict anti-cache headers are returned on the file endpoint.
        4. Old Document A physical file is removed from disk.
        """
        app_id = str(self.app_a.id)

        # 1. Upload Document A
        content_a = b"%PDF-1.4 Initial Document A Content Version 1.0"
        res1 = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {self.token_student_a}"},
            data={"document_type": "GOVERNMENT_ID"},
            files={"file": ("aadhaar_doc_a.pdf", io.BytesIO(content_a), "application/pdf")}
        )
        self.assertEqual(res1.status_code, 200)
        docs1 = res1.json()["documents"]
        gov_doc1 = next(d for d in docs1 if d["document_type"] == "GOVERNMENT_ID")
        doc_id = gov_doc1["id"]
        self.assertEqual(gov_doc1["original_filename"], "aadhaar_doc_a.pdf")

        # Get old storage path from DB
        doc_db = self.db.query(Document).filter(Document.id == uuid.UUID(doc_id)).first()
        old_storage_path = Path(settings.DOCUMENT_STORAGE_PATH) / doc_db.storage_path
        self.assertTrue(old_storage_path.exists())

        # 2. Student views Document A
        res_view_a = self.client.get(
            f"/api/v1/applications/{app_id}/documents/{doc_id}/file",
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        self.assertEqual(res_view_a.status_code, 200)
        self.assertEqual(res_view_a.content, content_a)
        self.assertIn("no-store", res_view_a.headers.get("cache-control", "").lower())
        self.assertIn("no-cache", res_view_a.headers.get("cache-control", "").lower())

        # 3. Replace Document A with Document B
        content_b = b"%PDF-1.4 Replacement Document B Content Version 2.0 (Updated Aadhaar)"
        res2 = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {self.token_student_a}"},
            data={"document_type": "GOVERNMENT_ID"},
            files={"file": ("aadhaar_doc_b_updated.pdf", io.BytesIO(content_b), "application/pdf")}
        )
        self.assertEqual(res2.status_code, 200)
        docs2 = res2.json()["documents"]
        gov_doc2 = next(d for d in docs2 if d["document_type"] == "GOVERNMENT_ID")
        self.assertEqual(gov_doc2["id"], doc_id, "Document UUID should be preserved for stable referencing")
        self.assertEqual(gov_doc2["original_filename"], "aadhaar_doc_b_updated.pdf")

        # Verify old file on disk was cleaned up and new file exists
        self.db.refresh(doc_db)
        new_storage_path = Path(settings.DOCUMENT_STORAGE_PATH) / doc_db.storage_path
        self.assertTrue(new_storage_path.exists(), "New document file B must exist on disk")
        self.assertFalse(old_storage_path.exists(), "Old document file A must be deleted after replacement")

        # 4. Student retrieval MUST return Document B content
        res_student_b = self.client.get(
            f"/api/v1/applications/{app_id}/documents/{doc_id}/file",
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        self.assertEqual(res_student_b.status_code, 200)
        self.assertEqual(res_student_b.content, content_b)
        self.assertIn("no-store", res_student_b.headers.get("cache-control", "").lower())
        self.assertIn("no-cache", res_student_b.headers.get("cache-control", "").lower())

        # 5. Admin retrieval MUST return Document B content
        res_admin_b = self.client.get(
            f"/api/v1/applications/{app_id}/documents/{doc_id}/file",
            headers={"Authorization": f"Bearer {self.token_admin_a}"}
        )
        self.assertEqual(res_admin_b.status_code, 200)
        self.assertEqual(res_admin_b.content, content_b)
        self.assertIn("no-store", res_admin_b.headers.get("cache-control", "").lower())

    def test_02_reverification_processes_replaced_document(self):
        """
        Uploading all 4 documents, replacing Document 1, and triggering verification
        proves reverification uses the new Document B.
        """
        app_id = str(self.app_a.id)

        # Upload 4 required documents
        doc_specs = [
            ("GOVERNMENT_ID", "aadhaar_v1.pdf", b"%PDF-1.4 Aadhaar Original V1"),
            ("MARKSHEET", "marksheet.pdf", b"%PDF-1.4 Marksheet Valid"),
            ("INCOME_CERTIFICATE", "income.pdf", b"%PDF-1.4 Income Valid"),
            ("DOMICILE_CERTIFICATE", "domicile.pdf", b"%PDF-1.4 Domicile Valid"),
        ]
        for dtype, fname, fbytes in doc_specs:
            res = self.client.post(
                f"/api/v1/applications/{app_id}/documents",
                headers={"Authorization": f"Bearer {self.token_student_a}"},
                data={"document_type": dtype},
                files={"file": (fname, io.BytesIO(fbytes), "application/pdf")}
            )
            self.assertEqual(res.status_code, 200)

        # First verification
        res_ver1 = self.client.post(
            f"/api/v1/applications/{app_id}/verify",
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        self.assertEqual(res_ver1.status_code, 200)

        # Admin requests correction on GOVERNMENT_ID
        res_corr = self.client.post(
            f"/api/v1/applications/{app_id}/admin-review/request-correction",
            headers={"Authorization": f"Bearer {self.token_admin_a}"},
            json={"document_types": ["GOVERNMENT_ID"], "reason": "Name on Aadhaar is partially blurred"}
        )
        self.assertEqual(res_corr.status_code, 200)

        # Student replaces GOVERNMENT_ID with Document B
        replacement_bytes = b"%PDF-1.4 Aadhaar Clear Document B"
        res_replace = self.client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers={"Authorization": f"Bearer {self.token_student_a}"},
            data={"document_type": "GOVERNMENT_ID"},
            files={"file": ("aadhaar_clear_b.pdf", io.BytesIO(replacement_bytes), "application/pdf")}
        )
        self.assertEqual(res_replace.status_code, 200)

        # Re-verify
        res_ver2 = self.client.post(
            f"/api/v1/applications/{app_id}/verify",
            headers={"Authorization": f"Bearer {self.token_student_a}"}
        )
        self.assertEqual(res_ver2.status_code, 200)
        data_ver2 = res_ver2.json()

        # Verify audit history and correction request are preserved across reverification
        extracted = data_ver2.get("extracted_data") or {}
        self.assertIn("review_history", extracted, "Audit history must be preserved across reverification")
        self.assertIn("correction_request", extracted, "Correction request tracking must be preserved across reverification")

        # Verify Document B is retrieved by student and admin
        doc_record = self.db.query(Document).filter(
            Document.application_id == self.app_a.id,
            Document.document_type == DocumentType.GOVERNMENT_ID
        ).first()
        res_stream = self.client.get(
            f"/api/v1/applications/{app_id}/documents/{doc_record.id}/file",
            headers={"Authorization": f"Bearer {self.token_admin_a}"}
        )
        self.assertEqual(res_stream.status_code, 200)
        self.assertEqual(res_stream.content, replacement_bytes)


if __name__ == "__main__":
    unittest.main()
