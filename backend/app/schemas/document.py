import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.db.models.enums import DocumentType, UploadStatus

class DocumentBase(BaseModel):
    document_type: DocumentType
    original_filename: str
    storage_path: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    upload_status: UploadStatus = UploadStatus.UPLOADED


class DocumentCreate(DocumentBase):
    application_id: uuid.UUID


class DocumentResponse(DocumentBase):
    id: uuid.UUID
    application_id: uuid.UUID
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
