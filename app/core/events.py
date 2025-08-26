"""
Application Events
Startup and shutdown event handlers
"""
import logging
from app.core.database import create_tables
from app.core.config import settings

logger = logging.getLogger(__name__)


async def startup_handler() -> None:
    """
    Handle application startup
    """
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # Create database tables if they don't exist
    # Note: In production, use Alembic migrations instead
    if settings.DEBUG:
        create_tables()
        logger.info("Database tables created")
    
    logger.info("Application startup complete")


async def shutdown_handler() -> None:
    """
    Handle application shutdown
    """
    logger.info("Shutting down application...")
    logger.info("Application shutdown complete")
