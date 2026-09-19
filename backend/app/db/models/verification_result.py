import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import Float, DateTime, ForeignKey, Enum as SQLEnum, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.models.enums import VerificationStatus

class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scholarship_applications.id", ondelete="CASCADE"), nullable=False
    )
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SQLEnum(VerificationStatus, native_enum=False),
        default=VerificationStatus.PENDING,
        nullable=False
    )
    extracted_data: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    field_checks: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    cross_document_matches: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    issues: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    verified_by_admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_officers.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    document: Mapped[Optional["Document"]] = relationship("Document", back_populates="verification_results")
    application: Mapped["ScholarshipApplication"] = relationship(
        "ScholarshipApplication", back_populates="verification_results"
    )
    verified_by_admin: Mapped[Optional["AdminOfficer"]] = relationship(
        "AdminOfficer", back_populates="reviewed_results"
    )
