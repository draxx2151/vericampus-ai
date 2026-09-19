import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.db.models.enums import VerificationStatus

class VerificationResultBase(BaseModel):
    overall_score: Optional[float] = None
    verification_status: VerificationStatus = VerificationStatus.PENDING
    extracted_data: Optional[Dict[str, Any]] = None
    field_checks: Optional[Dict[str, Any]] = None
    cross_document_matches: Optional[Dict[str, Any]] = None
    issues: Optional[Dict[str, Any]] = None


class VerificationResultCreate(VerificationResultBase):
    application_id: uuid.UUID
    document_id: Optional[uuid.UUID] = None


class VerificationResultResponse(VerificationResultBase):
    id: uuid.UUID
    application_id: uuid.UUID
    document_id: Optional[uuid.UUID] = None
    verified_by_admin_id: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
