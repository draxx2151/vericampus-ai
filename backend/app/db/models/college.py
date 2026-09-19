import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class College(Base):
    __tablename__ = "colleges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    college_name: Mapped[str] = mapped_column(String(255), nullable=False)
    college_code: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, index=True, nullable=True
    )
    admin_setup_code: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, index=True, nullable=True
    )
    is_setup_code_used: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    # Exactly ONE admin officer per college
    admin_officer: Mapped[Optional["AdminOfficer"]] = relationship(
        "AdminOfficer", back_populates="college", uselist=False, cascade="all, delete-orphan"
    )
    # Many students per college
    students: Mapped[List["Student"]] = relationship(
        "Student", back_populates="college", cascade="all, delete-orphan"
    )
