"""
Application Configuration
Environment-based settings using Pydantic Settings
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import model_validator, ConfigDict
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file"""
    
    # Configuration
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )
    
    # Application
    PROJECT_NAME: str = "EduCapture"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    
    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Database
    DATABASE_URL: Optional[str] = None
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "educapture_db"
    
    @model_validator(mode='before')
    @classmethod
    def assemble_db_connection(cls, values):
        # If DATABASE_URL is already provided, use it
        if isinstance(values, dict) and values.get('DATABASE_URL'):
            return values
            
        if isinstance(values, dict):
            # Construct database URL from individual components
            user = values.get('DB_USER', 'postgres')
            password = values.get('DB_PASSWORD', '')
            host = values.get('DB_HOST', 'localhost')
            port = values.get('DB_PORT', 5432)
            db_name = values.get('DB_NAME', 'educapture_db')
            
            values['DATABASE_URL'] = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
        
        return values
    
    # S3 Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = None
    S3_ENDPOINT_URL: Optional[str] = None  # For MinIO or custom S3-compatible storage
    
    # File Storage Configuration
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20MB in bytes
    ALLOWED_FILE_TYPES: List[str] = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.pdf']
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production-educapture-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    
    # Email Configuration
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[str] = None
    MAIL_PORT: int = 587
    MAIL_SERVER: Optional[str] = None
    MAIL_FROM_NAME: str = "EduCapture"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    
    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Cookie Settings
    COOKIE_DOMAIN: Optional[str] = None
    COOKIE_SECURE: bool = False  # Set to True in production with HTTPS
    COOKIE_SAMESITE: str = "lax"
    
    # AI Service Configuration
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_CLOUD_PROJECT_ID: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None  # Path to service account JSON
    
    # AI Processing Settings
    MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 10MB for AI processing
    SUPPORTED_IMAGE_FORMATS: List[str] = ["JPEG", "PNG", "WEBP", "BMP", "TIFF"]
    QUALITY_THRESHOLD: float = 0.6  # Minimum quality score for processing
    
    # Text Extraction Settings
    OCR_CONFIDENCE_THRESHOLD: float = 0.5
    MIN_TEXT_LENGTH: int = 10  # Minimum characters for meaningful text
    
    # Quiz Generation Settings
    DEFAULT_QUIZ_QUESTIONS: int = 5
    MAX_QUIZ_QUESTIONS: int = 20
    
    # Rate Limiting
    AI_REQUESTS_PER_MINUTE: int = 60
    AI_REQUESTS_PER_HOUR: int = 1000


settings = Settings()