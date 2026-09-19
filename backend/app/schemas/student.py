import uuid
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

class StudentBase(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    government_id_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None


class StudentCreate(StudentBase):
    college_id: Optional[uuid.UUID] = None


class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    government_id_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None


class StudentResponse(StudentBase):
    id: uuid.UUID
    college_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
