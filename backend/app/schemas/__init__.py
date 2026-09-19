from app.schemas.college import (
    CollegeBase,
    CollegeCreate,
    CollegeUpdate,
    CollegeResponse,
)
from app.schemas.student import (
    StudentBase,
    StudentCreate,
    StudentUpdate,
    StudentResponse,
)
from app.schemas.admin_officer import (
    AdminOfficerBase,
    AdminOfficerCreate,
    AdminOfficerUpdate,
    AdminOfficerResponse,
)
from app.schemas.scholarship_application import (
    ScholarshipApplicationBase,
    ScholarshipApplicationCreate,
    ScholarshipApplicationUpdate,
    ScholarshipApplicationResponse,
)
from app.schemas.document import (
    DocumentBase,
    DocumentCreate,
    DocumentResponse,
)
from app.schemas.verification_result import (
    VerificationResultBase,
    VerificationResultCreate,
    VerificationResultResponse,
)
from app.schemas.appointment import (
    AppointmentBase,
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
)
from app.schemas.auth import (
    StudentRegisterRequest,
    LoginRequest,
    AdminLoginRequest,
    TokenResponse,
    TokenPayload,
    UserProfileResponse,
)

__all__ = [
    "CollegeBase",
    "CollegeCreate",
    "CollegeUpdate",
    "CollegeResponse",
    "StudentBase",
    "StudentCreate",
    "StudentUpdate",
    "StudentResponse",
    "AdminOfficerBase",
    "AdminOfficerCreate",
    "AdminOfficerUpdate",
    "AdminOfficerResponse",
    "ScholarshipApplicationBase",
    "ScholarshipApplicationCreate",
    "ScholarshipApplicationUpdate",
    "ScholarshipApplicationResponse",
    "DocumentBase",
    "DocumentCreate",
    "DocumentResponse",
    "VerificationResultBase",
    "VerificationResultCreate",
    "VerificationResultResponse",
    "AppointmentBase",
    "AppointmentCreate",
    "AppointmentUpdate",
    "AppointmentResponse",
    "StudentRegisterRequest",
    "LoginRequest",
    "AdminLoginRequest",
    "TokenResponse",
    "TokenPayload",
    "UserProfileResponse",
]
