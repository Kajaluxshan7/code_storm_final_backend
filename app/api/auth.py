"""
Authentication API Routes
Endpoints for user authentication, registration, and session management
"""
import uuid
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User, AuthProvider
from app.models.session import UserSession
from app.schemas.auth import (
    UserRegisterRequest, 
    UserLoginRequest, 
    GoogleOAuthCompleteRequest,
    ResetPasswordRequest,
    ForgotPasswordRequest,
    ResendVerificationRequest,
    VerifyEmailRequest,
    UserResponse, 
    TokenResponse, 
    UserSessionResponse,
    SessionListResponse,
    MessageResponse,
    ErrorResponse
)
from app.services.auth import AuthService
from app.core.config import settings

from app.core.database import get_db
from app.core.auth import create_cookie_response_data
from app.core.dependencies import (
    CurrentUser, 
    CurrentActiveUser, 
    CurrentVerifiedUser,
    AuthServiceDep,
    get_refresh_token_from_cookie
)
from app.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    GoogleOAuthRequest,
    GoogleOAuthCompleteRequest,
    TokenResponse,
    UserResponse,
    UserProfileUpdateRequest,
    SessionListResponse,
    UserSessionResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ResendVerificationRequest,
    VerifyEmailRequest,
    MessageResponse,
    ErrorResponse
)
from app.services.google_oauth import google_oauth_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegisterRequest,
    request: Request,
    auth_service: AuthServiceDep
):
    """Register a new user with email verification"""

    user, verification_token = await auth_service.register_user(
        email=user_data.email,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        date_of_birth=user_data.date_of_birth,
        request=request
    )

    # Check if verification email was sent successfully
    # Note: This is a simplified check - in production you might want to
    # return this information in the response or check logs
    logger.info(f"User {user.email} registered successfully. Verification email sent.")

    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_data: UserLoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthServiceDep
):
    """Authenticate user and create session"""
    
    user, access_token, refresh_token, session = auth_service.login_user(
        email=user_data.email,
        password=user_data.password,
        request=request
    )
    
    # Set HTTP-only cookies
    cookie_data = create_cookie_response_data(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    # Set access token cookie
    response.set_cookie(
        key="access_token",
        value=cookie_data["access_token"]["value"],
        expires=cookie_data["access_token"]["expires"],
        httponly=cookie_data["access_token"]["httponly"],
        secure=cookie_data["access_token"]["secure"],
        samesite=cookie_data["access_token"]["samesite"],
        domain=cookie_data["access_token"]["domain"]
    )
    
    # Set refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=cookie_data["refresh_token"]["value"],
        expires=cookie_data["refresh_token"]["expires"],
        httponly=cookie_data["refresh_token"]["httponly"],
        secure=cookie_data["refresh_token"]["secure"],
        samesite=cookie_data["refresh_token"]["samesite"],
        domain=cookie_data["refresh_token"]["domain"]
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.get("/google/authorize")
async def google_authorize(state: Optional[str] = None):
    """Get Google OAuth authorization URL"""

    # Create a fresh instance to ensure settings are loaded correctly
    from app.services.google_oauth import GoogleOAuthService
    from app.core.config import settings

    logger.info(f"Google authorize endpoint called")
    logger.info(f"Settings GOOGLE_CLIENT_ID: {bool(settings.GOOGLE_CLIENT_ID)}")

    google_oauth_service = GoogleOAuthService()
    logger.info(f"Service client_id: {bool(google_oauth_service.client_id)}")

    auth_url = google_oauth_service.get_authorization_url(state=state)
    return {"auth_url": auth_url}


@router.get("/google/callback")
async def google_callback(
    code: str,
    request: Request,
    response: Response,
    auth_service: AuthServiceDep,
    state: Optional[str] = None
):
    """Handle Google OAuth callback"""

    try:
        # Create a fresh instance to ensure settings are loaded correctly
        from app.services.google_oauth import GoogleOAuthService
        google_oauth_service = GoogleOAuthService()

        # Complete OAuth flow and get user data
        user_data = await google_oauth_service.complete_oauth_flow(code)

        # Check if user exists
        existing_user = auth_service.db.query(User).filter(
            User.email == user_data["email"]
        ).first()

        if existing_user:
            # User exists - handle different auth provider scenarios
            if existing_user.auth_provider == AuthProvider.GOOGLE:
                # Existing Google user - check if profile is complete
                if (existing_user.first_name and 
                    existing_user.last_name and 
                    existing_user.date_of_birth and
                    existing_user.google_id):
                    # Complete Google user profile, log them in directly
                    user, access_token, refresh_token, session = await auth_service._google_login_existing_user(
                        user=existing_user,
                        request=request
                    )

                    # Set cookies and redirect to dashboard
                    cookie_data = create_cookie_response_data(
                        access_token=access_token,
                        refresh_token=refresh_token,
                        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
                    )

                    redirect_response = RedirectResponse(
                        url=f"{settings.FRONTEND_URL}/dashboard",
                        status_code=status.HTTP_302_FOUND
                    )

                    # Set cookies on redirect response
                    redirect_response.set_cookie(
                        key="access_token",
                        value=cookie_data["access_token"]["value"],
                        expires=cookie_data["access_token"]["expires"],
                        httponly=cookie_data["access_token"]["httponly"],
                        secure=cookie_data["access_token"]["secure"],
                        samesite=cookie_data["access_token"]["samesite"],
                        domain=cookie_data["access_token"]["domain"]
                    )

                    redirect_response.set_cookie(
                        key="refresh_token",
                        value=cookie_data["refresh_token"]["value"],
                        expires=cookie_data["refresh_token"]["expires"],
                        httponly=cookie_data["refresh_token"]["httponly"],
                        secure=cookie_data["refresh_token"]["secure"],
                        samesite=cookie_data["refresh_token"]["samesite"],
                        domain=cookie_data["refresh_token"]["domain"]
                    )

                    return redirect_response
                else:
                    # Incomplete Google user profile - need to complete it
                    from datetime import datetime, timedelta

                    temp_token_data = {
                        "google_id": user_data["google_id"],
                        "email": user_data["email"],
                        "first_name": user_data.get("first_name", ""),
                        "last_name": user_data.get("last_name", ""),
                        "profile_picture_url": user_data.get("profile_picture_url"),
                        "existing_user_id": str(existing_user.id),
                        "exp": datetime.utcnow() + timedelta(minutes=30)  # 30 minute expiry
                    }

                    temp_token = jwt.encode(
                        temp_token_data,
                        settings.SECRET_KEY,
                        algorithm=settings.ALGORITHM
                    )

                    redirect_url = f"{settings.FRONTEND_URL}/auth/complete-google?token={temp_token}"
                    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
            
            elif existing_user.auth_provider == AuthProvider.EMAIL:
                # User has email account, link with Google account
                # Update user to also support Google auth
                existing_user.google_id = user_data["google_id"]
                existing_user.profile_picture_url = user_data.get("profile_picture_url")
                # Update name if not set or if Google provides better data
                if not existing_user.first_name or existing_user.first_name == "Google":
                    existing_user.first_name = user_data.get("first_name", existing_user.first_name)
                if not existing_user.last_name or existing_user.last_name == "User":
                    existing_user.last_name = user_data.get("last_name", existing_user.last_name)
                
                auth_service.db.commit()
                auth_service.db.refresh(existing_user)
                
                # Log them in directly (they already have complete profile from email registration)
                user, access_token, refresh_token, session = await auth_service._google_login_existing_user(
                    user=existing_user,
                    request=request
                )

                # Set cookies and redirect to dashboard
                cookie_data = create_cookie_response_data(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
                )

                redirect_response = RedirectResponse(
                    url=f"{settings.FRONTEND_URL}/dashboard",
                    status_code=status.HTTP_302_FOUND
                )

                # Set cookies on redirect response
                redirect_response.set_cookie(
                    key="access_token",
                    value=cookie_data["access_token"]["value"],
                    expires=cookie_data["access_token"]["expires"],
                    httponly=cookie_data["access_token"]["httponly"],
                    secure=cookie_data["access_token"]["secure"],
                    samesite=cookie_data["access_token"]["samesite"],
                    domain=cookie_data["access_token"]["domain"]
                )

                redirect_response.set_cookie(
                    key="refresh_token",
                    value=cookie_data["refresh_token"]["value"],
                    expires=cookie_data["refresh_token"]["expires"],
                    httponly=cookie_data["refresh_token"]["httponly"],
                    secure=cookie_data["refresh_token"]["secure"],
                    samesite=cookie_data["refresh_token"]["samesite"],
                    domain=cookie_data["refresh_token"]["domain"]
                )

                return redirect_response
        else:
            # New user - redirect to complete registration
            # Create a temporary token with Google user data
            from datetime import datetime, timedelta

            temp_token_data = {
                "google_id": user_data["google_id"],
                "email": user_data["email"],
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "profile_picture_url": user_data.get("profile_picture_url"),
                "exp": datetime.utcnow() + timedelta(minutes=30)  # 30 minute expiry
            }

            temp_token = jwt.encode(
                temp_token_data,
                settings.SECRET_KEY,
                algorithm=settings.ALGORITHM
            )

            redirect_url = f"{settings.FRONTEND_URL}/auth/complete-google?token={temp_token}"
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    except Exception as e:
        logger.error(f"Google OAuth callback error: {str(e)}")
        error_url = f"{settings.FRONTEND_URL}/auth/login?error=oauth_failed"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)


@router.post("/google/complete", response_model=TokenResponse)
async def complete_google_registration(
    registration_data: GoogleOAuthCompleteRequest,
    request: Request,
    response: Response,
    auth_service: AuthServiceDep
):
    """Complete Google OAuth registration with date of birth"""

    try:
        # Decode the JWT token to get Google user data
        try:
            token_data = jwt.decode(
                registration_data.google_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token. Please try logging in again."
            )

        google_id = token_data.get("google_id")
        email = token_data.get("email")
        existing_user_id = token_data.get("existing_user_id")

        logger.info(f"Token data parsed: google_id={google_id}, email={email}, existing_user_id={existing_user_id}")

        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token data"
            )

        # Check if this is an existing user that needs profile completion
        if existing_user_id:
            # Update existing user's profile
            existing_user = auth_service.db.query(User).filter(User.id == existing_user_id).first()
            if not existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User not found"
                )

            # Update the user's profile with the provided data
            logger.info(f"Updating existing user {existing_user.id} with Google ID: {google_id}")
            existing_user.date_of_birth = registration_data.date_of_birth
            existing_user.google_id = google_id  # Link Google account
            existing_user.profile_picture_url = token_data.get("profile_picture_url")
            if registration_data.first_name:
                existing_user.first_name = registration_data.first_name
            if registration_data.last_name:
                existing_user.last_name = registration_data.last_name

            auth_service.db.commit()
            auth_service.db.refresh(existing_user)
            logger.info(f"User updated. New Google ID: {existing_user.google_id}")

            # Log the user in
            user, access_token, refresh_token, session = await auth_service._google_login_existing_user(
                user=existing_user,
                request=request
            )
        else:
            # New user registration
            user_data = {
                'google_id': google_id,
                'email': email,
                'first_name': registration_data.first_name or token_data.get("first_name", "Google"),
                'last_name': registration_data.last_name or token_data.get("last_name", "User"),
                'date_of_birth': registration_data.date_of_birth,
                'profile_picture_url': token_data.get("profile_picture_url")
            }

            # Complete the Google OAuth registration
            user, access_token, refresh_token, session = await auth_service.register_google_user(
                google_id=user_data['google_id'],
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                date_of_birth=user_data['date_of_birth'],
                profile_picture_url=user_data['profile_picture_url'],
                request=request
            )

        # Set HTTP-only cookies
        cookie_data = create_cookie_response_data(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

        # Set cookies
        response.set_cookie(
            key="access_token",
            value=cookie_data["access_token"]["value"],
            expires=cookie_data["access_token"]["expires"],
            httponly=cookie_data["access_token"]["httponly"],
            secure=cookie_data["access_token"]["secure"],
            samesite=cookie_data["access_token"]["samesite"],
            domain=cookie_data["access_token"]["domain"]
        )

        response.set_cookie(
            key="refresh_token",
            value=cookie_data["refresh_token"]["value"],
            expires=cookie_data["refresh_token"]["expires"],
            httponly=cookie_data["refresh_token"]["httponly"],
            secure=cookie_data["refresh_token"]["secure"],
            samesite=cookie_data["refresh_token"]["samesite"],
            domain=cookie_data["refresh_token"]["domain"]
        )

        return TokenResponse(
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth completion error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to complete Google registration: {str(e)}"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: Request,
    response: Response,
    auth_service: AuthServiceDep,
    refresh_token: str = Depends(get_refresh_token_from_cookie)
):
    """Refresh access token using refresh token"""
    
    new_access_token, new_refresh_token, session = auth_service.refresh_tokens(
        refresh_token=refresh_token,
        request=request
    )
    
    # Set new HTTP-only cookies
    cookie_data = create_cookie_response_data(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    # Update cookies
    response.set_cookie(
        key="access_token",
        value=cookie_data["access_token"]["value"],
        expires=cookie_data["access_token"]["expires"],
        httponly=cookie_data["access_token"]["httponly"],
        secure=cookie_data["access_token"]["secure"],
        samesite=cookie_data["access_token"]["samesite"],
        domain=cookie_data["access_token"]["domain"]
    )
    
    response.set_cookie(
        key="refresh_token",
        value=cookie_data["refresh_token"]["value"],
        expires=cookie_data["refresh_token"]["expires"],
        httponly=cookie_data["refresh_token"]["httponly"],
        secure=cookie_data["refresh_token"]["secure"],
        samesite=cookie_data["refresh_token"]["samesite"],
        domain=cookie_data["refresh_token"]["domain"]
    )
    
    user = auth_service.get_user_by_id(session.user_id)
    
    return TokenResponse(
        access_token=new_access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/logout", response_model=MessageResponse)
async def logout_user(
    response: Response,
    auth_service: AuthServiceDep,
    refresh_token: str = Depends(get_refresh_token_from_cookie)
):
    """Logout user from current session"""
    
    auth_service.logout_user(refresh_token)
    
    # Clear cookies
    response.delete_cookie(key="access_token", domain=settings.COOKIE_DOMAIN)
    response.delete_cookie(key="refresh_token", domain=settings.COOKIE_DOMAIN)
    
    return MessageResponse(message="Logout successful")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all_sessions(
    response: Response,
    current_user: CurrentUser,
    auth_service: AuthServiceDep
):
    """Logout user from all sessions"""
    
    revoked_count = auth_service.logout_all_sessions(current_user.id)
    
    # Clear cookies
    response.delete_cookie(key="access_token", domain=settings.COOKIE_DOMAIN)
    response.delete_cookie(key="refresh_token", domain=settings.COOKIE_DOMAIN)
    
    return MessageResponse(message=f"Logged out from {revoked_count} sessions")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    verification_data: VerifyEmailRequest,
    auth_service: AuthServiceDep
):
    """Verify user email with token"""
    
    user = await auth_service.verify_email(verification_data.token)
    
    return MessageResponse(message="Email verified successfully")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification_email(
    request_data: ResendVerificationRequest,
    auth_service: AuthServiceDep
):
    """Resend email verification"""
    
    await auth_service.resend_verification_email(request_data.email)
    
    return MessageResponse(message="Verification email sent")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """Get current user information"""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    profile_data: UserProfileUpdateRequest,
    current_user: CurrentVerifiedUser,
    db: Session = Depends(get_db)
):
    """Update user profile"""
    
    # Update fields if provided
    if profile_data.first_name is not None:
        current_user.first_name = profile_data.first_name
    if profile_data.last_name is not None:
        current_user.last_name = profile_data.last_name
    if profile_data.date_of_birth is not None:
        current_user.date_of_birth = profile_data.date_of_birth
    if profile_data.timezone is not None:
        current_user.timezone = profile_data.timezone
    if profile_data.language is not None:
        current_user.language = profile_data.language
    if profile_data.theme_preference is not None:
        current_user.theme_preference = profile_data.theme_preference
    
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    
    return UserResponse.model_validate(current_user)


@router.get("/sessions", response_model=SessionListResponse)
async def get_user_sessions(
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
    refresh_token: str = Depends(get_refresh_token_from_cookie)
):
    """Get user's active sessions"""
    
    sessions = auth_service.get_user_sessions(current_user.id)
    
    # Find current session
    current_session = None
    for session in sessions:
        if session.refresh_token == refresh_token:
            current_session = session
            break
    
    current_session_id = current_session.id if current_session else None
    
    return SessionListResponse(
        sessions=[UserSessionResponse.model_validate(session) for session in sessions],
        current_session_id=current_session_id
    )


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Revoke a specific session"""
    
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    session = db.query(UserSession).filter(
        UserSession.id == session_uuid,
        UserSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.is_active = False
    session.is_revoked = True
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    
    return MessageResponse(message="Session revoked successfully")
