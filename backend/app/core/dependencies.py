import uuid
import jwt
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_access_token
from app.schemas.auth import TokenPayload
from app.db.models.enums import UserRole

# Reusable HTTP Bearer token extractor
security_scheme = HTTPBearer(auto_error=True)

def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> TokenPayload:
    """
    FastAPI dependency that extracts Bearer token, decodes JWT, and returns TokenPayload.
    Raises 401 Unauthorized if invalid or expired.
    """
    token = credentials.credentials
    try:
        payload_dict = decode_access_token(token)
        sub: Optional[str] = payload_dict.get("sub")
        role_str: Optional[str] = payload_dict.get("role")
        college_id_str: Optional[str] = payload_dict.get("college_id")
        exp: Optional[int] = payload_dict.get("exp")

        if not sub or not role_str or not college_id_str or exp is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials: Token payload missing required claims",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            college_uuid = uuid.UUID(college_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid college ID format in token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenPayload(
            sub=sub,
            role=UserRole(role_str),
            college_id=college_uuid,
            exp=exp,
            iat=payload_dict.get("iat")
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_admin_user(
    current_payload: TokenPayload = Depends(get_current_token_payload)
) -> TokenPayload:
    """
    Dependency that enforces current token user has ADMIN role.
    """
    if current_payload.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Admin privileges required"
        )
    return current_payload
