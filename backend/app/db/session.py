from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# SQLAlchemy engine with pool_pre_ping enabled for resilient connection handling
engine = create_engine(
    settings.sqlalchemy_database_url,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy database session per request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
