import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

class CollegeBase(BaseModel):
    college_name: str
    college_code: str
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    is_active: bool = True


class CollegeCreate(CollegeBase):
    pass


class CollegeUpdate(BaseModel):
    college_name: Optional[str] = None
    college_code: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class CollegeResponse(CollegeBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
