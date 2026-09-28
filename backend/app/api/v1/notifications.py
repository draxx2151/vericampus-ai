from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_token_payload
from app.schemas.auth import TokenPayload
from app.schemas.notification import NotificationResponse, NotificationListResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="Get Notifications for Authenticated User",
    description="Fetches real workflow notifications for current user. Students see their personal alerts; College Admins see tenant-scoped college audit events."
)
def get_notifications(
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    college_id_str = str(current_payload.college_id) if current_payload.college_id else None
    return NotificationService.get_notifications_for_user(
        db=db,
        user_id_str=current_payload.sub,
        role=current_payload.role,
        college_id_str=college_id_str
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark Notification as Read",
    description="Marks a specific notification as read. Validates user ownership and college tenant isolation."
)
def mark_notification_as_read(
    notification_id: str,
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    college_id_str = str(current_payload.college_id) if current_payload.college_id else None
    return NotificationService.mark_notification_as_read(
        db=db,
        notification_id_str=notification_id,
        user_id_str=current_payload.sub,
        role=current_payload.role,
        college_id_str=college_id_str
    )


@router.post(
    "/mark-all-read",
    summary="Mark All Notifications as Read",
    description="Marks all unread notifications as read for current user/tenant role."
)
def mark_all_notifications_as_read(
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    college_id_str = str(current_payload.college_id) if current_payload.college_id else None
    return NotificationService.mark_all_as_read(
        db=db,
        user_id_str=current_payload.sub,
        role=current_payload.role,
        college_id_str=college_id_str
    )
