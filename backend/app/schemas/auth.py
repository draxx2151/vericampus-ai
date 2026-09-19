import uuid
from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from app.db.models.enums import UserRole

class StudentRegisterRequest(BaseModel):
    college_code: str
    full_name: str
    email: EmailStr
    password: str
    phone_number: Optional[str] = None
    government_id_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    college_code: Optional[str] = None
    role: Optional[UserRole] = None


class AdminLoginRequest(BaseModel):
    college_code: str
    email: EmailStr
    password: str


class AdminRegisterRequest(BaseModel):
    admin_setup_code: str
    full_name: str
    email: EmailStr
    password: str
    phone_number: Optional[str] = None
    department: Optional[str] = "Scholarship Cell"
    designation: Optional[str] = "Verification Officer"


class CollegeCodeUpdateRequest(BaseModel):
    college_code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    college_id: uuid.UUID
    email: EmailStr
    role: UserRole
    expires_in_seconds: int

    model_config = ConfigDict(from_attributes=True)


class TokenPayload(BaseModel):
    sub: str
    role: UserRole
    college_id: uuid.UUID
    exp: int
    iat: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    college_id: uuid.UUID
    full_name: str
    email: EmailStr
    role: UserRole
    phone_number: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)
