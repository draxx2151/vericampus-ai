import uuid
from datetime import date, time, datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from app.db.models.enums import DocumentType, AppointmentStatus


class ApproveApplicationRequest(BaseModel):
    remarks: Optional[str] = Field(None, description="Optional administrative approval notes")
    notes: Optional[str] = Field(None, description="Optional alias for remarks")

    @model_validator(mode="after")
    def populate_remarks(self):
        if not self.remarks and self.notes:
            self.remarks = self.notes
        return self


class RequestCorrectionRequest(BaseModel):
    document_types: List[DocumentType] = Field(
        ...,
        min_length=1,
        description="One or more document types requiring student replacement",
    )
    reason: str = Field(
        ...,
        min_length=5,
        description="Specific justification for the correction request",
    )

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 5:
            raise ValueError("Correction reason must be at least 5 characters long.")
        return s


class SchedulePhysicalVerificationRequest(BaseModel):
    scheduled_date: date = Field(..., description="Date for physical verification (YYYY-MM-DD)")
    scheduled_time: time = Field(..., description="Time for physical verification (HH:MM, HH:MM:SS, or 10:30 AM/PM)")
    venue: str = Field(..., min_length=3, description="Physical location or office room")
    instructions: Optional[str] = Field(
        "Bring original copies of all uploaded documents for physical verification.",
        description="Instructions for the student attendee",
    )

    @field_validator("scheduled_time", mode="before")
    @classmethod
    def parse_scheduled_time(cls, v: Any) -> time:
        if isinstance(v, time):
            return v
        if isinstance(v, str):
            s = v.strip()
            for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p", "%I:%M %P", "%I:%M%P"):
                try:
                    return datetime.strptime(s, fmt).time()
                except ValueError:
                    continue
        raise ValueError("Invalid time format. Use HH:MM, HH:MM:SS, or 10:30 AM/PM.")

    @field_validator("venue")
    @classmethod
    def validate_venue(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 3:
            raise ValueError("Venue description must be at least 3 characters long.")
        return s


class CompletePhysicalVerificationRequest(BaseModel):
    result: Literal["VERIFIED", "NOT_VERIFIED"] = Field(
        ...,
        description="Physical document verification outcome",
    )
    remarks: str = Field(
        ...,
        min_length=3,
        description="Officer notes detailing physical inspection outcome",
    )

    @field_validator("remarks")
    @classmethod
    def validate_remarks(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 3:
            raise ValueError("Officer remarks must be at least 3 characters long.")
        return s


class RejectApplicationRequest(BaseModel):
    reason: str = Field(
        ...,
        min_length=5,
        description="Mandatory justification for application rejection",
    )

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 5:
            raise ValueError("Rejection reason must be at least 5 characters long.")
        return s


class PhysicalVerificationResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    status: AppointmentStatus
    scheduled_date: date
    scheduled_time: str
    venue: str
    instructions: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
