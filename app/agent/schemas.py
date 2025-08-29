"""
AI Agent Schemas
Pydantic models for AI processing workflow
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class ImageQuality(str, Enum):
    """Image quality classification"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ContentType(str, Enum):
    """Content type classification"""
    HANDWRITTEN_TEXT = "handwritten_text"
    PRINTED_TEXT = "printed_text" 
    DIAGRAM = "diagram"
    MIXED = "mixed"


class ProcessingTool(str, Enum):
    """AI processing tools"""
    TROCR = "trocr"
    PADDLEOCR = "paddleocr"
    GOOGLE_VISION = "google_vision"
    GEMINI_VISION = "gemini_vision"
    NONE = "none"


class QuestionType(str, Enum):
    """Quiz question types"""
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    TRUE_FALSE = "true_false"
    FILL_IN_BLANK = "fill_in_blank"


# Request/Response Models
class ImageUploadRequest(BaseModel):
    """Image upload request schema"""
    file_name: str
    file_size: int
    content_type: str


class ImageProcessingState(BaseModel):
    """State object passed through the LangGraph workflow"""
    # Input data
    image_path: str
    image_data: Optional[bytes] = None
    user_id: str
    
    # Processing metadata
    start_time: Optional[float] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Quality assessment
    quality_score: Optional[float] = None
    quality_classification: Optional[ImageQuality] = None
    quality_issues: List[str] = Field(default_factory=list)
    
    # Content type classification
    content_type: Optional[ContentType] = None
    content_confidence: Optional[float] = None
    
    # Text extraction
    extracted_text: Optional[str] = None
    extraction_confidence: Optional[float] = None
    processing_tool_used: Optional[ProcessingTool] = None
    
    # AI Analysis
    summary: Optional[str] = None
    explanation: Optional[str] = None
    quiz_questions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Routing decisions
    needs_preprocessing: bool = False
    should_proceed: bool = True
    recommended_action: Optional[str] = None


class QualityAssessmentResult(BaseModel):
    """Quality assessment result"""
    score: float = Field(..., ge=0.0, le=1.0, description="Quality score between 0 and 1")
    classification: ImageQuality
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class ContentTypeResult(BaseModel):
    """Content type classification result"""
    content_type: ContentType
    confidence: float = Field(..., ge=0.0, le=1.0)
    details: Dict[str, Any] = Field(default_factory=dict)


class TextExtractionResult(BaseModel):
    """Text extraction result"""
    text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    tool_used: ProcessingTool
    bounding_boxes: Optional[List[Dict[str, Any]]] = None
    language_detected: Optional[str] = None


class SummaryResult(BaseModel):
    """Summary generation result"""
    summary: str
    key_points: List[str] = Field(default_factory=list)
    word_count: int
    reading_time_minutes: int


class ExplanationResult(BaseModel):
    """Explanation generation result"""
    explanation: str
    concepts_explained: List[str] = Field(default_factory=list)
    difficulty_level: Literal["beginner", "intermediate", "advanced"]
    related_topics: List[str] = Field(default_factory=list)


class QuizQuestion(BaseModel):
    """Individual quiz question"""
    question: str
    question_type: QuestionType
    options: Optional[List[str]] = None  # For MCQ
    correct_answer: str
    explanation: Optional[str] = None
    difficulty: Literal["easy", "medium", "hard"]
    topic: Optional[str] = None


class QuizResult(BaseModel):
    """Quiz generation result"""
    questions: List[QuizQuestion]
    total_questions: int
    estimated_time_minutes: int
    topics_covered: List[str] = Field(default_factory=list)


class ProcessingResult(BaseModel):
    """Final processing result"""
    success: bool
    processing_time_seconds: float
    
    # Results
    summary: Optional[SummaryResult] = None
    explanation: Optional[ExplanationResult] = None
    quiz: Optional[QuizResult] = None
    
    # Metadata
    image_quality: QualityAssessmentResult
    content_type: ContentTypeResult
    text_extraction: TextExtractionResult
    
    # Error handling
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class StudySessionRequest(BaseModel):
    """Study session creation request"""
    image_file: str  # File path or URL
    generate_summary: bool = True
    generate_explanation: bool = True
    generate_quiz: bool = True
    quiz_question_count: int = Field(default=5, ge=1, le=20)
    quiz_difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    preferred_explanation_level: Optional[Literal["beginner", "intermediate", "advanced"]] = None


class StudySessionResponse(BaseModel):
    """Study session response"""
    session_id: str
    user_id: str
    result: ProcessingResult
    created_at: str
    status: Literal["completed", "failed", "processing"]


# Error Models
class ProcessingError(BaseModel):
    """Processing error details"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retry_suggested: bool = False


class ValidationError(BaseModel):
    """Validation error details"""
    field: str
    message: str
    invalid_value: Any = None
