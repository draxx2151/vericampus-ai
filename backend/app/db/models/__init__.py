from app.db.base import Base
from app.db.models.enums import (
    UserRole,
    ApplicationStatus,
    DocumentType,
    UploadStatus,
    VerificationStatus,
    AppointmentStatus,
)
from app.db.models.college import College
from app.db.models.student import Student
from app.db.models.admin_officer import AdminOfficer
from app.db.models.scholarship_application import ScholarshipApplication
from app.db.models.document import Document
from app.db.models.verification_result import VerificationResult
from app.db.models.appointment import PhysicalVerificationAppointment

__all__ = [
    "Base",
    "UserRole",
    "ApplicationStatus",
    "DocumentType",
    "UploadStatus",
    "VerificationStatus",
    "AppointmentStatus",
    "College",
    "Student",
    "AdminOfficer",
    "ScholarshipApplication",
    "Document",
    "VerificationResult",
    "PhysicalVerificationAppointment",
]
