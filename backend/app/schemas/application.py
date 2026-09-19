import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.db.models.enums import ApplicationStatus, DocumentType, UploadStatus

MAHADBT_SCHEMES = [
    "Post Matric Scholarship to VJNT Students",
    "Post Matric Scholarship to OBC Students",
    "Post Matric Scholarship to SBC Students",
    "Post Matric Scholarship to the Girls Belonging to Other Backward Classes taking admission in Professional Courses",
    "Rajarshi Chhatrapati Shahu Maharaj Shikshan Shulkh Shishyavrutti Yojna (EBC)",
    "Dr. Panjabrao Deshmukh Vasatigruh Nirvah Bhatta Yojna (DTE)",
    "State Minority Scholarship Part II (DHE)",
    "Scholarship for students of minority communities pursuing Higher and Professional courses (DTE)"
]

class ApplicationCreateRequest(BaseModel):
    scholarship_name: str


class DocumentUploadRequest(BaseModel):
    document_type: str
    original_filename: Optional[str] = "document.pdf"


class DocumentResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    document_type: DocumentType
    original_filename: str
    upload_status: UploadStatus
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    college_id: uuid.UUID
    student_name: str
    application_number: str
    scholarship_name: str
    status: ApplicationStatus
    documents_uploaded_count: int
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentResponse] = []

    model_config = ConfigDict(from_attributes=True)
