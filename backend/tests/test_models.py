import unittest
import uuid
from datetime import date, datetime, time

# Import SQLAlchemy models & Enums
from app.db.models import (
    Base,
    College,
    Student,
    AdminOfficer,
    ScholarshipApplication,
    Document,
    VerificationResult,
    PhysicalVerificationAppointment,
    ApplicationStatus,
    DocumentType,
    UploadStatus,
    VerificationStatus,
    AppointmentStatus,
)

# Import Pydantic schemas
from app.schemas import (
    CollegeCreate,
    CollegeResponse,
    StudentCreate,
    StudentResponse,
    AdminOfficerCreate,
    AdminOfficerResponse,
    ScholarshipApplicationCreate,
    ScholarshipApplicationResponse,
    DocumentCreate,
    DocumentResponse,
    VerificationResultCreate,
    VerificationResultResponse,
    AppointmentCreate,
    AppointmentResponse,
)

class TestDatabaseModelsAndSchemas(unittest.TestCase):

    def test_model_imports_and_metadata(self):
        """Verify all 7 SQLAlchemy models register correctly in Base.metadata"""
        table_names = set(Base.metadata.tables.keys())
        expected_tables = {
            "colleges",
            "students",
            "admin_officers",
            "scholarship_applications",
            "documents",
            "verification_results",
            "physical_verification_appointments",
        }
        self.assertTrue(expected_tables.issubset(table_names))

    def test_college_model_and_schema(self):
        """Test College schema validation and instantiation"""
        c_id = uuid.uuid4()
        now = datetime.now()
        college_data = CollegeCreate(
            college_name="Demo Engineering College",
            college_code="DEMO001",
            email="info@demo.edu",
            address="Pune, Maharashtra"
        )
        self.assertEqual(college_data.college_code, "DEMO001")
        response = CollegeResponse(
            id=c_id,
            created_at=now,
            updated_at=now,
            **college_data.model_dump()
        )
        self.assertEqual(response.id, c_id)

    def test_student_model_and_schema(self):
        """Test Student schema validation and instantiation"""
        c_id = uuid.uuid4()
        student_data = StudentCreate(
            college_id=c_id,
            full_name="Rahul Sharma",
            email="rahul.sharma@example.com",
            phone_number="+919876543210",
            government_id_number="XXXX-XXXX-4892",
            date_of_birth=date(2004, 5, 14),
            address="Pune, Maharashtra"
        )
        self.assertEqual(student_data.full_name, "Rahul Sharma")
        self.assertEqual(student_data.email, "rahul.sharma@example.com")

        # Test StudentResponse schema with UUID
        s_id = uuid.uuid4()
        now = datetime.now()
        response = StudentResponse(
            id=s_id,
            created_at=now,
            updated_at=now,
            **student_data.model_dump()
        )
        self.assertEqual(response.id, s_id)
        self.assertEqual(response.college_id, c_id)

    def test_admin_officer_model_and_schema(self):
        """Test AdminOfficer schema validation and instantiation"""
        c_id = uuid.uuid4()
        admin_data = AdminOfficerCreate(
            college_id=c_id,
            full_name="Dr. V. K. Deshmukh",
            email="admin@vericampus.edu",
            phone_number="+919811122233",
            department="Scholarship Cell",
            designation="Chief Verification Officer"
        )
        self.assertTrue(admin_data.is_active)
        self.assertEqual(admin_data.department, "Scholarship Cell")

    def test_scholarship_application_model_and_schema(self):
        """Test ScholarshipApplication schema and Enum status"""
        stu_id = uuid.uuid4()
        app_data = ScholarshipApplicationCreate(
            student_id=stu_id,
            scholarship_name="Merit Scholarship 2026",
            application_number="VC-2026-001",
            status=ApplicationStatus.NEEDS_REVIEW
        )
        self.assertEqual(app_data.status, ApplicationStatus.NEEDS_REVIEW)
        self.assertEqual(app_data.application_number, "VC-2026-001")

    def test_document_model_and_schema(self):
        """Test Document schema with 4 required document types"""
        app_id = uuid.uuid4()
        for doc_type in [
            DocumentType.GOVERNMENT_ID,
            DocumentType.MARKSHEET,
            DocumentType.INCOME_CERTIFICATE,
            DocumentType.DOMICILE_CERTIFICATE
        ]:
            doc_data = DocumentCreate(
                application_id=app_id,
                document_type=doc_type,
                original_filename=f"test_{doc_type.value.lower()}.pdf",
                upload_status=UploadStatus.UPLOADED
            )
            self.assertEqual(doc_data.upload_status, UploadStatus.UPLOADED)

    def test_verification_result_model_and_schema(self):
        """Test VerificationResult schema with JSON extractions"""
        app_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        result_data = VerificationResultCreate(
            application_id=app_id,
            document_id=doc_id,
            overall_score=94.5,
            verification_status=VerificationStatus.VERIFIED,
            extracted_data={"name": "Rahul Sharma", "marks": "91.4%"},
            field_checks={"name_match": True, "income_valid": True}
        )
        self.assertEqual(result_data.overall_score, 94.5)
        self.assertEqual(result_data.extracted_data["name"], "Rahul Sharma")

    def test_appointment_model_and_schema(self):
        """Test PhysicalVerificationAppointment schema"""
        app_id = uuid.uuid4()
        stu_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        appt_data = AppointmentCreate(
            application_id=app_id,
            student_id=stu_id,
            scheduled_by_admin_id=admin_id,
            scheduled_date=date(2026, 9, 25),
            scheduled_time=time(11, 30),
            venue="Room 204, VeriCampus Main Campus",
            purpose="Physical Document Verification",
            status=AppointmentStatus.SCHEDULED
        )
        self.assertEqual(appt_data.status, AppointmentStatus.SCHEDULED)
        self.assertEqual(appt_data.venue, "Room 204, VeriCampus Main Campus")

if __name__ == "__main__":
    unittest.main()
