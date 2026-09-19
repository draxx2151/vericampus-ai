import uuid
import random
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.db.models.scholarship_application import ScholarshipApplication
from app.db.models.document import Document
from app.db.models.student import Student
from app.db.models.admin_officer import AdminOfficer
from app.db.models.enums import ApplicationStatus, DocumentType, UploadStatus, UserRole
from app.schemas.application import MAHADBT_SCHEMES
from app.services.document_storage_service import DocumentStorageService

class ApplicationService:
    @staticmethod
    def format_application_response(app: ScholarshipApplication) -> dict:
        doc_list = []
        for d in app.documents:
            doc_list.append({
                "id": str(d.id),
                "application_id": str(d.application_id),
                "document_type": d.document_type.value if hasattr(d.document_type, 'value') else str(d.document_type),
                "original_filename": d.original_filename,
                "mime_type": d.mime_type,
                "file_size": d.file_size,
                "upload_status": d.upload_status.value if hasattr(d.upload_status, 'value') else str(d.upload_status),
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None
            })

        return {
            "id": str(app.id),
            "student_id": str(app.student_id),
            "college_id": str(app.student.college_id) if app.student else None,
            "student_name": app.student.full_name if app.student else "Student",
            "application_number": app.application_number,
            "scholarship_name": app.scholarship_name,
            "status": app.status.value if hasattr(app.status, 'value') else str(app.status),
            "documents_uploaded_count": len(app.documents),
            "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
            "documents": doc_list
        }

    @staticmethod
    def create_or_get_application(db: Session, student_id_str: str, scholarship_name: str) -> dict:
        try:
            student_uuid = uuid.UUID(student_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid student ID format"
            )

        student = db.query(Student).filter(Student.id == student_uuid).first()
        if not student or not student.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found"
            )

        # 1. Check if student ALREADY has an application (Rule: ONE Student = ONE Application)
        existing_app = db.query(ScholarshipApplication).filter(
            ScholarshipApplication.student_id == student_uuid
        ).first()

        if existing_app:
            # Return existing application without creating another one
            return ApplicationService.format_application_response(existing_app)

        # 2. Validate scholarship scheme against authoritative list
        clean_scheme = scholarship_name.strip()
        if clean_scheme not in MAHADBT_SCHEMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scholarship scheme. Must be one of the official MahaDBT schemes."
            )

        # 3. Generate unique application number
        random_suffix = random.randint(1000, 9999)
        app_number = f"VC-2026-{random_suffix}"
        
        while db.query(ScholarshipApplication).filter(ScholarshipApplication.application_number == app_number).first():
            random_suffix = random.randint(1000, 9999)
            app_number = f"VC-2026-{random_suffix}"

        # 4. Create ScholarshipApplication (Status = DRAFT, Documents = 0 rows)
        new_app = ScholarshipApplication(
            id=uuid.uuid4(),
            student_id=student_uuid,
            scholarship_name=clean_scheme,
            application_number=app_number,
            status=ApplicationStatus.DRAFT
        )

        db.add(new_app)
        db.commit()
        db.refresh(new_app)

        return ApplicationService.format_application_response(new_app)

    @staticmethod
    def get_student_application(db: Session, student_id_str: str) -> Optional[dict]:
        try:
            student_uuid = uuid.UUID(student_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid student ID format"
            )

        app = db.query(ScholarshipApplication).filter(
            ScholarshipApplication.student_id == student_uuid
        ).first()

        if not app:
            return None

        return ApplicationService.format_application_response(app)

    @staticmethod
    def get_college_applications(db: Session, college_id_str: str) -> List[dict]:
        try:
            college_uuid = uuid.UUID(college_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid college ID format"
            )

        apps = db.query(ScholarshipApplication).join(Student).filter(
            Student.college_id == college_uuid
        ).all()

        return [ApplicationService.format_application_response(a) for a in apps]

    @staticmethod
    def get_application_by_id(
        db: Session,
        app_id_str: str,
        user_id_str: str,
        role: UserRole,
        user_college_id_str: str
    ) -> dict:
        try:
            app_uuid = uuid.UUID(app_id_str)
            user_uuid = uuid.UUID(user_id_str)
            college_uuid = uuid.UUID(user_college_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ID format"
            )

        app = db.query(ScholarshipApplication).filter(
            ScholarshipApplication.id == app_uuid
        ).first()

        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )

        # Cross-college tenant authorization check
        if role == UserRole.STUDENT:
            if app.student_id != user_uuid:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not authorized to view this application."
                )
        elif role == UserRole.ADMIN:
            if app.student.college_id != college_uuid:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Cross-college application access is prohibited."
                )

        return ApplicationService.format_application_response(app)

    @staticmethod
    def upload_or_replace_document(
        db: Session,
        app_id_str: str,
        student_id_str: str,
        document_type_input: str,
        original_filename: str,
        content_type: str,
        file_bytes: bytes
    ) -> dict:
        try:
            app_uuid = uuid.UUID(app_id_str)
            student_uuid = uuid.UUID(student_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ID format"
            )

        # 1. Validate Document Type against exact 4 allowed enum types
        valid_doc_types = [
            DocumentType.GOVERNMENT_ID,
            DocumentType.MARKSHEET,
            DocumentType.INCOME_CERTIFICATE,
            DocumentType.DOMICILE_CERTIFICATE
        ]

        target_enum = None
        for dt in valid_doc_types:
            if dt.value == document_type_input or dt.name == document_type_input:
                target_enum = dt
                break

        if not target_enum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document type. Accepted types: GOVERNMENT_ID, MARKSHEET, INCOME_CERTIFICATE, DOMICILE_CERTIFICATE"
            )

        # 2. Check application ownership
        app = db.query(ScholarshipApplication).filter(
            ScholarshipApplication.id == app_uuid
        ).first()

        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )

        if app.student_id != student_uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not own this application."
            )

        # 3. Check for existing document record for replacement tracking
        existing_doc = db.query(Document).filter(
            Document.application_id == app_uuid,
            Document.document_type == target_enum
        ).first()

        old_storage_path = existing_doc.storage_path if existing_doc else None

        # 4. STEP A: Save new physical file first using DocumentStorageService
        new_storage_path, mime_type, file_size = DocumentStorageService.save_document_file(
            app_id_str=str(app_uuid),
            doc_type_str=target_enum.value,
            original_filename=original_filename,
            file_bytes=file_bytes,
            content_type=content_type
        )

        # 5. STEP B: Update/Insert Document model in database
        if existing_doc:
            existing_doc.original_filename = original_filename
            existing_doc.storage_path = new_storage_path
            existing_doc.mime_type = mime_type
            existing_doc.file_size = file_size
            existing_doc.upload_status = UploadStatus.UPLOADED
            existing_doc.uploaded_at = func.now()
        else:
            new_doc = Document(
                id=uuid.uuid4(),
                application_id=app_uuid,
                document_type=target_enum,
                original_filename=original_filename,
                storage_path=new_storage_path,
                mime_type=mime_type,
                file_size=file_size,
                upload_status=UploadStatus.UPLOADED
            )
            db.add(new_doc)

        # 6. STEP C: Execute Database Transaction with Rollback Protection
        try:
            db.commit()
            db.refresh(app)
        except Exception as db_err:
            db.rollback()
            # Rollback: Delete newly written physical file so no orphaned file remains
            DocumentStorageService.delete_document_file(new_storage_path)
            # Preserve old physical file intact on disk
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database transaction failed while saving document metadata."
            )

        # 7. STEP D: Post-Commit Cleanup of Old File
        if old_storage_path and old_storage_path != new_storage_path:
            DocumentStorageService.delete_document_file(old_storage_path)

        return ApplicationService.format_application_response(app)

    @staticmethod
    def get_document_for_download(
        db: Session,
        app_id_str: str,
        doc_id_str: str,
        user_id_str: str,
        role: UserRole,
        user_college_id_str: str
    ):
        try:
            app_uuid = uuid.UUID(app_id_str)
            doc_uuid = uuid.UUID(doc_id_str)
            user_uuid = uuid.UUID(user_id_str)
            college_uuid = uuid.UUID(user_college_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ID format"
            )

        app = db.query(ScholarshipApplication).filter(
            ScholarshipApplication.id == app_uuid
        ).first()

        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )

        # Authorization checks
        if role == UserRole.STUDENT:
            if app.student_id != user_uuid:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You do not own this application document."
                )
        elif role == UserRole.ADMIN:
            if app.student.college_id != college_uuid:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Cross-college document access is prohibited."
                )

        doc = db.query(Document).filter(
            Document.id == doc_uuid,
            Document.application_id == app_uuid
        ).first()

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document record not found"
            )

        file_path = DocumentStorageService.get_document_file_path(doc.storage_path)
        mime_type = doc.mime_type or "application/octet-stream"
        
        return file_path, mime_type, doc.original_filename

