from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_token_payload
from app.services.auth_service import AuthService
from app.schemas.auth import (
    StudentRegisterRequest,
    AdminRegisterRequest,
    LoginRequest,
    AdminLoginRequest,
    TokenResponse,
    TokenPayload,
    UserProfileResponse,
)
from app.schemas.student import StudentResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/student/register",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Student user",
    description="Registers a new Student account bound to a valid college using college_code. Rejects duplicate emails or invalid college codes."
)
def register_student(
    req: StudentRegisterRequest,
    db: Session = Depends(get_db)
):
    student = AuthService.register_student(db, req)
    return student


@router.post(
    "/admin/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Admin Officer via Setup Code",
    description="Registers a new Admin Officer account using a private one-time-use Admin Setup Code. Enforces 1 admin officer per college rule and invalidates the setup code upon completion."
)
def register_admin(
    req: AdminRegisterRequest,
    db: Session = Depends(get_db)
):
    return AuthService.register_admin(db, req)


@router.post(
    "/admin/login",
    response_model=TokenResponse,
    summary="Admin Officer Login",
    description="Authenticates an Admin Officer using College Code + Email + Password. All three credentials are required."
)
def admin_login(
    req: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    return AuthService.authenticate_admin(db, req)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Unified User Login",
    description="Authenticates either Student (Email + Password) or AdminOfficer (College Code + Email + Password). Returns a signed JWT access token containing user ID, role, and college ID."
)
def login(
    req: LoginRequest,
    db: Session = Depends(get_db)
):
    return AuthService.authenticate_user(db, req)


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get Authenticated User Profile",
    description="Validates Bearer JWT access token and returns current authenticated user profile including college_id."
)
def get_current_user_profile(
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    return AuthService.get_user_profile(db, current_payload.sub, current_payload.role)
