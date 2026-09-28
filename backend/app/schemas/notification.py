import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.db.models.enums import UserRole

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    college_id: str
    student_id: Optional[str] = None
    application_id: Optional[str] = None
    application_number: Optional[str] = None
    applicationId: Optional[str] = None
    recipient_role: str
    event_type: str
    title: str
    message: str
    is_read: bool
    read_at: Optional[str] = None
    created_at: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    unread_count: int
    total_count: int

class NotificationMarkReadRequest(BaseModel):
    is_read: bool = True
