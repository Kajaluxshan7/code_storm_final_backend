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
    PROJECT_NAME: str = "Financial Statement Processor"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    
    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Database
    DATABASE_URL: Optional[str] = None
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "financial_app"
    
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
            db_name = values.get('DB_NAME', 'financial_app')
            
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
    ALLOWED_FILE_TYPES: List[str] = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg']
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    
settings = Settings()
