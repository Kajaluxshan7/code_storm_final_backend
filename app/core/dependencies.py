"""
Authentication Dependencies
FastAPI dependencies for authentication and authorization
"""
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import uuid

from app.core.database import get_db
from app.core.auth import verify_token
from app.models import User, UserSession
from app.services.auth import AuthService

# Security scheme for OpenAPI documentation
security = HTTPBearer(auto_error=False)


def get_token_from_cookie_or_header(
    request: Request,
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token: Optional[str] = Cookie(None)
) -> Optional[str]:
    """Extract token from cookie or Authorization header"""
    
    # First try to get token from cookie (preferred method)
    if access_token:
        return access_token
    
    # Fall back to Authorization header
    if authorization:
        return authorization.credentials
    
    return None


def get_current_user(
    token: Optional[str] = Depends(get_token_from_cookie_or_header),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token
    payload = verify_token(token, token_type="access")
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user can still login (account status, etc.)
    if not user.can_login:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_optional_current_user(
    token: Optional[str] = Depends(get_token_from_cookie_or_header),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    
    if not token:
        return None
    
    try:
        return get_current_user(token, db)
    except HTTPException:
        return None


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (additional check for active status)"""
    
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return current_user


def get_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current verified user"""
    
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified"
        )
    
    return current_user


def get_refresh_token_from_cookie(
    refresh_token: Optional[str] = Cookie(None)
) -> str:
    """Get refresh token from cookie"""
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required"
        )
    
    return refresh_token


def get_current_session(
    token: str = Depends(get_token_from_cookie_or_header),
    refresh_token: str = Depends(get_refresh_token_from_cookie),
    db: Session = Depends(get_db)
) -> UserSession:
    """Get current user session"""
    
    # Find session by refresh token
    session = db.query(UserSession).filter(
        UserSession.refresh_token == refresh_token
    ).first()
    
    if not session or not session.is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )
    
    return session


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get authentication service instance"""
    return AuthService(db)


# Type annotations for easier use
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalCurrentUser = Annotated[Optional[User], Depends(get_optional_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentVerifiedUser = Annotated[User, Depends(get_verified_user)]
CurrentSession = Annotated[UserSession, Depends(get_current_session)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
