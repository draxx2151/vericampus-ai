from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_token_payload, require_admin_user
from app.db.models.enums import UserRole
from app.services.auth_service import AuthService
from app.schemas.auth import TokenPayload, CollegeCodeUpdateRequest

router = APIRouter(prefix="/admin", tags=["Admin Management"])


@router.put(
    "/college-code",
    summary="Set / Update Student-Facing College Code",
    description="Allows authenticated Admin Officer to set or update their college's student-facing college code (e.g. COLLEGE001)."
)
def update_college_code(
    req: CollegeCodeUpdateRequest,
    current_payload: TokenPayload = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    return AuthService.update_college_code(db, current_payload.sub, req.college_code)


@router.get(
    "/college",
    summary="Get Current Admin College Information",
    description="Returns current college details and configuration for the authenticated Admin Officer."
)
def get_admin_college(
    current_payload: TokenPayload = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    return AuthService.get_admin_college(db, current_payload.sub)
