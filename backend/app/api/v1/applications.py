from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_token_payload, require_admin_user
from app.db.models.enums import UserRole
from app.services.application_service import ApplicationService
from app.services.verification import VerificationService
from app.schemas.application import (
    MAHADBT_SCHEMES,
    ApplicationCreateRequest,
    DocumentUploadRequest,
    ApplicationResponse
)
from app.schemas.auth import TokenPayload
from app.services.admin_review_service import AdminReviewService
from app.schemas.admin_review import (
    ApproveApplicationRequest,
    RequestCorrectionRequest,
    SchedulePhysicalVerificationRequest,
    CompletePhysicalVerificationRequest,
    RejectApplicationRequest,
)

router = APIRouter(prefix="/applications", tags=["Scholarship Applications"])


@router.get(
    "/schemes",
    summary="Get Authoritative List of Official MahaDBT Schemes",
    description="Returns the single source of truth list of official 8 Maharashtra MahaDBT scholarship schemes."
)
def get_schemes():
    return {"schemes": MAHADBT_SCHEMES}


@router.post(
    "",
    summary="Create or Open Student Scholarship Application",
    description="Allows authenticated Student to create a new scholarship application. If an application already exists for the student, returns the existing application (1-application rule)."
)
def create_application(
    req: ApplicationCreateRequest,
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    if current_payload.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can create scholarship applications."
        )
    return ApplicationService.create_or_get_application(db, current_payload.sub, req.scholarship_name)


@router.get(
    "/my-application",
    summary="Get Authenticated Student Application",
    description="Fetches the current authenticated student's scholarship application. Returns null if no application has been started."
)
def get_my_application(
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    if current_payload.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access their personal application."
        )
    return ApplicationService.get_student_application(db, current_payload.sub)


@router.get(
    "/my-application/physical-verification",
    summary="Get Student Physical Verification Appointment",
    description="Retrieves the scheduled physical verification appointment for the current authenticated student."
)
def get_my_physical_verification_appointment(
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    if current_payload.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access their personal appointment via this endpoint."
        )
    return AdminReviewService.get_physical_verification_appointment(
        db=db,
        user_id_str=current_payload.sub,
        role=current_payload.role,
        user_college_id_str=str(current_payload.college_id) if current_payload.college_id else None
    )


@router.get(
    "",
    summary="List College Applications (Admin Only)",
    description="Returns all scholarship applications belonging strictly to the authenticated admin's college (tenant isolation)."
)
def list_college_applications(
    current_payload: TokenPayload = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    return ApplicationService.get_college_applications(db, str(current_payload.college_id))


@router.get(
    "/{application_id}",
    summary="Get Application Details by ID",
    description="Returns application details. Enforces authorization checks: student must own the application or admin must belong to the same college."
)
def get_application_by_id(
    application_id: str,
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    return ApplicationService.get_application_by_id(
        db,
        app_id_str=application_id,
        user_id_str=current_payload.sub,
        role=current_payload.role,
        user_college_id_str=str(current_payload.college_id)
    )


@router.post(
    "/{application_id}/documents",
    summary="Upload or Replace Core Verification Document",
    description="Uploads one of the 4 required core documents (GOVERNMENT_ID, MARKSHEET, INCOME_CERTIFICATE, DOMICILE_CERTIFICATE) as a multipart file."
)
async def upload_document(
    application_id: str,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    if current_payload.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can upload verification documents."
        )

    file_bytes = await file.read()
    filename = file.filename or f"{document_type.lower()}_document.pdf"
    content_type = file.content_type or "application/octet-stream"

    return ApplicationService.upload_or_replace_document(
        db=db,
        app_id_str=application_id,
        student_id_str=current_payload.sub,
        document_type_input=document_type,
        original_filename=filename,
        content_type=content_type,
        file_bytes=file_bytes
    )


@router.get(
    "/{application_id}/documents/{document_id}/file",
    summary="Download or View Authenticated Verification Document",
    description="Streams document binary file for authenticated student owner or college admin. Strictly prohibits unauthorized cross-student or cross-college access."
)
def download_document(
    application_id: str,
    document_id: str,
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    from fastapi.responses import FileResponse
    file_path, mime_type, original_filename = ApplicationService.get_document_for_download(
        db=db,
        app_id_str=application_id,
        doc_id_str=document_id,
        user_id_str=current_payload.sub,
        role=current_payload.role,
        user_college_id_str=str(current_payload.college_id)
    )
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=original_filename,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


@router.post(
    "/{application_id}/verify",
    summary="Trigger Automated Document Verification Pipeline",
    description="Initiates verification for the 4 required scholarship documents. Evaluates applicant identity, cross-document consistency, and scheme eligibility."
)
def verify_application(
    application_id: str,
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    return VerificationService.verify_application(
        db=db,
        app_id_str=application_id,
        user_id_str=current_payload.sub,
        role=current_payload.role,
        user_college_id_str=str(current_payload.college_id) if current_payload.college_id else None
    )


@router.get(
    "/{application_id}/verification-result",
    summary="Get Application Verification Result",
    description="Retrieves the persisted verification evaluation result for an application."
)
def get_verification_result(
    application_id: str,
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    return VerificationService.get_verification_result(
        db=db,
        app_id_str=application_id,
        user_id_str=current_payload.sub,
        role=current_payload.role,
        user_college_id_str=str(current_payload.college_id) if current_payload.college_id else None
    )


@router.get(
    "/{application_id}/authority-verification",
    summary="Get Application Authority Verification Result",
    description="Retrieves the Stage 5 authority verification result for an application. Enforces student ownership and college tenant isolation."
)
def get_authority_verification(
    application_id: str,
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    return VerificationService.get_authority_verification_result(
        db=db,
        app_id_str=application_id,
        user_id_str=current_payload.sub,
        role=current_payload.role,
        user_college_id_str=str(current_payload.college_id) if current_payload.college_id else None
    )


@router.get(
    "/{application_id}/evidence",
    summary="Get Application Evidence Summary",
    description="Retrieves the Stage 6 evidence & decision support summary for an application. Enforces student ownership and college tenant isolation."
)
def get_application_evidence(
    application_id: str,
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    return VerificationService.get_evidence_summary(
        db=db,
        app_id_str=application_id,
        user_id_str=current_payload.sub,
        role=current_payload.role,
        user_college_id_str=str(current_payload.college_id) if current_payload.college_id else None
    )


@router.get(
    "/{application_id}/review-history",
    summary="Get Application Review History Audit Trail",
    description="Retrieves the chronological administrative review audit history. Accessible by authorized student owner or same-college admin."
)
def get_application_review_history(
    application_id: str,
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    return AdminReviewService.get_review_history(
        db=db,
        app_id_str=application_id,
        user_id_str=current_payload.sub,
        role=current_payload.role,
        user_college_id_str=str(current_payload.college_id) if current_payload.college_id else None
    )


@router.get(
    "/{application_id}/physical-verification",
    summary="Get Application Physical Verification Appointment",
    description="Retrieves the physical verification appointment for an application. Accessible by authorized student owner or same-college admin."
)
def get_application_physical_verification(
    application_id: str,
    current_payload: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):
    return AdminReviewService.get_physical_verification_appointment(
        db=db,
        app_id_str=application_id,
        user_id_str=current_payload.sub,
        role=current_payload.role,
        user_college_id_str=str(current_payload.college_id) if current_payload.college_id else None
    )


@router.post(
    "/{application_id}/admin-review/approve",
    summary="Admin Review: Approve Scholarship Application",
    description="Allows authorized college admin to approve an application. Enforces tenant isolation, 4-document requirement, and human-in-the-loop decision."
)
def approve_application(
    application_id: str,
    req: Optional[ApproveApplicationRequest] = None,
    current_payload: TokenPayload = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    return AdminReviewService.approve_application(
        db=db,
        app_id_str=application_id,
        admin_id_str=current_payload.sub,
        admin_college_id_str=str(current_payload.college_id),
        remarks=req.remarks if req else None
    )


@router.post(
    "/{application_id}/admin-review/request-correction",
    summary="Admin Review: Request Document Correction",
    description="Allows authorized college admin to request correction of one or more documents with mandatory reason."
)
def request_document_correction(
    application_id: str,
    req: RequestCorrectionRequest,
    current_payload: TokenPayload = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    return AdminReviewService.request_document_correction(
        db=db,
        app_id_str=application_id,
        admin_id_str=current_payload.sub,
        admin_college_id_str=str(current_payload.college_id),
        document_types=req.document_types,
        reason=req.reason
    )


@router.post(
    "/{application_id}/admin-review/physical-verification",
    summary="Admin Review: Schedule Physical Verification Session",
    description="Allows authorized college admin to schedule a physical document verification appointment for an applicant."
)
def schedule_physical_verification(
    application_id: str,
    req: SchedulePhysicalVerificationRequest,
    current_payload: TokenPayload = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    return AdminReviewService.require_physical_verification(
        db=db,
        app_id_str=application_id,
        admin_id_str=current_payload.sub,
        admin_college_id_str=str(current_payload.college_id),
        scheduled_date=req.scheduled_date,
        scheduled_time=req.scheduled_time,
        venue=req.venue,
        instructions=req.instructions
    )


@router.post(
    "/{application_id}/admin-review/physical-verification/complete",
    summary="Admin Review: Record Physical Verification Outcome",
    description="Allows authorized college admin to record physical verification inspection result (VERIFIED or NOT_VERIFIED) and officer remarks."
)
def complete_physical_verification(
    application_id: str,
    req: CompletePhysicalVerificationRequest,
    current_payload: TokenPayload = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    return AdminReviewService.record_physical_verification_result(
        db=db,
        app_id_str=application_id,
        admin_id_str=current_payload.sub,
        admin_college_id_str=str(current_payload.college_id),
        result=req.result,
        remarks=req.remarks
    )


@router.post(
    "/{application_id}/admin-review/reject",
    summary="Admin Review: Reject Scholarship Application",
    description="Allows authorized college admin to reject a scholarship application with mandatory justification."
)
def reject_application(
    application_id: str,
    req: RejectApplicationRequest,
    current_payload: TokenPayload = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    return AdminReviewService.reject_application(
        db=db,
        app_id_str=application_id,
        admin_id_str=current_payload.sub,
        admin_college_id_str=str(current_payload.college_id),
        reason=req.reason
    )


