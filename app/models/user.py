"""
User Model
SQLAlchemy model for user authentication and profile management
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base


class UserStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_EMAIL_VERIFICATION = "pending_email_verification"


class AuthProvider(str, enum.Enum):
    """Authentication provider types"""
    EMAIL = "email"
    GOOGLE = "google"


class User(Base):
    """User model for authentication and profile management"""
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Authentication fields
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    auth_provider = Column(Enum(AuthProvider), default=AuthProvider.EMAIL, nullable=False)
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    
    # Profile fields
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)  # Required field as per requirements
    profile_picture_url = Column(String(500), nullable=True)
    
    # Account status and verification
    status = Column(Enum(UserStatus), default=UserStatus.PENDING_EMAIL_VERIFICATION, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Password reset fields
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Session management
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Privacy and preferences
    timezone = Column(String(50), default="UTC", nullable=False)
    language = Column(String(10), default="en", nullable=False)
    theme_preference = Column(String(20), default="system", nullable=False)  # light, dark, system
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, status={self.status})>"
    
    @property
    def full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_oauth_user(self):
        """Check if user registered via OAuth"""
        return self.auth_provider != AuthProvider.EMAIL
    
    @property
    def can_login(self):
        """Check if user can login"""
        return (
            self.status in [UserStatus.ACTIVE] and
            self.is_active and
            self.is_email_verified
        )
