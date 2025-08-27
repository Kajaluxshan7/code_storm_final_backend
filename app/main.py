"""
FastAPI Application Entry Point
EduCapture - Educational Note Enhancement Platform
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine
from app.core.events import startup_handler, shutdown_handler
from app.api import health, realtime, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events"""
    await startup_handler()
    yield
    await shutdown_handler()


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="EduCapture - Upload, enhance and organize your educational notes with AI-powered tools",
        version="1.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan
    )

    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers
    app.include_router(health.router, prefix=f"{settings.API_V1_STR}/health", tags=["health"])
    app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"])
    app.include_router(realtime.router, prefix=f"{settings.API_V1_STR}/realtime", tags=["realtime"])

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
