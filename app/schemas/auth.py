"""
Authentication Schemas
Pydantic models for API request/response validation
"""
from pydantic import BaseModel, EmailStr, ConfigDict, Field, validator
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID


# Base schemas
class BaseResponse(BaseModel):
    """Base response schema"""
    model_config = ConfigDict(from_attributes=True)


# User Registration
class UserRegisterRequest(BaseModel):
    """User registration request schema"""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    
    @validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


# User Login
class UserLoginRequest(BaseModel):
    """User login request schema"""
    email: EmailStr
    password: str


# Google OAuth
class GoogleOAuthRequest(BaseModel):
    """Google OAuth request schema"""
    code: str
    state: Optional[str] = None


class GoogleOAuthCompleteRequest(BaseModel):
    """Google OAuth complete registration request schema"""
    google_token: str
    date_of_birth: date
    first_name: Optional[str] = None
    last_name: Optional[str] = None


# Token schemas
class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


# User response schemas
class UserResponse(BaseResponse):
    """User response schema"""
    id: UUID
    email: str
    first_name: str
    last_name: str
    date_of_birth: date
    profile_picture_url: Optional[str] = None
    status: str
    is_email_verified: bool
    auth_provider: str
    theme_preference: str
    timezone: str
    language: str
    created_at: datetime
    last_login_at: Optional[datetime] = None
    login_count: int
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class UserProfileUpdateRequest(BaseModel):
    """User profile update request schema"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    theme_preference: Optional[str] = Field(None, pattern="^(light|dark|system)$")


# Session schemas
class UserSessionResponse(BaseResponse):
    """User session response schema"""
    id: UUID
    device_info: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime


class SessionListResponse(BaseResponse):
    """Session list response schema"""
    sessions: List[UserSessionResponse]
    current_session_id: UUID


# Password management
class ChangePasswordRequest(BaseModel):
    """Change password request schema"""
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request schema"""
    token: str
    new_password: str = Field(min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


# Email verification
class ResendVerificationRequest(BaseModel):
    """Resend verification email request schema"""
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    """Verify email request schema"""
    token: str


# Common response schemas
class MessageResponse(BaseModel):
    """Generic message response schema"""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response schema"""
    detail: str
    error_code: Optional[str] = None
    success: bool = False
