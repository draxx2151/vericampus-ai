import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

class AdminOfficerBase(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    is_active: bool = True


class AdminOfficerCreate(AdminOfficerBase):
    college_id: Optional[uuid.UUID] = None


class AdminOfficerUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    is_active: Optional[bool] = None


class AdminOfficerResponse(AdminOfficerBase):
    id: uuid.UUID
    college_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
