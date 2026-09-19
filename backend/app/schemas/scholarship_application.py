import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.db.models.enums import ApplicationStatus

class ScholarshipApplicationBase(BaseModel):
    scholarship_name: str
    application_number: str
    status: ApplicationStatus = ApplicationStatus.DRAFT


class ScholarshipApplicationCreate(BaseModel):
    student_id: uuid.UUID
    scholarship_name: str
    application_number: str
    status: Optional[ApplicationStatus] = ApplicationStatus.DRAFT


class ScholarshipApplicationUpdate(BaseModel):
    scholarship_name: Optional[str] = None
    status: Optional[ApplicationStatus] = None
    submitted_at: Optional[datetime] = None


class ScholarshipApplicationResponse(ScholarshipApplicationBase):
    id: uuid.UUID
    student_id: uuid.UUID
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
