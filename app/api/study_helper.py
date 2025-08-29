"""
Study Helper API Routes
FastAPI routes for AI-powered study assistance
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.study_helper import get_study_helper_service
from app.agent.schemas import StudySessionResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/study", tags=["Study Helper"])


@router.post("/upload-enhanced", response_model=StudySessionResponse)
async def upload_enhanced_study_image(
    file: UploadFile = File(..., description="Image file to process"),
    generate_summary: bool = Form(True, description="Generate summary"),
    generate_explanation: bool = Form(True, description="Generate explanation"),
    generate_quiz: bool = Form(True, description="Generate quiz questions"),
    quiz_question_count: int = Form(5, ge=1, le=20, description="Number of quiz questions"),
    quiz_difficulty: Optional[str] = Form(None, description="Quiz difficulty (easy/medium/hard)"),
    explanation_level: Optional[str] = Form(None, description="Explanation level (beginner/intermediate/advanced)"),
    enable_chunking: bool = Form(False, description="Enable chunked processing for large documents"),
    chunk_size: int = Form(4000, ge=1000, le=8000, description="Size of each chunk in characters"),
    max_concurrency: int = Form(3, ge=1, le=5, description="Maximum concurrent chunk processing"),
    preserve_equations: bool = Form(True, description="Preserve mathematical content"),
    preprocessing: bool = Form(True, description="Enable text preprocessing"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Enhanced upload endpoint with chunked processing support
    
    This endpoint supports advanced processing options including:
    - Chunked processing for large documents
    - Mathematical content preservation
    - Parallel processing with rate limiting
    - Enhanced text preprocessing
    """
    try:
        study_service = get_study_helper_service(db)
        
        result = await study_service.process_enhanced_study_image(
            image_file=file,
            user=current_user,
            generate_summary=generate_summary,
            generate_explanation=generate_explanation,
            generate_quiz=generate_quiz,
            quiz_question_count=quiz_question_count,
            quiz_difficulty=quiz_difficulty,
            explanation_level=explanation_level,
            enable_chunking=enable_chunking,
            chunk_size=chunk_size,
            max_concurrency=max_concurrency,
            preserve_equations=preserve_equations,
            preprocessing=preprocessing
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced study image upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process enhanced study image"
        )


@router.post("/estimate-processing")
async def estimate_processing_requirements(
    file: UploadFile = File(..., description="Image file to analyze"),
    chunk_size: int = Form(4000, ge=1000, le=8000, description="Proposed chunk size"),
    max_concurrency: int = Form(3, ge=1, le=5, description="Proposed concurrency"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Estimate processing requirements for a document
    
    Analyzes the uploaded file and provides estimates for:
    - Processing time
    - Number of chunks required
    - Complexity assessment
    - Recommendations for optimal settings
    """
    try:
        study_service = get_study_helper_service(db)
        
        estimate = await study_service.estimate_processing_requirements(
            image_file=file,
            chunk_size=chunk_size,
            max_concurrency=max_concurrency
        )
        
        return estimate
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing estimation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to estimate processing requirements"
        )


@router.post("/upload", response_model=StudySessionResponse)
async def upload_study_image(
    file: UploadFile = File(..., description="Image file to process"),
    generate_summary: bool = Form(True, description="Generate summary"),
    generate_explanation: bool = Form(True, description="Generate explanation"),
    generate_quiz: bool = Form(True, description="Generate quiz questions"),
    quiz_question_count: int = Form(5, ge=1, le=20, description="Number of quiz questions"),
    quiz_difficulty: Optional[str] = Form(None, description="Quiz difficulty (easy/medium/hard)"),
    explanation_level: Optional[str] = Form(None, description="Explanation level (beginner/intermediate/advanced)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and process an educational image
    
    This endpoint processes uploaded images (handwritten notes, textbook pages, diagrams)
    and generates educational content including summaries, explanations, and quiz questions.
    
    **Supported Image Formats:**
    - JPEG, PNG, WEBP, BMP, TIFF
    - Maximum file size: 20MB
    
    **Processing Features:**
    - Automatic quality assessment
    - Content type classification
    - Intelligent text extraction
    - AI-generated summaries
    - Detailed explanations
    - Custom quiz generation
    
    **Usage Examples:**
    - Upload handwritten class notes for summary generation
    - Process textbook pages for quiz questions
    - Extract content from diagrams with explanations
    """
    try:
        study_service = get_study_helper_service(db)
        
        result = await study_service.process_study_image(
            image_file=file,
            user=current_user,
            generate_summary=generate_summary,
            generate_explanation=generate_explanation,
            generate_quiz=generate_quiz,
            quiz_question_count=quiz_question_count,
            quiz_difficulty=quiz_difficulty,
            explanation_level=explanation_level
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Study image upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process study image"
        )


@router.get("/session/{session_id}", response_model=StudySessionResponse)
async def get_study_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific study session by ID
    
    Retrieve the results of a previously processed study session.
    """
    try:
        study_service = get_study_helper_service(db)
        session = await study_service.get_study_session(session_id, current_user)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Study session not found"
            )
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get study session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve study session"
        )


@router.get("/sessions")
async def list_study_sessions(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List user's study sessions
    
    Get a list of the user's recent study sessions with basic information.
    """
    try:
        study_service = get_study_helper_service(db)
        sessions = await study_service.list_user_sessions(current_user, limit)
        
        return {
            "sessions": sessions,
            "total": len(sessions),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Failed to list study sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve study sessions"
        )


@router.delete("/session/{session_id}")
async def delete_study_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a study session
    
    Remove a study session and its associated files.
    """
    try:
        study_service = get_study_helper_service(db)
        deleted = await study_service.delete_study_session(session_id, current_user)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Study session not found"
            )
        
        return {"message": "Study session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete study session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete study session"
        )


@router.get("/health")
async def study_helper_health():
    """
    Check study helper service health
    
    Verify that AI services and dependencies are available.
    """
    try:
        health_status = {
            "status": "healthy",
            "services": {},
            "timestamp": "2024-01-01T00:00:00Z"  # You'd use real timestamp
        }
        
        # Check Gemini API availability
        health_status["services"]["gemini_api"] = {
            "available": bool(settings.GEMINI_API_KEY),
            "configured": bool(settings.GEMINI_API_KEY)
        }
        
        # Check Google Vision API availability
        health_status["services"]["google_vision"] = {
            "available": bool(settings.GOOGLE_APPLICATION_CREDENTIALS),
            "configured": bool(settings.GOOGLE_APPLICATION_CREDENTIALS)
        }
        
        # Check upload directory
        import os
        upload_dir = "uploads/study_images"
        health_status["services"]["file_storage"] = {
            "available": os.path.exists(upload_dir),
            "writable": os.access(upload_dir, os.W_OK) if os.path.exists(upload_dir) else False
        }
        
        # Determine overall status
        if not any(service["available"] for service in health_status["services"].values()):
            health_status["status"] = "unhealthy"
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=health_status
            )
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )


@router.get("/config")
async def get_study_helper_config(
    current_user: User = Depends(get_current_user)
):
    """
    Get study helper configuration
    
    Return configuration settings for the frontend.
    """
    return {
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
        "allowed_file_types": settings.ALLOWED_FILE_TYPES,
        "supported_image_formats": settings.SUPPORTED_IMAGE_FORMATS,
        "default_quiz_questions": settings.DEFAULT_QUIZ_QUESTIONS,
        "max_quiz_questions": settings.MAX_QUIZ_QUESTIONS,
        "quality_threshold": settings.QUALITY_THRESHOLD,
        "min_text_length": settings.MIN_TEXT_LENGTH,
        "features": {
            "summary_generation": True,
            "explanation_generation": True,
            "quiz_generation": True,
            "quality_assessment": True,
            "content_classification": True,
            "image_preprocessing": True
        }
    }


@router.post("/test")
async def test_ai_services(
    current_user: User = Depends(get_current_user)
):
    """
    Test AI services connectivity
    
    Perform basic connectivity tests for AI services.
    Development/admin endpoint.
    """
    try:
        test_results = {
            "timestamp": "2024-01-01T00:00:00Z",
            "tests": {}
        }
        
        # Test Gemini API
        try:
            if settings.GEMINI_API_KEY:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-2.5-flash-lite')
                response = model.generate_content("Test: respond with 'OK'")
                test_results["tests"]["gemini"] = {
                    "status": "pass",
                    "response_length": len(response.text) if response.text else 0
                }
            else:
                test_results["tests"]["gemini"] = {
                    "status": "skip",
                    "reason": "API key not configured"
                }
        except Exception as e:
            test_results["tests"]["gemini"] = {
                "status": "fail",
                "error": str(e)
            }
        
        # Test Google Vision API
        try:
            if settings.GOOGLE_APPLICATION_CREDENTIALS:
                from google.cloud import vision
                client = vision.ImageAnnotatorClient()
                test_results["tests"]["google_vision"] = {
                    "status": "pass",
                    "client_initialized": True
                }
            else:
                test_results["tests"]["google_vision"] = {
                    "status": "skip",
                    "reason": "Credentials not configured"
                }
        except Exception as e:
            test_results["tests"]["google_vision"] = {
                "status": "fail",
                "error": str(e)
            }
        
        return test_results
        
    except Exception as e:
        logger.error(f"AI services test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test AI services"
        )
