import os
import uuid
from pathlib import Path
from typing import Tuple
from fastapi import HTTPException, status

from app.core.config import settings


class DocumentStorageService:
    @staticmethod
    def validate_file_size(file_bytes: bytes) -> None:
        if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File exceeds the maximum allowed size of 2.5 MB."
            )

    @staticmethod
    def validate_file_type(original_filename: str, content_type: str, file_bytes: bytes) -> str:
        safe_name = Path(original_filename).name
        ext = Path(safe_name).suffix.lower()

        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension '{ext}'. Only PDF, JPG, JPEG, and PNG files are allowed."
            )

        if content_type.lower() not in settings.ALLOWED_MIME_TYPES and content_type != "application/octet-stream":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid MIME content-type '{content_type}'. Only PDF, JPG, JPEG, and PNG files are allowed."
            )

        signatures = settings.MAGIC_SIGNATURES.get(ext, [])
        valid_magic = any(file_bytes.startswith(sig) for sig in signatures)
        if not valid_magic:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file signature or corrupted file. The uploaded content does not match the file extension."
            )

        return ext

    @staticmethod
    def save_document_file(
        app_id_str: str,
        doc_type_str: str,
        original_filename: str,
        file_bytes: bytes,
        content_type: str
    ) -> Tuple[str, str, int]:
        DocumentStorageService.validate_file_size(file_bytes)
        ext = DocumentStorageService.validate_file_type(original_filename, content_type, file_bytes)

        # Sanitize original filename and strip any path traversal sequences
        safe_filename = Path(original_filename).name
        unique_filename = f"{uuid.uuid4().hex}_{safe_filename}"

        base_dir = Path(settings.DOCUMENT_STORAGE_PATH).resolve()
        target_dir = (base_dir / app_id_str / doc_type_str.lower()).resolve()
        target_path = (target_dir / unique_filename).resolve()

        # Path traversal security verification
        try:
            if not target_path.is_relative_to(base_dir):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid filename or path traversal detected."
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename or path traversal detected."
            )

        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            with open(target_path, "wb") as f:
                f.write(file_bytes)
        except Exception as e:
            # Partial file write cleanup
            if target_path.exists():
                try:
                    target_path.unlink()
                except OSError:
                    pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to write document file to storage."
            )

        # Generate relative storage path string (using forward slashes for cross-platform consistency)
        relative_path = Path(app_id_str) / doc_type_str.lower() / unique_filename
        relative_path_str = relative_path.as_posix()

        # Determine effective mime type
        mime_type = content_type
        if mime_type == "application/octet-stream":
            if ext == ".pdf":
                mime_type = "application/pdf"
            elif ext in (".jpg", ".jpeg"):
                mime_type = "image/jpeg"
            elif ext == ".png":
                mime_type = "image/png"

        return relative_path_str, mime_type, len(file_bytes)

    @staticmethod
    def delete_document_file(storage_path_str: str) -> None:
        if not storage_path_str:
            return

        base_dir = Path(settings.DOCUMENT_STORAGE_PATH).resolve()
        file_path = (base_dir / storage_path_str).resolve()

        try:
            if file_path.is_relative_to(base_dir) and file_path.exists() and file_path.is_file():
                file_path.unlink()
        except (ValueError, OSError):
            pass

    @staticmethod
    def get_document_file_path(storage_path_str: str) -> Path:
        if not storage_path_str:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No file storage reference recorded for this document."
            )

        base_dir = Path(settings.DOCUMENT_STORAGE_PATH).resolve()
        file_path = (base_dir / storage_path_str).resolve()

        try:
            if not file_path.is_relative_to(base_dir):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Invalid document file path."
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Invalid document file path."
            )

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical document file not found on storage server."
            )

        return file_path
