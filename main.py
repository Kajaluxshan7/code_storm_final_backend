"""
EduCapture Backend Application Entry Point
"""
from app.main import create_application

app = create_application()

if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
