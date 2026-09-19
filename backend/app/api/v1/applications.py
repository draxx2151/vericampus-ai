from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_token_payload, require_admin_user
from app.db.models.enums import UserRole
from app.services.application_service import ApplicationService
from app.schemas.application import (
    MAHADBT_SCHEMES,
    ApplicationCreateRequest,
    DocumentUploadRequest,
    ApplicationResponse
)
from app.schemas.auth import TokenPayload

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
        filename=original_filename
    )

