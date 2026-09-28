import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.models.enums import UserRole

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    college_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=True, index=True
    )
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scholarship_applications.id", ondelete="CASCADE"), nullable=True, index=True
    )
    recipient_role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    message: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    event_metadata: Mapped[Optional[Any]] = mapped_column(
        JSON, nullable=True
    )

    # Relationships
    college: Mapped["College"] = relationship("College")
    student: Mapped[Optional["Student"]] = relationship("Student")
    application: Mapped[Optional["ScholarshipApplication"]] = relationship("ScholarshipApplication")
