"""
Authentication Service
Business logic for user authentication, registration, and session management
"""
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta, timezone, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status, Request
import uuid
import logging

from app.models import User, UserSession, UserStatus, AuthProvider
from app.core.auth import (
    hash_password, 
    verify_password, 
    create_access_token, 
    create_refresh_token,
    generate_email_verification_token,
    generate_password_reset_token,
    extract_token_jti
)
from app.services.email import get_email_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for handling user authentication operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def register_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        date_of_birth: date,
        request: Request
    ) -> Tuple[User, str]:
        """Register a new user with email verification"""
        
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Generate verification token
        verification_token = generate_email_verification_token()
        verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        
        # Create new user
        user = User(
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            auth_provider=AuthProvider.EMAIL,
            status=UserStatus.PENDING_EMAIL_VERIFICATION,
            email_verification_token=verification_token,
            email_verification_expires_at=verification_expires,
            is_email_verified=False
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Send verification email
        email_service = get_email_service()
        logger.info(f"Attempting to send verification email to {email}...")
        email_sent = await email_service.send_email_verification(
            email=email,
            first_name=first_name,
            verification_token=verification_token
        )

        if email_sent:
            logger.info(f"Verification email sent successfully to {email}")
        else:
            logger.error(f"Failed to send verification email to {email} - email service returned False")
            # In production, you might want to:
            # 1. Store this failure for retry
            # 2. Send a notification to admins
            # 3. Provide alternative verification methods to the user

        logger.info(f"User registered successfully: {email}")
        return user, verification_token
    
    def login_user(
        self,
        email: str,
        password: str,
        request: Request
    ) -> Tuple[User, str, str, UserSession]:
        """Authenticate user and create session"""
        
        # Find user by email
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password for email auth users
        if user.auth_provider == AuthProvider.EMAIL:
            if not user.password_hash or not verify_password(password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
        
        # Check if user can login
        if not user.can_login:
            if not user.is_email_verified:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email not verified. Please check your email for verification link."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is not active. Please contact support."
                )
        
        # Create tokens
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        # Extract access token JTI
        access_token_jti = extract_token_jti(access_token)
        
        # Create session
        session = self._create_user_session(
            user=user,
            refresh_token=refresh_token,
            access_token_jti=access_token_jti,
            request=request
        )
        
        # Update user login info
        user.last_login_at = datetime.now(timezone.utc)
        user.login_count += 1
        self.db.commit()
        
        logger.info(f"User logged in successfully: {email}")
        return user, access_token, refresh_token, session
    
    async def register_google_user(
        self,
        google_id: str,
        email: str,
        first_name: str,
        last_name: str,
        date_of_birth: date,
        profile_picture_url: Optional[str],
        request: Request
    ) -> Tuple[User, str, str, UserSession]:
        """Register a new user via Google OAuth"""
        
        # Check if user already exists with this email
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            if existing_user.auth_provider == AuthProvider.GOOGLE:
                # User exists with Google auth, just login
                return await self._google_login_existing_user(existing_user, request)
            elif existing_user.auth_provider == AuthProvider.EMAIL:
                # Link Google account to existing email account
                existing_user.google_id = google_id
                existing_user.profile_picture_url = profile_picture_url
                # Update name if Google provides better data
                if not existing_user.first_name or existing_user.first_name in ["Google", ""]:
                    existing_user.first_name = first_name
                if not existing_user.last_name or existing_user.last_name in ["User", ""]:
                    existing_user.last_name = last_name
                
                self.db.commit()
                self.db.refresh(existing_user)
                return await self._google_login_existing_user(existing_user, request)
        
        # Create new Google user
        user = User(
            email=email,
            google_id=google_id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            profile_picture_url=profile_picture_url,
            auth_provider=AuthProvider.GOOGLE,
            status=UserStatus.ACTIVE,  # Google users are pre-verified
            is_email_verified=True  # Google provides verified emails
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Create tokens and session
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        access_token_jti = extract_token_jti(access_token)
        session = self._create_user_session(
            user=user,
            refresh_token=refresh_token,
            access_token_jti=access_token_jti,
            request=request
        )
        
        # Update login info
        user.last_login_at = datetime.now(timezone.utc)
        user.login_count += 1
        self.db.commit()
        
        logger.info(f"Google user registered successfully: {email}")
        return user, access_token, refresh_token, session
        self.db.commit()
        
        # Send welcome email
        email_service = get_email_service()
        await email_service.send_welcome_email(
            email=email,
            first_name=first_name,
            auth_provider="google"
        )
        
        logger.info(f"Google user registered successfully: {email}")
        return user, access_token, refresh_token, session
    
    async def _google_login_existing_user(
        self,
        user: User,
        request: Request
    ) -> Tuple[User, str, str, UserSession]:
        """Login existing Google user"""
        
        if not user.can_login:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is not active. Please contact support."
            )
        
        # Create tokens and session
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        access_token_jti = extract_token_jti(access_token)
        session = self._create_user_session(
            user=user,
            refresh_token=refresh_token,
            access_token_jti=access_token_jti,
            request=request
        )
        
        # Update login info
        user.last_login_at = datetime.now(timezone.utc)
        user.login_count += 1
        self.db.commit()
        
        logger.info(f"Existing Google user logged in: {user.email}")
        return user, access_token, refresh_token, session
    
    def _create_user_session(
        self,
        user: User,
        refresh_token: str,
        access_token_jti: str,
        request: Request
    ) -> UserSession:
        """Create a new user session"""
        
        # Extract device info from request
        user_agent = request.headers.get("user-agent", "")
        ip_address = request.client.host if request.client else ""
        
        # Create session
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        session = UserSession(
            user_id=user.id,
            refresh_token=refresh_token,
            access_token_jti=access_token_jti,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def refresh_tokens(
        self,
        refresh_token: str,
        request: Request
    ) -> Tuple[str, str, UserSession]:
        """Refresh access token using refresh token"""
        
        # Find session by refresh token
        session = self.db.query(UserSession).filter(
            UserSession.refresh_token == refresh_token
        ).first()
        
        if not session or not session.is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Get user
        user = self.db.query(User).filter(User.id == session.user_id).first()
        if not user or not user.can_login:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is not active"
            )
        
        # Create new tokens
        new_access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        new_refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        # Update session
        session.refresh_token = new_refresh_token
        session.access_token_jti = extract_token_jti(new_access_token)
        session.last_used_at = datetime.now(timezone.utc)
        session.expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        self.db.commit()
        
        logger.info(f"Tokens refreshed for user: {user.email}")
        return new_access_token, new_refresh_token, session
    
    def logout_user(self, refresh_token: str) -> bool:
        """Logout user by invalidating session"""
        
        session = self.db.query(UserSession).filter(
            UserSession.refresh_token == refresh_token
        ).first()
        
        if session:
            session.is_active = False
            session.is_revoked = True
            session.revoked_at = datetime.now(timezone.utc)
            self.db.commit()
            
            logger.info(f"User session revoked: {session.user_id}")
            return True
        
        return False
    
    def logout_all_sessions(self, user_id: uuid.UUID) -> int:
        """Logout user from all sessions"""
        
        sessions = self.db.query(UserSession).filter(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.is_revoked == False
            )
        ).all()
        
        revoked_count = 0
        for session in sessions:
            session.is_active = False
            session.is_revoked = True
            session.revoked_at = datetime.now(timezone.utc)
            revoked_count += 1
        
        self.db.commit()
        
        logger.info(f"All sessions revoked for user: {user_id}, count: {revoked_count}")
        return revoked_count
    
    async def verify_email(self, token: str) -> User:
        """Verify user email with token"""
        
        user = self.db.query(User).filter(
            and_(
                User.email_verification_token == token,
                User.email_verification_expires_at > datetime.now(timezone.utc),
                User.is_email_verified == False
            )
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
        # Update user
        user.is_email_verified = True
        user.status = UserStatus.ACTIVE
        user.email_verification_token = None
        user.email_verification_expires_at = None
        
        self.db.commit()
        
        # Send welcome email
        email_service = get_email_service()
        await email_service.send_welcome_email(
            email=user.email,
            first_name=user.first_name
        )
        
        logger.info(f"Email verified for user: {user.email}")
        return user
    
    async def resend_verification_email(self, email: str) -> bool:
        """Resend verification email"""
        
        user = self.db.query(User).filter(
            and_(
                User.email == email,
                User.is_email_verified == False
            )
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found or already verified"
            )
        
        # Generate new verification token
        verification_token = generate_email_verification_token()
        verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        
        user.email_verification_token = verification_token
        user.email_verification_expires_at = verification_expires
        
        self.db.commit()
        
        # Send verification email
        email_service = get_email_service()
        await email_service.send_email_verification(
            email=email,
            first_name=user.first_name,
            verification_token=verification_token
        )
        
        logger.info(f"Verification email resent to: {email}")
        return True
    
    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_sessions(self, user_id: uuid.UUID) -> list[UserSession]:
        """Get all active sessions for user"""
        return self.db.query(UserSession).filter(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.is_revoked == False
            )
        ).order_by(UserSession.last_used_at.desc()).all()
