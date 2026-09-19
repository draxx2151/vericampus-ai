import uuid
from datetime import datetime, date, time
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.db.models.enums import AppointmentStatus

class AppointmentBase(BaseModel):
    scheduled_date: date
    scheduled_time: time
    venue: str
    purpose: Optional[str] = None
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    application_id: uuid.UUID
    student_id: uuid.UUID
    scheduled_by_admin_id: Optional[uuid.UUID] = None


class AppointmentUpdate(BaseModel):
    scheduled_date: Optional[date] = None
    scheduled_time: Optional[time] = None
    venue: Optional[str] = None
    purpose: Optional[str] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    id: uuid.UUID
    application_id: uuid.UUID
    student_id: uuid.UUID
    scheduled_by_admin_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
