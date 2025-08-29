"""
AI Study Helper Workflow
LangGraph-based workflow for processing educational images
"""
import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import base64
import io

# LangGraph and LangChain imports
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, AIMessage

# Google Vision API
from google.cloud import vision
import google.generativeai as genai

# Image processing
from PIL import Image
import cv2
import numpy as np

# Local imports
from app.agent.schemas import (
    ImageProcessingState, 
    ImageQuality, 
    ContentType, 
    ProcessingTool,
    QualityAssessmentResult,
    ContentTypeResult,
    TextExtractionResult,
    QuizQuestion,
    QuestionType
)
from app.agent.prompts import (
    QUALITY_CLASSIFIER_PROMPT,
    CONTENT_TYPE_CLASSIFIER_PROMPT,
    SUMMARY_AGENT_PROMPT,
    EXPLANATION_AGENT_PROMPT,
    QUIZ_GENERATOR_PROMPT,
    ROUTING_AGENT_PROMPT,
    SYSTEM_PROMPTS
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class StudyHelperWorkflow:
    """LangGraph workflow for AI Study Helper"""
    
    def __init__(self):
        """Initialize the workflow with AI models and tools"""
        self.setup_ai_models()
        self.graph = self.build_workflow_graph()
    
    def setup_ai_models(self):
        """Setup AI models and services"""
        # Configure Gemini
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-pro')
            self.gemini_vision_model = genai.GenerativeModel('gemini-1.5-pro')
        else:
            logger.warning("Gemini API key not configured")
            
        # Setup LangChain Gemini
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            temperature=0.1,
            google_api_key=settings.GEMINI_API_KEY
        )
        
        # Setup Google Vision (if credentials available)
        try:
            self.vision_client = vision.ImageAnnotatorClient()
        except Exception as e:
            logger.warning(f"Google Vision API not available: {e}")
            self.vision_client = None
    
    def build_workflow_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(ImageProcessingState)
        
        # Add nodes
        workflow.add_node("validate_image", self.validate_image_node)
        workflow.add_node("assess_quality", self.assess_quality_node)
        workflow.add_node("classify_content", self.classify_content_node)
        workflow.add_node("route_processing", self.route_processing_node)
        workflow.add_node("preprocess_image", self.preprocess_image_node)
        workflow.add_node("extract_text", self.extract_text_node)
        workflow.add_node("generate_summary", self.generate_summary_node)
        workflow.add_node("generate_explanation", self.generate_explanation_node)
        workflow.add_node("generate_quiz", self.generate_quiz_node)
        workflow.add_node("finalize_results", self.finalize_results_node)
        
        # Set entry point
        workflow.set_entry_point("validate_image")
        
        # Add edges (workflow flow)
        workflow.add_edge("validate_image", "assess_quality")
        workflow.add_edge("assess_quality", "classify_content")
        workflow.add_edge("classify_content", "route_processing")
        
        # Conditional routing from route_processing
        workflow.add_conditional_edges(
            "route_processing",
            self.should_continue_processing,
            {
                "preprocess": "preprocess_image",
                "extract": "extract_text",
                "end": END
            }
        )
        
        workflow.add_edge("preprocess_image", "extract_text")
        
        # Parallel processing after text extraction
        workflow.add_conditional_edges(
            "extract_text",
            self.route_ai_processing,
            {
                "summary": "generate_summary",
                "explanation": "generate_explanation", 
                "quiz": "generate_quiz",
                "finalize": "finalize_results"
            }
        )
        
        workflow.add_edge("generate_summary", "generate_explanation")
        workflow.add_edge("generate_explanation", "generate_quiz")
        workflow.add_edge("generate_quiz", "finalize_results")
        workflow.add_edge("finalize_results", END)
        
        return workflow.compile()
    
    # Node Functions
    async def validate_image_node(self, state: ImageProcessingState) -> ImageProcessingState:
        """Validate uploaded image"""
        try:
            # Load and validate image
            if state.image_data:
                image = Image.open(io.BytesIO(state.image_data))
            else:
                image = Image.open(state.image_path)
            
            # Check format
            if image.format not in settings.SUPPORTED_IMAGE_FORMATS:
                state.error_message = f"Unsupported image format: {image.format}"
                state.should_proceed = False
                return state
            
            # Check size
            if len(state.image_data or b"") > settings.MAX_IMAGE_SIZE:
                state.error_message = "Image too large for processing"
                state.should_proceed = False
                return state
            
            # Store image data if not already present
            if not state.image_data:
                buffer = io.BytesIO()
                image.save(buffer, format=image.format)
                state.image_data = buffer.getvalue()
            
            logger.info(f"Image validated successfully: {image.size}, {image.format}")
            return state
            
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            state.error_message = f"Image validation failed: {str(e)}"
            state.should_proceed = False
            return state
    
    async def assess_quality_node(self, state: ImageProcessingState) -> ImageProcessingState:
        """Assess image quality using Gemini Vision"""
        try:
            if not state.should_proceed:
                return state
            
            # Prepare image for Gemini
            image_data = base64.b64encode(state.image_data).decode()
            
            # Create prompt
            prompt = QUALITY_CLASSIFIER_PROMPT.format(
                image_description="Analyze this educational image for quality assessment"
            )
            
            # Call Gemini Vision API
            response = await self._call_gemini_vision(prompt, image_data)
            
            # Parse response (simplified - in production, use structured output)
            quality_data = self._parse_quality_response(response)
            
            state.quality_score = quality_data.get("score", 0.5)
            state.quality_classification = ImageQuality(quality_data.get("classification", "medium").lower())
            state.quality_issues = quality_data.get("issues", [])
            
            logger.info(f"Quality assessment: {state.quality_classification}, score: {state.quality_score}")
            return state
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            state.quality_score = 0.3
            state.quality_classification = ImageQuality.LOW
            state.quality_issues = ["Quality assessment failed"]
            return state
    
    async def classify_content_node(self, state: ImageProcessingState) -> ImageProcessingState:
        """Classify content type"""
        try:
            if not state.should_proceed:
                return state
                
            # First, extract basic text for classification
            basic_text = await self._extract_basic_text(state.image_data)
            
            # Prepare prompt
            prompt = CONTENT_TYPE_CLASSIFIER_PROMPT.format(
                image_description="Educational content image",
                extracted_text=basic_text[:500]  # First 500 chars
            )
            
            # Call Gemini
            response = await self._call_gemini_text(prompt)
            content_data = self._parse_content_type_response(response)
            
            state.content_type = ContentType(content_data.get("content_type", "mixed").lower())
            state.content_confidence = content_data.get("confidence", 0.7)
            
            logger.info(f"Content classified as: {state.content_type}")
            return state
            
        except Exception as e:
            logger.error(f"Content classification failed: {e}")
            state.content_type = ContentType.MIXED
            state.content_confidence = 0.5
            return state
    
    async def route_processing_node(self, state: ImageProcessingState) -> ImageProcessingState:
        """Route processing based on quality and content type"""
        try:
            # Determine if preprocessing is needed
            if state.quality_classification == ImageQuality.LOW:
                state.needs_preprocessing = True
                state.recommended_action = "Apply image preprocessing to improve quality"
            elif state.quality_score < settings.QUALITY_THRESHOLD:
                state.needs_preprocessing = True
                state.recommended_action = "Minor preprocessing recommended"
            
            # Check if we should continue
            if state.quality_score < 0.2:  # Very low quality
                state.should_proceed = False
                state.error_message = "Image quality too low for processing"
                return state
            
            # Select processing tool based on content type
            if state.content_type == ContentType.HANDWRITTEN_TEXT:
                state.processing_tool_used = ProcessingTool.TROCR
            elif state.content_type == ContentType.DIAGRAM:
                state.processing_tool_used = ProcessingTool.GEMINI_VISION
            else:
                state.processing_tool_used = ProcessingTool.GOOGLE_VISION
            
            logger.info(f"Routing: preprocessing={state.needs_preprocessing}, tool={state.processing_tool_used}")
            return state
            
        except Exception as e:
            logger.error(f"Routing failed: {e}")
            state.error_message = f"Routing failed: {str(e)}"
            return state
    
    async def preprocess_image_node(self, state: ImageProcessingState) -> ImageProcessingState:
        """Apply image preprocessing"""
        try:
            if not state.needs_preprocessing:
                return state
            
            # Convert to OpenCV format
            image = Image.open(io.BytesIO(state.image_data))
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Apply preprocessing based on quality issues
            processed_image = cv_image.copy()
            
            if "blur" in str(state.quality_issues).lower():
                # Apply sharpening
                kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                processed_image = cv2.filter2D(processed_image, -1, kernel)
            
            if "contrast" in str(state.quality_issues).lower():
                # Enhance contrast
                processed_image = cv2.convertScaleAbs(processed_image, alpha=1.2, beta=10)
            
            if "noise" in str(state.quality_issues).lower():
                # Reduce noise
                processed_image = cv2.medianBlur(processed_image, 3)
            
            # Convert back to bytes
            processed_pil = Image.fromarray(cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB))
            buffer = io.BytesIO()
            processed_pil.save(buffer, format="PNG")
            state.image_data = buffer.getvalue()
            
            logger.info("Image preprocessing completed")
            return state
            
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            # Continue with original image
            return state
    
    async def extract_text_node(self, state: ImageProcessingState) -> ImageProcessingState:
        """Extract text using selected tool"""
        try:
            if not state.should_proceed:
                return state
            
            text = ""
            confidence = 0.0
            
            if state.processing_tool_used == ProcessingTool.GOOGLE_VISION and self.vision_client:
                text, confidence = await self._extract_with_google_vision(state.image_data)
            elif state.processing_tool_used == ProcessingTool.GEMINI_VISION:
                text, confidence = await self._extract_with_gemini_vision(state.image_data)
            else:
                # Fallback to basic extraction
                text, confidence = await self._extract_basic_text(state.image_data), 0.7
            
            state.extracted_text = text
            state.extraction_confidence = confidence
            
            # Check if we have meaningful text
            if len(text.strip()) < settings.MIN_TEXT_LENGTH:
                state.error_message = "Insufficient text extracted from image"
                logger.warning(f"Minimal text extracted: {len(text)} characters")
            
            logger.info(f"Text extracted: {len(text)} characters, confidence: {confidence}")
            return state
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            state.error_message = f"Text extraction failed: {str(e)}"
            return state
    
    async def generate_summary_node(self, state: ImageProcessingState) -> ImageProcessingState:
        """Generate summary using Gemini"""
        try:
            if not state.extracted_text or len(state.extracted_text.strip()) < 10:
                state.summary = "No sufficient text found for summary generation."
                return state
            
            prompt = SUMMARY_AGENT_PROMPT.format(
                extracted_text=state.extracted_text,
                content_type=state.content_type.value if state.content_type else "mixed",
                subject_area="General Education"
            )
            
            response = await self._call_gemini_text(prompt)
            
            # Try to parse JSON response
            try:
                import json
                import re
                
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    parsed = json.loads(json_str)
                    
                    # Use the structured response
                    state.summary = parsed.get("summary_text", response.strip())
                else:
                    # Fallback to raw response
                    state.summary = response.strip()
            except Exception as e:
                logger.warning(f"Failed to parse summary JSON: {e}")
                state.summary = response.strip()
            
            logger.info("Summary generated successfully")
            return state
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            state.summary = f"Summary generation failed: {str(e)}. Original content: {state.extracted_text[:200]}..."
            return state
    
    async def generate_explanation_node(self, state: ImageProcessingState) -> ImageProcessingState:
        """Generate explanation using Gemini"""
        try:
            if not state.extracted_text:
                state.explanation = "No text available for explanation generation."
                return state
            
            prompt = EXPLANATION_AGENT_PROMPT.format(
                extracted_text=state.extracted_text,
                content_type=state.content_type.value if state.content_type else "mixed",
                summary=state.summary or "No summary available",
                difficulty_level="intermediate"
            )
            
            response = await self._call_gemini_text(prompt)
            
            # Try to parse JSON response
            try:
                import json
                import re
                
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    parsed = json.loads(json_str)
                    
                    # Use the structured response
                    state.explanation = parsed.get("detailed_explanation", response.strip())
                else:
                    # Fallback to raw response
                    state.explanation = response.strip()
            except Exception as e:
                logger.warning(f"Failed to parse explanation JSON: {e}")
                state.explanation = response.strip()
            
            logger.info("Explanation generated successfully")
            return state
            
        except Exception as e:
            logger.error(f"Explanation generation failed: {e}")
            state.explanation = f"Explanation generation failed: {str(e)}. Content overview: {state.extracted_text[:300]}..."
            return state
    
    async def generate_quiz_node(self, state: ImageProcessingState) -> ImageProcessingState:
        """Generate quiz questions using Gemini"""
        try:
            if not state.extracted_text:
                state.quiz_questions = []
                return state
            
            prompt = QUIZ_GENERATOR_PROMPT.format(
                extracted_text=state.extracted_text,
                content_type=state.content_type.value if state.content_type else "mixed",
                summary=state.summary or "",
                key_concepts="General educational concepts from the content",
                question_count=settings.DEFAULT_QUIZ_QUESTIONS,
                difficulty_preference="mixed"
            )
            
            response = await self._call_gemini_text(prompt)
            quiz_questions = self._parse_quiz_response(response)
            state.quiz_questions = quiz_questions
            
            logger.info(f"Generated {len(quiz_questions)} quiz questions")
            return state
            
        except Exception as e:
            logger.error(f"Quiz generation failed: {e}")
            # Generate fallback questions based on content
            state.quiz_questions = self._generate_fallback_quiz(state.extracted_text)
            return state
    
    def _generate_fallback_quiz(self, text: str) -> List[Dict[str, Any]]:
        """Generate basic quiz questions as fallback"""
        try:
            # Split text into sentences
            sentences = text.split('. ')
            quiz_questions = []
            
            for i, sentence in enumerate(sentences[:5]):  # Up to 5 questions
                sentence = sentence.strip()
                if len(sentence) > 20:  # Minimum sentence length
                    # Create a fill-in-the-blank question
                    words = sentence.split()
                    if len(words) > 5:
                        # Remove a key word (not articles, prepositions)
                        key_words = [w for w in words if len(w) > 3 and w.lower() not in ['the', 'and', 'for', 'with', 'from']]
                        if key_words:
                            missing_word = key_words[0]
                            question_text = sentence.replace(missing_word, "______", 1)
                            
                            quiz_questions.append({
                                "question": f"Fill in the blank: {question_text}",
                                "question_type": "fill_in_blank",
                                "options": [missing_word, "placeholder1", "placeholder2", "placeholder3"],
                                "correct_answer": missing_word,
                                "explanation": f"The correct answer is '{missing_word}' based on the context in the original text.",
                                "difficulty": "medium",
                                "topic": "Content Comprehension"
                            })
            
            # Add a general comprehension question
            if text and len(quiz_questions) < 3:
                quiz_questions.append({
                    "question": "What is the main topic discussed in this content?",
                    "question_type": "short_answer",
                    "options": [],
                    "correct_answer": "The main topic relates to the educational content provided.",
                    "explanation": "This question tests general comprehension of the material.",
                    "difficulty": "easy",
                    "topic": "General Comprehension"
                })
            
            return quiz_questions
        except Exception as e:
            logger.error(f"Fallback quiz generation failed: {e}")
            return []
    
    async def finalize_results_node(self, state: ImageProcessingState) -> ImageProcessingState:
        """Finalize processing results"""
        try:
            # Calculate processing time
            state.processing_time = time.time() - getattr(state, 'start_time', time.time())
            
            # Log completion
            logger.info(f"Processing completed for user {state.user_id}")
            logger.info(f"Results: summary={bool(state.summary)}, explanation={bool(state.explanation)}, quiz={len(state.quiz_questions)} questions")
            
            return state
            
        except Exception as e:
            logger.error(f"Finalization failed: {e}")
            return state
    
    # Conditional Edge Functions
    def should_continue_processing(self, state: ImageProcessingState) -> str:
        """Determine next step after routing"""
        if not state.should_proceed:
            return "end"
        elif state.needs_preprocessing:
            return "preprocess"
        else:
            return "extract"
    
    def route_ai_processing(self, state: ImageProcessingState) -> str:
        """Route to AI processing steps"""
        if not state.extracted_text or len(state.extracted_text.strip()) < 10:
            return "finalize"
        return "summary"
    
    # Helper Methods
    async def _call_gemini_vision(self, prompt: str, image_data: str) -> str:
        """Call Gemini Vision API"""
        try:
            # Convert base64 to image format expected by Gemini
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            response = self.gemini_vision_model.generate_content([prompt, image])
            return response.text
        except Exception as e:
            logger.error(f"Gemini Vision API call failed: {e}")
            raise
    
    async def _call_gemini_text(self, prompt: str) -> str:
        """Call Gemini text API"""
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"Gemini Text API call failed: {e}")
            raise
    
    async def _extract_with_google_vision(self, image_data: bytes) -> tuple[str, float]:
        """Extract text using Google Vision API"""
        try:
            image = vision.Image(content=image_data)
            response = self.vision_client.text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                return texts[0].description, 0.9
            return "", 0.0
        except Exception as e:
            logger.error(f"Google Vision extraction failed: {e}")
            return "", 0.0
    
    async def _extract_with_gemini_vision(self, image_data: bytes) -> tuple[str, float]:
        """Extract text using Gemini Vision"""
        try:
            image = Image.open(io.BytesIO(image_data))
            prompt = "Extract all text content from this image. Provide clean, formatted text without interpretation."
            
            response = self.gemini_vision_model.generate_content([prompt, image])
            return response.text, 0.8
        except Exception as e:
            logger.error(f"Gemini Vision extraction failed: {e}")
            return "", 0.0
    
    async def _extract_basic_text(self, image_data: bytes) -> str:
        """Basic text extraction using EasyOCR or fallback methods"""
        try:
            # Try EasyOCR first
            try:
                import easyocr
                
                # Initialize reader for English (can be extended for other languages)
                reader = easyocr.Reader(['en'])
                
                # Convert bytes to numpy array
                import numpy as np
                from PIL import Image
                import io
                
                image = Image.open(io.BytesIO(image_data))
                image_array = np.array(image)
                
                # Extract text
                results = reader.readtext(image_array)
                
                # Combine all detected text
                extracted_text = " ".join([result[1] for result in results if result[2] > 0.5])  # Confidence > 0.5
                
                if extracted_text.strip():
                    return extracted_text.strip()
                    
            except ImportError:
                logger.warning("EasyOCR not available, falling back to basic extraction")
            except Exception as e:
                logger.warning(f"EasyOCR failed: {e}, falling back to basic extraction")
            
            # Fallback: Use Tesseract if available
            try:
                import pytesseract
                from PIL import Image
                import io
                
                image = Image.open(io.BytesIO(image_data))
                text = pytesseract.image_to_string(image)
                
                if text.strip():
                    return text.strip()
                    
            except ImportError:
                logger.warning("Tesseract not available")
            except Exception as e:
                logger.warning(f"Tesseract failed: {e}")
            
            # Last resort: Use Google Vision if available
            if self.vision_client:
                try:
                    text, _ = await self._extract_with_google_vision(image_data)
                    if text.strip():
                        return text.strip()
                except Exception as e:
                    logger.warning(f"Google Vision fallback failed: {e}")
            
            # Final fallback
            return "Text extraction failed - please ensure the image contains clear, readable text"
            
        except Exception as e:
            logger.error(f"All text extraction methods failed: {e}")
            return "Text extraction failed due to processing error"
    
    def _parse_quality_response(self, response: str) -> Dict[str, Any]:
        """Parse quality assessment response"""
        try:
            # Try to parse as JSON first
            import json
            import re
            
            # Clean response to extract JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                
                # Validate and clean the response
                return {
                    "score": min(1.0, max(0.0, float(parsed.get("score", 0.5)))),
                    "classification": parsed.get("classification", "MEDIUM").lower(),
                    "issues": parsed.get("issues", [])[:5],  # Limit to 5 issues
                    "recommendations": parsed.get("recommendations", [])[:5]
                }
        except Exception as e:
            logger.warning(f"Failed to parse quality JSON response: {e}")
            
        # Fallback to text parsing
        try:
            lines = response.lower().split('\n')
            score = 0.5
            classification = "medium"
            issues = []
            
            for line in lines:
                if 'score' in line and any(char.isdigit() for char in line):
                    import re
                    numbers = re.findall(r'0\.\d+|\d+\.\d+', line)
                    if numbers:
                        score = float(numbers[0])
                        
                if any(word in line for word in ['high', 'good', 'excellent']):
                    classification = "high"
                elif any(word in line for word in ['low', 'poor', 'bad']):
                    classification = "low"
                    
                if any(word in line for word in ['blur', 'dark', 'noise', 'tilt']):
                    issues.append(line.strip())
            
            return {
                "score": min(1.0, max(0.0, score)),
                "classification": classification,
                "issues": issues[:3],  # Limit to 3 issues
                "recommendations": []
            }
        except:
            return {
                "score": 0.5, 
                "classification": "medium", 
                "issues": ["Quality assessment failed"],
                "recommendations": ["Try taking a clearer photo"]
            }
    
    def _parse_content_type_response(self, response: str) -> Dict[str, Any]:
        """Parse content type classification response"""
        try:
            # Try to parse as JSON first
            import json
            import re
            
            # Clean response to extract JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                
                return {
                    "content_type": parsed.get("content_type", "mixed").lower(),
                    "confidence": min(1.0, max(0.0, float(parsed.get("confidence", 0.7))))
                }
        except Exception as e:
            logger.warning(f"Failed to parse content type JSON response: {e}")
            
        # Fallback to text parsing
        try:
            content_type = "mixed"
            confidence = 0.7
            
            response_lower = response.lower()
            
            if "handwritten" in response_lower or "handwriting" in response_lower:
                content_type = "handwritten_text"
                confidence = 0.8
            elif "printed" in response_lower or "textbook" in response_lower:
                content_type = "printed_text"
                confidence = 0.8
            elif "diagram" in response_lower or "chart" in response_lower or "graph" in response_lower:
                content_type = "diagram"
                confidence = 0.8
            
            return {
                "content_type": content_type,
                "confidence": confidence
            }
        except:
            return {"content_type": "mixed", "confidence": 0.5}
    
    def _parse_quiz_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse quiz generation response"""
        try:
            # Try to parse as JSON first
            import json
            import re
            
            # Clean response to extract JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                
                if "questions" in parsed:
                    quiz_questions = []
                    for q in parsed["questions"][:10]:  # Limit to 10 questions
                        quiz_questions.append({
                            "question": q.get("question", "Sample question"),
                            "question_type": q.get("type", "multiple_choice"),
                            "options": q.get("options", ["Option A", "Option B", "Option C", "Option D"]),
                            "correct_answer": q.get("correct_answer", "Option A"),
                            "explanation": q.get("explanation", "Generated explanation"),
                            "difficulty": q.get("difficulty", "medium"),
                            "topic": q.get("topic", "General")
                        })
                    return quiz_questions
        except Exception as e:
            logger.warning(f"Failed to parse quiz JSON response: {e}")
            
        # Fallback: Generate basic questions from the response text
        try:
            quiz_questions = []
            
            # Split by question markers or double newlines
            potential_questions = response.split('\n\n')
            
            for i, q_text in enumerate(potential_questions[:5]):  # Limit to 5 questions
                if len(q_text.strip()) > 20:  # Minimum question length
                    # Try to extract a proper question
                    lines = q_text.strip().split('\n')
                    question_text = lines[0]
                    
                    # Look for multiple choice options
                    options = []
                    for line in lines[1:]:
                        if any(line.strip().startswith(prefix) for prefix in ['A)', 'B)', 'C)', 'D)', 'a)', 'b)', 'c)', 'd)']):
                            options.append(line.strip())
                    
                    if not options:
                        options = ["True", "False"] if "true" in question_text.lower() or "false" in question_text.lower() else [
                            "Option A", "Option B", "Option C", "Option D"
                        ]
                    
                    quiz_questions.append({
                        "question": question_text[:300],  # Limit question length
                        "question_type": "true_false" if len(options) == 2 else "multiple_choice",
                        "options": options[:4],  # Limit to 4 options
                        "correct_answer": options[0] if options else "True",
                        "explanation": f"This question tests understanding of the concept discussed in the content.",
                        "difficulty": "medium",
                        "topic": "Content Analysis"
                    })
            
            return quiz_questions
        except Exception as e:
            logger.warning(f"Failed to parse quiz text response: {e}")
            return []
    
    # Main Processing Method
    async def process_image(self, image_path: str, user_id: str) -> ImageProcessingState:
        """Process an image through the complete workflow"""
        try:
            # Initialize state
            state = ImageProcessingState(
                image_path=image_path,
                user_id=user_id,
                start_time=time.time()
            )
            
            # Run the workflow
            result_dict = await self.graph.ainvoke(state.dict())
            
            # Convert back to ImageProcessingState object
            result = ImageProcessingState(**result_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            # Return error state
            error_state = ImageProcessingState(
                image_path=image_path,
                user_id=user_id,
                start_time=time.time(),
                error_message=f"Workflow failed: {str(e)}",
                should_proceed=False
            )
            return error_state


# Global workflow instance
workflow_instance = None

def get_workflow() -> StudyHelperWorkflow:
    """Get or create workflow instance"""
    global workflow_instance
    if workflow_instance is None:
        workflow_instance = StudyHelperWorkflow()
    return workflow_instance
