import uuid
from datetime import datetime, date, time
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.db.models.scholarship_application import ScholarshipApplication
from app.db.models.document import Document
from app.db.models.student import Student
from app.db.models.admin_officer import AdminOfficer
from app.db.models.verification_result import VerificationResult
from app.db.models.appointment import PhysicalVerificationAppointment
from app.db.models.enums import (
    ApplicationStatus,
    DocumentType,
    VerificationStatus,
    AppointmentStatus,
    UserRole,
)
from app.services.verification.verification_service import REQUIRED_VERIFICATION_DOCUMENTS
from app.services.notification_service import NotificationService


class AdminReviewService:
    """
    Dedicated service for Administrative Review and Human-in-the-Loop decision making.
    Supports:
      1. APPROVE / VERIFY
      2. REQUEST DOCUMENT CORRECTION
      3. REQUIRE PHYSICAL VERIFICATION (schedule session)
      4. RECORD PHYSICAL VERIFICATION RESULT
      5. REJECT

    CRITICAL SAFEGUARDS:
      - The AI verification engine and ML risk model provide decision support only.
      - Final scholarship approval, rejection, correction request, and physical verification
        are strictly executed by authenticated administrators of the matching college.
      - Enforces strict multi-college tenant isolation.
    """

    @classmethod
    def _validate_admin_and_application(
        cls,
        db: Session,
        app_id_str: str,
        admin_id_str: str,
        admin_college_id_str: str,
    ) -> Tuple[ScholarshipApplication, AdminOfficer]:
        # 1. Parse and validate UUIDs
        try:
            app_uuid = uuid.UUID(str(app_id_str))
            admin_uuid = uuid.UUID(str(admin_id_str))
            college_uuid = uuid.UUID(str(admin_college_id_str))
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ID format.",
            )

        # 2. Verify Admin Officer exists and belongs to the specified college
        admin = db.query(AdminOfficer).filter(AdminOfficer.id == admin_uuid).first()
        if not admin or not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Administrative officer not found or account is inactive.",
            )

        if admin.college_id != college_uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Admin does not belong to the authorized college.",
            )

        # 3. Load Application
        app = db.query(ScholarshipApplication).filter(
            ScholarshipApplication.id == app_uuid
        ).first()

        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scholarship application not found.",
            )

        # 4. Strict College Tenant Isolation
        if not app.student or app.student.college_id != college_uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cross-college administrative action is strictly prohibited.",
            )

        return app, admin

    @classmethod
    def _get_or_create_app_verification_result(
        cls, db: Session, app: ScholarshipApplication
    ) -> VerificationResult:
        res = db.query(VerificationResult).filter(
            VerificationResult.application_id == app.id,
            VerificationResult.document_id.is_(None),
        ).first()

        if not res:
            res = VerificationResult(
                id=uuid.uuid4(),
                application_id=app.id,
                document_id=None,
                verification_status=VerificationStatus.PENDING,
                extracted_data={},
                issues=[],
            )
            db.add(res)
            db.flush()

        if res.extracted_data is None:
            res.extracted_data = {}
        if res.issues is None:
            res.issues = []

        return res

    @classmethod
    def _append_audit_history(
        cls,
        res: VerificationResult,
        action: str,
        admin: AdminOfficer,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        extracted = dict(res.extracted_data or {})
        history = list(extracted.get("review_history") or [])

        history.append({
            "action": action,
            "admin_id": str(admin.id),
            "admin_name": admin.full_name,
            "admin_email": admin.email,
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "notes": reason,
            "details": details or {},
        })

        extracted["review_history"] = history
        extracted["last_admin_action"] = {
            "action": action,
            "admin_id": str(admin.id),
            "timestamp": datetime.now().isoformat(),
        }
        res.extracted_data = extracted
        res.verified_by_admin_id = admin.id
        res.reviewed_at = func.now()

    # -------------------------------------------------------------------------
    # 1. APPROVE / VERIFY
    # -------------------------------------------------------------------------
    @classmethod
    def approve_application(
        cls,
        db: Session,
        app_id_str: str,
        admin_id_str: str,
        admin_college_id_str: str,
        remarks: Optional[str] = None,
    ) -> dict:
        app, admin = cls._validate_admin_and_application(
            db, app_id_str, admin_id_str, admin_college_id_str
        )

        # Ensure all 4 required documents exist
        doc_types_present = {d.document_type for d in app.documents}
        missing_docs = [dt for dt in REQUIRED_VERIFICATION_DOCUMENTS if dt not in doc_types_present]
        if missing_docs:
            missing_str = ", ".join(d.value for d in missing_docs)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve application. Missing required documents: {missing_str}.",
            )

        # Cannot approve an already REJECTED application directly without resubmission
        if app.status == ApplicationStatus.REJECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot approve a rejected application. Student must submit a new application or appeal.",
            )

        # Retrieve verification result
        ver_result = cls._get_or_create_app_verification_result(db, app)

        # Update statuses
        app.status = ApplicationStatus.VERIFIED
        ver_result.verification_status = VerificationStatus.VERIFIED

        # Resolve any pending correction requests
        extracted = dict(ver_result.extracted_data or {})
        if "correction_request" in extracted and isinstance(extracted["correction_request"], dict):
            extracted["correction_request"]["status"] = "RESOLVED"
            ver_result.extracted_data = extracted

        # Append audit history
        cls._append_audit_history(
            ver_result,
            action="APPROVE",
            admin=admin,
            reason=remarks or "Approved by college verification officer.",
        )

        # Real workflow notifications
        NotificationService.create_notification(
            db=db,
            college_id=admin.college_id,
            recipient_role=UserRole.STUDENT,
            event_type="APPLICATION_APPROVED",
            title="Congratulations! Application Approved",
            message=f"Your scholarship application {app.application_number} for {app.scholarship_name} has been officially approved.",
            student_id=app.student_id,
            application_id=app.id,
            metadata={"application_number": app.application_number, "scholarship_name": app.scholarship_name}
        )
        NotificationService.create_notification(
            db=db,
            college_id=admin.college_id,
            recipient_role=UserRole.ADMIN,
            event_type="APPLICATION_APPROVED",
            title="Scholarship Application Approved",
            message=f"Application {app.application_number} for {app.student.full_name if app.student else 'Applicant'} has been approved by {admin.full_name}.",
            student_id=app.student_id,
            application_id=app.id,
            metadata={"application_number": app.application_number, "student_name": app.student.full_name if app.student else "Applicant", "admin_name": admin.full_name}
        )

        try:
            db.commit()
            db.refresh(app)
            db.refresh(ver_result)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database transaction failed while approving application.",
            )

        return cls._format_admin_action_response(app, ver_result, "Application approved successfully.")

    # -------------------------------------------------------------------------
    # 2. REQUEST DOCUMENT CORRECTION
    # -------------------------------------------------------------------------
    @classmethod
    def request_document_correction(
        cls,
        db: Session,
        app_id_str: str,
        admin_id_str: str,
        admin_college_id_str: str,
        document_types: List[DocumentType],
        reason: str,
    ) -> dict:
        app, admin = cls._validate_admin_and_application(
            db, app_id_str, admin_id_str, admin_college_id_str
        )

        if not document_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one document type must be specified for correction.",
            )

        clean_reason = reason.strip() if reason else ""
        if len(clean_reason) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A detailed correction reason (minimum 5 characters) is required.",
            )

        if app.status == ApplicationStatus.REJECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot request corrections on a rejected application.",
            )

        # Verify requested documents exist on application
        existing_doc_types = {d.document_type for d in app.documents}
        invalid_types = [dt for dt in document_types if dt not in existing_doc_types]
        if invalid_types:
            invalid_str = ", ".join(dt.value for dt in invalid_types)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot request correction for documents that have not been uploaded: {invalid_str}.",
            )

        ver_result = cls._get_or_create_app_verification_result(db, app)

        # Move application and verification result to NEEDS_REVIEW
        app.status = ApplicationStatus.NEEDS_REVIEW
        ver_result.verification_status = VerificationStatus.NEEDS_REVIEW

        doc_type_values = [dt.value for dt in document_types]

        # Store structured correction request in extracted_data
        extracted = dict(ver_result.extracted_data or {})
        extracted["correction_request"] = {
            "status": "PENDING",
            "requested_at": datetime.now().isoformat(),
            "admin_id": str(admin.id),
            "requested_by": str(admin.id),
            "admin_name": admin.full_name,
            "document_types": doc_type_values,
            "requested_documents": doc_type_values,
            "reason": clean_reason,
            "resolved_documents": [],
        }
        ver_result.extracted_data = extracted

        # Append to issues
        issues = list(ver_result.issues or [])
        issues.append(
            f"Correction requested for {', '.join(doc_type_values)}: {clean_reason}"
        )
        ver_result.issues = issues

        # Record audit history
        cls._append_audit_history(
            ver_result,
            action="REQUEST_CORRECTION",
            admin=admin,
            reason=clean_reason,
            details={"document_types": doc_type_values},
        )

        # Real workflow notifications
        NotificationService.create_notification(
            db=db,
            college_id=admin.college_id,
            recipient_role=UserRole.STUDENT,
            event_type="CORRECTION_REQUESTED",
            title="Action Required: Document Correction Requested",
            message=f"Reviewing officer requested corrections for application {app.application_number}: {clean_reason}. Please upload updated files.",
            student_id=app.student_id,
            application_id=app.id,
            metadata={"reason": clean_reason, "requested_documents": doc_type_values, "application_number": app.application_number}
        )
        NotificationService.create_notification(
            db=db,
            college_id=admin.college_id,
            recipient_role=UserRole.ADMIN,
            event_type="CORRECTION_REQUESTED",
            title="Correction Request Dispatched",
            message=f"Correction request sent to {app.student.full_name if app.student else 'Applicant'} for application {app.application_number}.",
            student_id=app.student_id,
            application_id=app.id,
            metadata={"reason": clean_reason, "admin_name": admin.full_name, "application_number": app.application_number}
        )

        try:
            db.commit()
            db.refresh(app)
            db.refresh(ver_result)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database transaction failed while requesting document correction.",
            )

        return cls._format_admin_action_response(
            app, ver_result, f"Correction requested for {len(document_types)} document(s)."
        )

    # -------------------------------------------------------------------------
    # 3. REQUIRE PHYSICAL VERIFICATION (Schedule Session)
    # -------------------------------------------------------------------------
    @classmethod
    def require_physical_verification(
        cls,
        db: Session,
        app_id_str: str,
        admin_id_str: str,
        admin_college_id_str: str,
        scheduled_date: date,
        scheduled_time: time,
        venue: str,
        instructions: Optional[str] = None,
    ) -> dict:
        app, admin = cls._validate_admin_and_application(
            db, app_id_str, admin_id_str, admin_college_id_str
        )

        if app.status == ApplicationStatus.REJECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot schedule physical verification for a rejected application.",
            )

        clean_venue = venue.strip() if venue else ""
        if len(clean_venue) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Venue must be at least 3 characters long.",
            )

        clean_instructions = instructions.strip() if instructions else "Bring original documents for verification."

        # Find existing active appointment for this application
        existing_appointment = db.query(PhysicalVerificationAppointment).filter(
            PhysicalVerificationAppointment.application_id == app.id,
            PhysicalVerificationAppointment.status == AppointmentStatus.SCHEDULED,
        ).first()

        if existing_appointment:
            # Update existing scheduled session safely (no duplicate constraint violations)
            existing_appointment.scheduled_date = scheduled_date
            existing_appointment.scheduled_time = scheduled_time
            existing_appointment.venue = clean_venue
            existing_appointment.purpose = clean_instructions
            existing_appointment.notes = clean_instructions
            existing_appointment.scheduled_by_admin_id = admin.id
            existing_appointment.updated_at = func.now()
            target_appointment = existing_appointment
        else:
            target_appointment = PhysicalVerificationAppointment(
                id=uuid.uuid4(),
                application_id=app.id,
                student_id=app.student_id,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                venue=clean_venue,
                purpose=clean_instructions,
                notes=clean_instructions,
                status=AppointmentStatus.SCHEDULED,
                scheduled_by_admin_id=admin.id,
            )
            db.add(target_appointment)

        # Update application status
        app.status = ApplicationStatus.PHYSICAL_VERIFICATION_REQUIRED

        # Audit history in VerificationResult
        ver_result = cls._get_or_create_app_verification_result(db, app)
        cls._append_audit_history(
            ver_result,
            action="REQUIRE_PHYSICAL_VERIFICATION",
            admin=admin,
            reason=clean_instructions,
            details={
                "venue": clean_venue,
                "scheduled_date": scheduled_date.isoformat(),
                "scheduled_time": scheduled_time.strftime("%H:%M:%S"),
            },
        )

        # Real workflow notifications
        NotificationService.create_notification(
            db=db,
            college_id=admin.college_id,
            recipient_role=UserRole.STUDENT,
            event_type="PHYSICAL_VERIFICATION_SCHEDULED",
            title="In-Person Document Verification Scheduled",
            message=f"An in-person physical verification appointment is scheduled for {scheduled_date.isoformat()} at {scheduled_time.strftime('%I:%M %p') if scheduled_time else '10:00 AM'} (Venue: {clean_venue}).",
            student_id=app.student_id,
            application_id=app.id,
            metadata={"scheduled_date": scheduled_date.isoformat(), "venue": clean_venue, "application_number": app.application_number}
        )
        NotificationService.create_notification(
            db=db,
            college_id=admin.college_id,
            recipient_role=UserRole.ADMIN,
            event_type="PHYSICAL_VERIFICATION_SCHEDULED",
            title="Physical Verification Appointment Scheduled",
            message=f"Physical verification scheduled for student {app.student.full_name if app.student else 'Applicant'} ({app.application_number}) on {scheduled_date.isoformat()}.",
            student_id=app.student_id,
            application_id=app.id,
            metadata={"scheduled_date": scheduled_date.isoformat(), "student_name": app.student.full_name if app.student else "Applicant", "application_number": app.application_number}
        )

        try:
            db.commit()
            db.refresh(app)
            db.refresh(target_appointment)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database transaction failed while scheduling physical verification.",
            )

        return cls.format_appointment_response(target_appointment, app)

    # -------------------------------------------------------------------------
    # 4. RECORD PHYSICAL VERIFICATION RESULT
    # -------------------------------------------------------------------------
    @classmethod
    def record_physical_verification_result(
        cls,
        db: Session,
        app_id_str: str,
        admin_id_str: str,
        admin_college_id_str: str,
        result: str,
        remarks: str,
    ) -> dict:
        app, admin = cls._validate_admin_and_application(
            db, app_id_str, admin_id_str, admin_college_id_str
        )

        clean_result = result.upper().strip()
        if clean_result not in ("VERIFIED", "NOT_VERIFIED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid physical verification result. Must be 'VERIFIED' or 'NOT_VERIFIED'.",
            )

        clean_remarks = remarks.strip() if remarks else ""
        if len(clean_remarks) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Physical verification remarks must be at least 3 characters long.",
            )

        # Find active appointment
        appointment = db.query(PhysicalVerificationAppointment).filter(
            PhysicalVerificationAppointment.application_id == app.id,
            PhysicalVerificationAppointment.status == AppointmentStatus.SCHEDULED,
        ).first()

        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No scheduled physical verification appointment found for this application.",
            )

        # Mark appointment completed
        appointment.status = AppointmentStatus.COMPLETED
        appointment.notes = f"Result: {clean_result}. Remarks: {clean_remarks}"
        appointment.updated_at = func.now()

        # Retrieve verification result
        ver_result = cls._get_or_create_app_verification_result(db, app)

        # Update application and verification statuses appropriately
        if clean_result == "VERIFIED":
            app.status = ApplicationStatus.PHYSICAL_VERIFICATION_COMPLETED
            ver_result.verification_status = VerificationStatus.VERIFIED
        else:
            # If not verified, do NOT automatically reject; move to NEEDS_REVIEW
            app.status = ApplicationStatus.NEEDS_REVIEW
            ver_result.verification_status = VerificationStatus.NEEDS_REVIEW
        cls._append_audit_history(
            ver_result,
            action="COMPLETE_PHYSICAL_VERIFICATION",
            admin=admin,
            reason=clean_remarks,
            details={
                "result": clean_result,
                "appointment_id": str(appointment.id),
            },
        )

        # Real workflow notifications
        NotificationService.create_notification(
            db=db,
            college_id=admin.college_id,
            recipient_role=UserRole.STUDENT,
            event_type="PHYSICAL_VERIFICATION_COMPLETED",
            title="Physical Verification Completed",
            message=f"In-person document verification for application {app.application_number} has been recorded with result: {clean_result}.",
            student_id=app.student_id,
            application_id=app.id,
            metadata={"result_status": clean_result, "application_number": app.application_number}
        )
        NotificationService.create_notification(
            db=db,
            college_id=admin.college_id,
            recipient_role=UserRole.ADMIN,
            event_type="PHYSICAL_VERIFICATION_COMPLETED",
            title="Physical Verification Completed",
            message=f"Recorded physical verification outcome ({clean_result}) for student {app.student.full_name if app.student else 'Applicant'} ({app.application_number}).",
            student_id=app.student_id,
            application_id=app.id,
            metadata={"result_status": clean_result, "student_name": app.student.full_name if app.student else "Applicant", "application_number": app.application_number}
        )

        try:
            db.commit()
            db.refresh(app)
            db.refresh(appointment)
            db.refresh(ver_result)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database transaction failed while recording physical verification outcome.",
            )

        app_action_resp = cls._format_admin_action_response(app, ver_result)
        return {
            "message": f"Physical verification completed with result: {clean_result}.",
            "status": app_action_resp["status"],
            "verification_status": app_action_resp["verification_status"],
            "appointment": cls.format_appointment_response(appointment, app),
            "application": app_action_resp,
        }

    # -------------------------------------------------------------------------
    # 5. REJECT APPLICATION
    # -------------------------------------------------------------------------
    @classmethod
    def reject_application(
        cls,
        db: Session,
        app_id_str: str,
        admin_id_str: str,
        admin_college_id_str: str,
        reason: str,
    ) -> dict:
        app, admin = cls._validate_admin_and_application(
            db, app_id_str, admin_id_str, admin_college_id_str
        )

        clean_reason = reason.strip() if reason else ""
        if len(clean_reason) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A detailed rejection reason (minimum 5 characters) is required.",
            )

        if app.status == ApplicationStatus.REJECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Application is already rejected.",
            )

        ver_result = cls._get_or_create_app_verification_result(db, app)

        # Update statuses
        app.status = ApplicationStatus.REJECTED
        ver_result.verification_status = VerificationStatus.REJECTED

        # Append rejection reason to issues
        issues = list(ver_result.issues or [])
        issues.append(f"Application rejected by administration. Rejection reason: {clean_reason}")
        ver_result.issues = issues

        # Append audit history
        cls._append_audit_history(
            ver_result,
            action="REJECT",
            admin=admin,
            reason=clean_reason,
        )

        # Real workflow notifications
        NotificationService.create_notification(
            db=db,
            college_id=admin.college_id,
            recipient_role=UserRole.STUDENT,
            event_type="APPLICATION_REJECTED",
            title="Scholarship Application Update: Rejected",
            message=f"Your application {app.application_number} was rejected. Reason: {clean_reason}.",
            student_id=app.student_id,
            application_id=app.id,
            metadata={"reason": clean_reason, "application_number": app.application_number}
        )
        NotificationService.create_notification(
            db=db,
            college_id=admin.college_id,
            recipient_role=UserRole.ADMIN,
            event_type="APPLICATION_REJECTED",
            title="Scholarship Application Rejected",
            message=f"Application {app.application_number} for {app.student.full_name if app.student else 'Applicant'} was rejected by {admin.full_name}. Reason: {clean_reason}.",
            student_id=app.student_id,
            application_id=app.id,
            metadata={"reason": clean_reason, "student_name": app.student.full_name if app.student else "Applicant", "admin_name": admin.full_name, "application_number": app.application_number}
        )

        try:
            db.commit()
            db.refresh(app)
            db.refresh(ver_result)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database transaction failed while rejecting application.",
            )

        return cls._format_admin_action_response(app, ver_result, "Application has been rejected by administration.")

    # -------------------------------------------------------------------------
    # 6. GET PHYSICAL VERIFICATION APPOINTMENT (Student / Admin View)
    # -------------------------------------------------------------------------
    @classmethod
    def get_physical_verification_appointment(
        cls,
        db: Session,
        app_id_str: Optional[str] = None,
        user_id_str: Optional[str] = None,
        role: Optional[UserRole] = None,
        user_college_id_str: Optional[str] = None,
    ) -> dict:
        if app_id_str:
            try:
                app_uuid = uuid.UUID(str(app_id_str))
            except (ValueError, TypeError):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid application ID format.")

            app = db.query(ScholarshipApplication).filter(ScholarshipApplication.id == app_uuid).first()
            if not app:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scholarship application not found.")

            # Access control checks
            if role == UserRole.STUDENT and user_id_str:
                if app.student_id != uuid.UUID(str(user_id_str)):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: You do not own this application.",
                    )
            elif role == UserRole.ADMIN and user_college_id_str:
                if not app.student or app.student.college_id != uuid.UUID(str(user_college_id_str)):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Cross-college appointment access is prohibited.",
                    )

            appointment = (
                db.query(PhysicalVerificationAppointment)
                .filter(PhysicalVerificationAppointment.application_id == app_uuid)
                .order_by(PhysicalVerificationAppointment.created_at.desc())
                .first()
            )
            if not appointment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No physical verification appointment found for this application.",
                )
            return cls.format_appointment_response(appointment, app)

        # Student self-service lookup (/my-application/physical-verification)
        if role == UserRole.STUDENT and user_id_str:
            try:
                student_uuid = uuid.UUID(str(user_id_str))
            except (ValueError, TypeError):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid student ID format.")

            appointment = (
                db.query(PhysicalVerificationAppointment)
                .filter(PhysicalVerificationAppointment.student_id == student_uuid)
                .order_by(PhysicalVerificationAppointment.created_at.desc())
                .first()
            )
            if not appointment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No physical verification appointment found for your application.",
                )
            return cls.format_appointment_response(appointment, appointment.application)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application ID is required to retrieve appointment.",
        )

    # -------------------------------------------------------------------------
    # Helpers: Formatting Responses
    # -------------------------------------------------------------------------
    @staticmethod
    def format_appointment_response(
        appointment: PhysicalVerificationAppointment, app: Optional[ScholarshipApplication] = None
    ) -> dict:
        time_str = (
            appointment.scheduled_time.strftime("%H:%M")
            if isinstance(appointment.scheduled_time, time)
            else str(appointment.scheduled_time)
        )
        return {
            "id": str(appointment.id),
            "application_id": str(appointment.application_id),
            "application_number": app.application_number if app else None,
            "status": appointment.status.value if hasattr(appointment.status, "value") else str(appointment.status),
            "application_status": (
                app.status.value if app and hasattr(app.status, "value") else str(app.status) if app else None
            ),
            "scheduled_date": appointment.scheduled_date.isoformat() if appointment.scheduled_date else None,
            "scheduled_time": time_str,
            "venue": appointment.venue,
            "instructions": appointment.purpose,
            "notes": appointment.notes,
            "created_at": appointment.created_at.isoformat() if appointment.created_at else None,
            "updated_at": appointment.updated_at.isoformat() if appointment.updated_at else None,
        }

    @staticmethod
    def _format_admin_action_response(
        app: ScholarshipApplication,
        res: Optional[VerificationResult] = None,
        message: Optional[str] = None,
    ) -> dict:
        extracted = res.extracted_data if (res and res.extracted_data and isinstance(res.extracted_data, dict)) else {}
        risk_analysis = extracted.get("risk_analysis")
        correction_request = extracted.get("correction_request")
        review_history = extracted.get("review_history", [])

        return {
            "application_id": str(app.id),
            "application_number": app.application_number,
            "status": app.status.value if hasattr(app.status, "value") else str(app.status),
            "verification_status": (
                res.verification_status.value
                if (res and hasattr(res.verification_status, "value"))
                else (str(res.verification_status) if res else None)
            ),
            "overall_score": res.overall_score if res else None,
            "message": message,
            "issues": res.issues or [] if res else [],
            "risk_analysis": risk_analysis,
            "correction_request": correction_request,
            "review_history": review_history,
            "extracted_data": extracted,
            "verified_by_admin_id": str(res.verified_by_admin_id) if (res and res.verified_by_admin_id) else None,
            "reviewed_at": res.reviewed_at.isoformat() if (res and res.reviewed_at) else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
        }
