"""
User Session Model
SQLAlchemy model for managing user sessions and refresh tokens
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class UserSession(Base):
    """User session model for multiple session support"""
    
    __tablename__ = "user_sessions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Session details
    refresh_token = Column(String(500), unique=True, nullable=False, index=True)
    access_token_jti = Column(String(255), nullable=False, index=True)  # JWT ID for access token
    
    # Device and browser information
    device_info = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # Support both IPv4 and IPv6
    location = Column(String(255), nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"
    
    @property
    def is_valid(self):
        """Check if session is valid and not expired"""
        from datetime import datetime, timezone
        return (
            self.is_active and
            not self.is_revoked and
            self.expires_at > datetime.now(timezone.utc)
        )
