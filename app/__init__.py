"""
FastAPI Application Package
Main application entry point and configuration
"""

from app.main import create_application

__version__ = "1.0.0"
__all__ = ["create_application"]