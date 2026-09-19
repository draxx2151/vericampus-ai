from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "VeriCampus AI Backend"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Database Settings
    DATABASE_URL: str = "postgresql+psycopg://postgres:password@localhost:5432/vericampus"

    # Security & JWT Settings
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production-vericampus-ai-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours default

    # File Upload & Storage Settings
    DOCUMENT_STORAGE_PATH: str = "storage/applications"
    MAX_UPLOAD_SIZE_BYTES: int = 2_621_440  # Exactly 2.5 MiB (2,621,440 bytes)
    ALLOWED_EXTENSIONS: set = {".pdf", ".jpg", ".jpeg", ".png"}
    ALLOWED_MIME_TYPES: set = {
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png"
    }
    MAGIC_SIGNATURES: dict = {
        ".pdf": [b"%PDF-"],
        ".jpg": [b"\xff\xd8\xff"],
        ".jpeg": [b"\xff\xd8\xff"],
        ".png": [b"\x89PNG\r\n\x1a\n"]
    }

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        """
        Returns DATABASE_URL with password safely percent-encoded if special characters (like '@') are present.
        """
        url = self.DATABASE_URL
        if "://" in url:
            scheme, rest = url.split("://", 1)
            if "@" in rest:
                last_at_idx = rest.rfind("@")
                user_pass = rest[:last_at_idx]
                host_db = rest[last_at_idx + 1:]
                if ":" in user_pass:
                    user, pwd = user_pass.split(":", 1)
                    quoted_pwd = quote_plus(pwd)
                    return f"{scheme}://{user}:{quoted_pwd}@{host_db}"
        return url

settings = Settings()
