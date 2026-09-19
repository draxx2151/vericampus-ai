import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.models.enums import ApplicationStatus

class ScholarshipApplication(Base):
    __tablename__ = "scholarship_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    scholarship_name: Mapped[str] = mapped_column(String(255), nullable=False)
    application_number: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, native_enum=False),
        default=ApplicationStatus.DRAFT,
        nullable=False
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="applications")
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="application", cascade="all, delete-orphan"
    )
    verification_results: Mapped[List["VerificationResult"]] = relationship(
        "VerificationResult", back_populates="application", cascade="all, delete-orphan"
    )
    appointments: Mapped[List["PhysicalVerificationAppointment"]] = relationship(
        "PhysicalVerificationAppointment", back_populates="application", cascade="all, delete-orphan"
    )
