"""
AI Study Helper Service
Service layer for handling AI-powered study assistance
"""
import asyncio
import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
import shutil

from app.agent.workflow import get_workflow
from app.services.enhanced_document_processor import EnhancedDocumentProcessor, preprocess_text_for_math
from app.agent.schemas import (
    ImageProcessingState,
    StudySessionRequest,
    StudySessionResponse,
    ProcessingResult,
    QualityAssessmentResult,
    ContentTypeResult,
    TextExtractionResult,
    SummaryResult,
    ExplanationResult,
    QuizResult,
    QuizQuestion,
    ProcessingTool
)
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


class StudyHelperService:
    """Service for AI-powered study assistance"""
    
    def __init__(self, db: Session):
        self.db = db
        self.workflow = get_workflow()
        self.enhanced_processor = EnhancedDocumentProcessor(self.workflow)
        self.upload_dir = "uploads/study_images"
        self._ensure_upload_directory()
    
    def _ensure_upload_directory(self):
        """Ensure upload directory exists"""
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def process_study_image(
        self,
        image_file: UploadFile,
        user: User,
        generate_summary: bool = True,
        generate_explanation: bool = True,
        generate_quiz: bool = True,
        quiz_question_count: int = 5,
        quiz_difficulty: Optional[str] = None,
        explanation_level: Optional[str] = None
    ) -> StudySessionResponse:
        """
        Process an uploaded image for study assistance
        
        Args:
            image_file: Uploaded image file
            user: Authenticated user
            generate_summary: Whether to generate summary
            generate_explanation: Whether to generate explanation
            generate_quiz: Whether to generate quiz questions
            quiz_question_count: Number of quiz questions to generate
            quiz_difficulty: Preferred quiz difficulty
            explanation_level: Preferred explanation complexity level
            
        Returns:
            StudySessionResponse with processing results
        """
        session_id = str(uuid.uuid4())
        
        try:
            # Validate file
            await self._validate_upload_file(image_file)
            
            # Save uploaded file
            file_path = await self._save_uploaded_file(image_file, session_id)
            
            # Process image through workflow
            processing_state = await self.workflow.process_image(
                image_path=file_path,
                user_id=str(user.id)
            )
            
            # Build processing result
            result = self._build_processing_result(
                processing_state,
                generate_summary,
                generate_explanation,
                generate_quiz,
                quiz_question_count
            )
            
            # Create response
            response = StudySessionResponse(
                session_id=session_id,
                user_id=str(user.id),
                result=result,
                created_at=datetime.utcnow().isoformat(),
                status="completed" if result.success else "failed"
            )
            
            logger.info(f"Study session completed: {session_id} for user {user.id}")
            return response
            
        except Exception as e:
            logger.error(f"Study session failed: {session_id}, error: {e}")
            
            # Return error response
            error_result = ProcessingResult(
                success=False,
                processing_time_seconds=0.0,
                error_message=str(e),
                image_quality=QualityAssessmentResult(
                    score=0.0,
                    classification="low",
                    issues=["Processing failed"]
                ),
                content_type=ContentTypeResult(
                    content_type="mixed",
                    confidence=0.0
                ),
                text_extraction=TextExtractionResult(
                    text="",
                    confidence=0.0,
                    tool_used=ProcessingTool.NONE
                )
            )
            
            return StudySessionResponse(
                session_id=session_id,
                user_id=str(user.id),
                result=error_result,
                created_at=datetime.utcnow().isoformat(),
                status="failed"
            )
    
    async def _validate_upload_file(self, file: UploadFile):
        """Validate uploaded file"""
        # Check file extension
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file_ext}. Allowed types: {settings.ALLOWED_FILE_TYPES}"
            )
        
        # Check file size
        if file.size and file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
    
    async def _save_uploaded_file(self, file: UploadFile, session_id: str) -> str:
        """Save uploaded file and return path"""
        try:
            # Generate unique filename
            file_ext = os.path.splitext(file.filename)[1]
            filename = f"{session_id}_{uuid.uuid4().hex[:8]}{file_ext}"
            file_path = os.path.join(self.upload_dir, filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            logger.info(f"File saved: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded file"
            )
    
    def _build_processing_result(
        self,
        state: ImageProcessingState,
        include_summary: bool,
        include_explanation: bool,
        include_quiz: bool,
        quiz_count: int
    ) -> ProcessingResult:
        """Build processing result from workflow state"""
        
        # Determine success
        success = (
            state.should_proceed and 
            not state.error_message and
            state.extracted_text and
            len(state.extracted_text.strip()) >= settings.MIN_TEXT_LENGTH
        )
        
        # Build quality assessment result
        quality_result = QualityAssessmentResult(
            score=state.quality_score or 0.0,
            classification=state.quality_classification or "low",
            issues=state.quality_issues or [],
            recommendations=self._generate_quality_recommendations(state)
        )
        
        # Build content type result
        content_result = ContentTypeResult(
            content_type=state.content_type or "mixed",
            confidence=state.content_confidence or 0.0,
            details={
                "processing_tool": state.processing_tool_used,
                "preprocessing_applied": state.needs_preprocessing
            }
        )
        
        # Build text extraction result
        text_result = TextExtractionResult(
            text=state.extracted_text or "",
            confidence=state.extraction_confidence or 0.0,
            tool_used=state.processing_tool_used or ProcessingTool.NONE
        )
        
        # Build optional results
        summary_result = None
        if include_summary and state.summary:
            summary_result = SummaryResult(
                summary=state.summary,
                key_points=self._extract_key_points(state.summary),
                word_count=len(state.summary.split()),
                reading_time_minutes=max(1, len(state.summary.split()) // 200)
            )
        
        explanation_result = None
        if include_explanation and state.explanation:
            explanation_result = ExplanationResult(
                explanation=state.explanation,
                concepts_explained=self._extract_concepts(state.explanation),
                difficulty_level="intermediate",
                related_topics=[]
            )
        
        quiz_result = None
        if include_quiz and state.quiz_questions:
            quiz_questions = [
                QuizQuestion(
                    question=q.get("question", ""),
                    question_type=q.get("question_type", "multiple_choice"),
                    options=q.get("options", []),
                    correct_answer=q.get("correct_answer", ""),
                    explanation=q.get("explanation", ""),
                    difficulty=q.get("difficulty", "medium"),
                    topic=q.get("topic", "General")
                )
                for q in state.quiz_questions[:quiz_count]
            ]
            
            quiz_result = QuizResult(
                questions=quiz_questions,
                total_questions=len(quiz_questions),
                estimated_time_minutes=len(quiz_questions) * 2,  # 2 minutes per question
                topics_covered=list(set(q.topic for q in quiz_questions if q.topic))
            )
        
        # Collect warnings
        warnings = []
        if state.quality_classification == "low":
            warnings.append("Image quality is low, results may be inaccurate")
        if state.extraction_confidence and state.extraction_confidence < 0.7:
            warnings.append("Text extraction confidence is low")
        if state.needs_preprocessing:
            warnings.append("Image required preprocessing")
        
        return ProcessingResult(
            success=success,
            processing_time_seconds=state.processing_time or 0.0,
            summary=summary_result,
            explanation=explanation_result,
            quiz=quiz_result,
            image_quality=quality_result,
            content_type=content_result,
            text_extraction=text_result,
            error_message=state.error_message,
            warnings=warnings
        )
    
    def _generate_quality_recommendations(self, state: ImageProcessingState) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []
        
        if state.quality_issues:
            for issue in state.quality_issues:
                if "blur" in issue.lower():
                    recommendations.append("Hold the camera steady and ensure proper focus")
                elif "dark" in issue.lower() or "light" in issue.lower():
                    recommendations.append("Improve lighting conditions")
                elif "angle" in issue.lower() or "tilt" in issue.lower():
                    recommendations.append("Take the photo straight-on, parallel to the page")
                elif "resolution" in issue.lower():
                    recommendations.append("Use higher resolution camera settings")
        
        if state.quality_score and state.quality_score < 0.6:
            recommendations.append("Consider retaking the photo with better conditions")
        
        return recommendations
    
    def _extract_key_points(self, summary: str) -> List[str]:
        """Extract key points from summary"""
        # Simple extraction - split by sentences and take important ones
        sentences = summary.split('. ')
        key_points = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and any(word in sentence.lower() for word in 
                ['important', 'key', 'main', 'primary', 'essential', 'crucial']):
                key_points.append(sentence)
        
        # If no key points found, take first few sentences
        if not key_points:
            key_points = [s.strip() for s in sentences[:3] if len(s.strip()) > 20]
        
        return key_points[:5]  # Limit to 5 key points
    
    def _extract_concepts(self, explanation: str) -> List[str]:
        """Extract key concepts from explanation"""
        # Simple concept extraction
        concepts = []
        
        # Look for capitalized terms that might be concepts
        import re
        capitalized_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', explanation)
        
        # Filter and clean
        for term in capitalized_terms:
            if len(term) > 3 and term.lower() not in ['the', 'and', 'for', 'this', 'that']:
                concepts.append(term)
        
        return list(set(concepts))[:10]  # Unique concepts, limit to 10
    
    async def get_study_session(self, session_id: str, user: User) -> Optional[StudySessionResponse]:
        """Get study session by ID (if stored in database)"""
        # This would query the database for stored sessions
        # For now, return None as we're not persisting sessions
        return None
    
    async def list_user_sessions(self, user: User, limit: int = 20) -> List[StudySessionResponse]:
        """List user's study sessions (if stored in database)"""
        # This would query the database for user's sessions
        # For now, return empty list
        return []
    
    async def delete_study_session(self, session_id: str, user: User) -> bool:
        """Delete a study session"""
        # This would delete from database and clean up files
        # For now, just try to delete the file
        try:
            # Find and delete associated file
            for filename in os.listdir(self.upload_dir):
                if filename.startswith(session_id):
                    file_path = os.path.join(self.upload_dir, filename)
                    os.remove(file_path)
                    logger.info(f"Deleted file: {file_path}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete session files: {e}")
            return False

    async def process_enhanced_study_image(
        self,
        image_file: UploadFile,
        user: User,
        generate_summary: bool = True,
        generate_explanation: bool = True,
        generate_quiz: bool = True,
        quiz_question_count: int = 5,
        quiz_difficulty: Optional[str] = None,
        explanation_level: Optional[str] = None,
        enable_chunking: bool = False,
        chunk_size: int = 4000,
        max_concurrency: int = 3,
        preserve_equations: bool = True,
        preprocessing: bool = True
    ) -> StudySessionResponse:
        """
        Enhanced study image processing with chunked support
        """
        session_id = str(uuid.uuid4())
        logger.info(f"Starting enhanced study session: {session_id}")
        
        try:
            # Save uploaded file
            file_path = await self._save_uploaded_file(image_file, session_id)
            
            # Initialize processing state
            initial_state = ImageProcessingState(
                image_path=file_path,
                user_id=user.id,
                start_time=datetime.now().timestamp()
            )
            
            # Run initial text extraction and quality assessment
            state = await self.workflow.run_workflow(initial_state)
            
            if not state.extracted_text or len(state.extracted_text.strip()) < 50:
                # Fallback to regular processing for short texts
                enable_chunking = False
            
            # Apply preprocessing if enabled
            processed_text = state.extracted_text
            if preprocessing and processed_text:
                processed_text = preprocess_text_for_math(processed_text)
                state.extracted_text = processed_text
            
            # Determine if chunking should be used
            should_chunk = (
                enable_chunking and 
                processed_text and 
                len(processed_text) > chunk_size * 0.8
            )
            
            if should_chunk:
                logger.info(f"Using chunked processing for session {session_id}")
                result = await self._process_with_chunking(
                    state=state,
                    chunk_size=chunk_size,
                    max_concurrency=max_concurrency,
                    preserve_equations=preserve_equations,
                    generate_summary=generate_summary,
                    generate_explanation=generate_explanation,
                    generate_quiz=generate_quiz,
                    quiz_question_count=quiz_question_count
                )
            else:
                logger.info(f"Using standard processing for session {session_id}")
                # Use existing workflow processing
                if generate_summary:
                    state = await self.workflow.generate_summary_node(state)
                
                if generate_explanation:
                    state = await self.workflow.generate_explanation_node(state)
                
                if generate_quiz:
                    state = await self.workflow.generate_quiz_node(state)
                
                result = self._build_processing_result(state, chunked=False)
            
            # Build and return response
            return self._build_study_session_response(
                session_id=session_id,
                user_id=user.id,
                result=result,
                status="completed"
            )
            
        except Exception as e:
            logger.error(f"Enhanced study session {session_id} failed: {e}")
            error_result = ProcessingResult(
                success=False,
                processing_time_seconds=0,
                error_message=str(e),
                warnings=[]
            )
            
            return self._build_study_session_response(
                session_id=session_id,
                user_id=user.id,
                result=error_result,
                status="failed"
            )


def get_study_helper_service(db: Session) -> StudyHelperService:
    """Get study helper service instance"""
    return StudyHelperService(db)
