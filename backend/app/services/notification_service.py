import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from fastapi import HTTPException, status

from app.db.models.notification import Notification
from app.db.models.scholarship_application import ScholarshipApplication
from app.db.models.enums import UserRole


class NotificationService:
    @staticmethod
    def format_notification(notif: Notification) -> dict:
        app_num = None
        if notif.application:
            app_num = notif.application.application_number
        elif notif.event_metadata and isinstance(notif.event_metadata, dict):
            app_num = notif.event_metadata.get("application_number")

        created_str = notif.created_at.isoformat() if notif.created_at else datetime.now().isoformat()

        return {
            "id": str(notif.id),
            "college_id": str(notif.college_id),
            "student_id": str(notif.student_id) if notif.student_id else None,
            "application_id": str(notif.application_id) if notif.application_id else None,
            "application_number": app_num,
            "applicationId": app_num or (str(notif.application_id) if notif.application_id else None),
            "recipient_role": notif.recipient_role.value if hasattr(notif.recipient_role, 'value') else str(notif.recipient_role),
            "event_type": notif.event_type,
            "title": notif.title,
            "message": notif.message,
            "is_read": bool(notif.is_read),
            "read_at": notif.read_at.isoformat() if notif.read_at else None,
            "created_at": created_str,
            "timestamp": created_str,
            "metadata": notif.event_metadata or {},
        }

    @classmethod
    def create_notification(
        cls,
        db: Session,
        college_id: Union[uuid.UUID, str],
        recipient_role: UserRole,
        event_type: str,
        title: str,
        message: str,
        student_id: Optional[Union[uuid.UUID, str]] = None,
        application_id: Optional[Union[uuid.UUID, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        college_uuid = uuid.UUID(str(college_id))
        student_uuid = uuid.UUID(str(student_id)) if student_id else None
        app_uuid = uuid.UUID(str(application_id)) if application_id else None

        notif = Notification(
            id=uuid.uuid4(),
            college_id=college_uuid,
            student_id=student_uuid,
            application_id=app_uuid,
            recipient_role=recipient_role,
            event_type=event_type,
            title=title,
            message=message,
            is_read=False,
            event_metadata=metadata or {},
        )
        db.add(notif)
        return notif

    @classmethod
    def get_notifications_for_user(
        cls,
        db: Session,
        user_id_str: str,
        role: UserRole,
        college_id_str: Optional[str] = None,
    ) -> dict:
        try:
            user_uuid = uuid.UUID(str(user_id_str))
            college_uuid = uuid.UUID(str(college_id_str)) if college_id_str else None
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ID format."
            )

        if role == UserRole.STUDENT:
            query = db.query(Notification).filter(
                Notification.student_id == user_uuid,
                Notification.recipient_role == UserRole.STUDENT,
            )
            if college_uuid:
                query = query.filter(Notification.college_id == college_uuid)
        elif role == UserRole.ADMIN:
            if not college_uuid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Admin college ID is required to fetch notifications."
                )
            query = db.query(Notification).filter(
                Notification.college_id == college_uuid,
                Notification.recipient_role == UserRole.ADMIN,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized notification access."
            )

        notifications = query.order_by(Notification.created_at.desc()).all()
        formatted = [cls.format_notification(n) for n in notifications]
        unread_count = sum(1 for n in notifications if not n.is_read)

        return {
            "notifications": formatted,
            "unread_count": unread_count,
            "total_count": len(formatted),
        }

    @classmethod
    def mark_notification_as_read(
        cls,
        db: Session,
        notification_id_str: str,
        user_id_str: str,
        role: UserRole,
        college_id_str: Optional[str] = None,
    ) -> dict:
        try:
            notif_uuid = uuid.UUID(str(notification_id_str))
            user_uuid = uuid.UUID(str(user_id_str))
            college_uuid = uuid.UUID(str(college_id_str)) if college_id_str else None
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ID format."
            )

        notif = db.query(Notification).filter(Notification.id == notif_uuid).first()
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found."
            )

        # Enforce tenant isolation and ownership
        if role == UserRole.STUDENT:
            if notif.student_id != user_uuid or notif.recipient_role != UserRole.STUDENT:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You do not own this notification."
                )
        elif role == UserRole.ADMIN:
            if not college_uuid or notif.college_id != college_uuid or notif.recipient_role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Cross-college notification access is prohibited."
                )

        notif.is_read = True
        notif.read_at = func.now()
        db.commit()
        db.refresh(notif)

        return cls.format_notification(notif)

    @classmethod
    def mark_all_as_read(
        cls,
        db: Session,
        user_id_str: str,
        role: UserRole,
        college_id_str: Optional[str] = None,
    ) -> dict:
        try:
            user_uuid = uuid.UUID(str(user_id_str))
            college_uuid = uuid.UUID(str(college_id_str)) if college_id_str else None
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ID format."
            )

        if role == UserRole.STUDENT:
            query = db.query(Notification).filter(
                Notification.student_id == user_uuid,
                Notification.recipient_role == UserRole.STUDENT,
                Notification.is_read.is_(False)
            )
            if college_uuid:
                query = query.filter(Notification.college_id == college_uuid)
        elif role == UserRole.ADMIN:
            if not college_uuid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Admin college ID is required."
                )
            query = db.query(Notification).filter(
                Notification.college_id == college_uuid,
                Notification.recipient_role == UserRole.ADMIN,
                Notification.is_read.is_(False)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized notification access."
            )

        count = query.update(
            {"is_read": True, "read_at": func.now()},
            synchronize_session=False
        )
        db.commit()

        return {"marked_count": count, "status": "success"}
