"""
Health Check API
System health and status endpoints
"""
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check for container orchestration"""
    # Add database connectivity check here
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """Liveness check for container orchestration"""
    return {"status": "alive"}
