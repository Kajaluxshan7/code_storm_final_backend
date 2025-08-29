"""
Enhanced Document Processing Service
Handles chunked document processing with mathematical content support
"""
import asyncio
import logging
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import math

from app.agent.workflow import StudyHelperWorkflow
from app.agent.schemas import ImageProcessingState, TextExtractionResult

logger = logging.getLogger(__name__)

class DocumentChunk:
    """Represents a chunk of document text"""
    def __init__(self, 
                 chunk_id: str, 
                 content: str, 
                 start_index: int, 
                 end_index: int,
                 overlap_size: int = 0):
        self.chunk_id = chunk_id
        self.content = content
        self.start_index = start_index
        self.end_index = end_index
        self.overlap_size = overlap_size
        self.word_count = len(content.split())
        self.character_count = len(content)
        self.has_math = self._detect_math_content()
        self.has_chemical = self._detect_chemical_content()
        self.has_supersub = self._detect_supersub_content()
        
    def _detect_math_content(self) -> bool:
        """Detect mathematical content in chunk"""
        math_patterns = [
            r'\$[^$]+\$',  # LaTeX inline math
            r'\$\$[^$]+\$\$',  # LaTeX block math
            r'[a-zA-Z0-9\s]*=\s*[a-zA-Z0-9\s+\-*/()^]+',  # Simple equations
            r'\\[a-zA-Z]+',  # LaTeX commands
            r'[∑∫π√∞±≈≠≤≥αβγδθλμσφψω]',  # Mathematical symbols
        ]
        return any(re.search(pattern, self.content, re.IGNORECASE) for pattern in math_patterns)
    
    def _detect_chemical_content(self) -> bool:
        """Detect chemical formulas in chunk"""
        chemical_patterns = [
            r'[A-Z][a-z]?[0-9]*(?:\([A-Z][a-z]?[0-9]*\))*[0-9]*',  # Chemical formulas
            r'H2O|CO2|NaCl|CH4|O2|N2|Ca\(OH\)2|H2SO4|HCl|NaOH',  # Common chemicals
        ]
        return any(re.search(pattern, self.content) for pattern in chemical_patterns)
    
    def _detect_supersub_content(self) -> bool:
        """Detect superscript/subscript content in chunk"""
        supersub_patterns = [
            r'\^[a-zA-Z0-9]+',  # Superscript
            r'_[a-zA-Z0-9]+',   # Subscript
            r'[0-9]+\^[0-9]+',  # Number with superscript
            r'[a-zA-Z]+_[0-9]+',  # Variable with subscript
            r'x²|x³|m²|cm³|kg/m³',  # Common superscript/subscript patterns
        ]
        return any(re.search(pattern, self.content, re.IGNORECASE) for pattern in supersub_patterns)

class EnhancedDocumentProcessor:
    """Enhanced document processor with chunking support"""
    
    def __init__(self, workflow: StudyHelperWorkflow):
        self.workflow = workflow
        
    def create_chunks(self, 
                     text: str, 
                     chunk_size: int = 4000, 
                     overlap_size: int = 200,
                     preserve_math: bool = True) -> List[DocumentChunk]:
        """
        Split text into manageable chunks while preserving context
        """
        if len(text) <= chunk_size:
            return [DocumentChunk("chunk_0", text, 0, len(text))]
        
        chunks = []
        start_index = 0
        chunk_index = 0
        
        while start_index < len(text):
            end_index = min(start_index + chunk_size, len(text))
            
            # Find a good breaking point
            if end_index < len(text):
                break_points = [
                    text.rfind('\n\n', start_index, end_index),  # Paragraph break
                    text.rfind('\n', start_index, end_index),    # Line break
                    text.rfind('. ', start_index, end_index),    # Sentence end
                    text.rfind('! ', start_index, end_index),    # Exclamation
                    text.rfind('? ', start_index, end_index),    # Question
                ]
                
                # Find the best break point that's not too close to the start
                min_chunk_size = chunk_size * 0.7
                best_break = None
                for bp in break_points:
                    if bp > start_index + min_chunk_size:
                        best_break = bp + 1
                        break
                
                if best_break:
                    end_index = best_break
            
            # Extract chunk content with overlap
            chunk_start = max(0, start_index - (overlap_size if chunk_index > 0 else 0))
            chunk_content = text[chunk_start:end_index]
            
            # Preserve mathematical expressions at chunk boundaries
            if preserve_math and chunk_index > 0:
                chunk_content = self._preserve_math_at_boundary(chunk_content, text, chunk_start)
            
            chunk = DocumentChunk(
                chunk_id=f"chunk_{chunk_index}",
                content=chunk_content,
                start_index=chunk_start,
                end_index=end_index,
                overlap_size=overlap_size if chunk_index > 0 else 0
            )
            
            chunks.append(chunk)
            start_index = end_index
            chunk_index += 1
        
        return chunks
    
    def _preserve_math_at_boundary(self, chunk_content: str, full_text: str, start_pos: int) -> str:
        """Ensure mathematical expressions aren't split across chunks"""
        # Check for incomplete mathematical expressions at the beginning
        math_patterns = [
            r'\$[^$]*$',  # Incomplete LaTeX math
            r'\\[a-zA-Z]*$',  # Incomplete LaTeX command
        ]
        
        for pattern in math_patterns:
            if re.search(pattern, chunk_content[:100]):  # Check first 100 chars
                # Find the complete expression in the full text
                complete_match = re.search(r'\$[^$]+\$|\\[a-zA-Z]+', full_text[start_pos-50:start_pos+200])
                if complete_match:
                    # Adjust chunk to include complete expression
                    chunk_content = complete_match.group(0) + chunk_content[complete_match.end():]
        
        return chunk_content
    
    async def process_chunks_parallel(self, 
                                    chunks: List[DocumentChunk],
                                    original_state: ImageProcessingState,
                                    max_concurrency: int = 3,
                                    progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        Process chunks in parallel with rate limiting
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        results = []
        
        async def process_single_chunk(chunk: DocumentChunk, index: int) -> Dict[str, Any]:
            async with semaphore:
                try:
                    # Create a new state for this chunk
                    chunk_state = ImageProcessingState(
                        image_path=original_state.image_path,
                        user_id=original_state.user_id,
                        extracted_text=chunk.content,
                        quality_score=original_state.quality_score,
                        quality_classification=original_state.quality_classification,
                        content_type=original_state.content_type,
                        content_confidence=original_state.content_confidence,
                    )
                    
                    # Process chunk through workflow nodes
                    summary_result = await self._process_chunk_summary(chunk_state, chunk)
                    explanation_result = await self._process_chunk_explanation(chunk_state, chunk)
                    quiz_result = await self._process_chunk_quiz(chunk_state, chunk)
                    
                    # Report progress
                    if progress_callback:
                        progress_callback(index + 1, len(chunks))
                    
                    return {
                        'chunk_id': chunk.chunk_id,
                        'summary': summary_result,
                        'explanation': explanation_result,
                        'quiz': quiz_result,
                        'has_math': chunk.has_math,
                        'has_chemical': chunk.has_chemical,
                        'has_supersub': chunk.has_supersub,
                        'word_count': chunk.word_count,
                        'character_count': chunk.character_count,
                    }
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk.chunk_id}: {e}")
                    return {
                        'chunk_id': chunk.chunk_id,
                        'error': str(e),
                        'has_math': chunk.has_math,
                        'has_chemical': chunk.has_chemical,
                        'has_supersub': chunk.has_supersub,
                    }
        
        # Process chunks in batches
        for i in range(0, len(chunks), max_concurrency):
            batch = chunks[i:i + max_concurrency]
            batch_tasks = [
                process_single_chunk(chunk, i + j) 
                for j, chunk in enumerate(batch)
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)
            
            # Add delay between batches to respect rate limits
            if i + max_concurrency < len(chunks):
                await asyncio.sleep(1)
        
        return results
    
    async def _process_chunk_summary(self, state: ImageProcessingState, chunk: DocumentChunk) -> str:
        """Process summary for a single chunk"""
        try:
            # Use the existing summary generation method
            summary_state = await self.workflow.generate_summary_node(state)
            return summary_state.summary or f"Summary for {chunk.chunk_id}"
        except Exception as e:
            logger.error(f"Error generating summary for {chunk.chunk_id}: {e}")
            return f"Summary generation failed for {chunk.chunk_id}: {str(e)}"
    
    async def _process_chunk_explanation(self, state: ImageProcessingState, chunk: DocumentChunk) -> str:
        """Process explanation for a single chunk"""
        try:
            # Use the existing explanation generation method
            explanation_state = await self.workflow.generate_explanation_node(state)
            return explanation_state.explanation or f"Explanation for {chunk.chunk_id}"
        except Exception as e:
            logger.error(f"Error generating explanation for {chunk.chunk_id}: {e}")
            return f"Explanation generation failed for {chunk.chunk_id}: {str(e)}"
    
    async def _process_chunk_quiz(self, state: ImageProcessingState, chunk: DocumentChunk) -> List[Dict[str, Any]]:
        """Process quiz questions for a single chunk"""
        try:
            # Use the existing quiz generation method
            quiz_state = await self.workflow.generate_quiz_node(state)
            return quiz_state.quiz_questions[:3]  # Limit to 3 questions per chunk
        except Exception as e:
            logger.error(f"Error generating quiz for {chunk.chunk_id}: {e}")
            return []
    
    def merge_chunk_results(self, 
                          chunks: List[DocumentChunk], 
                          chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge results from all chunks into a cohesive response
        """
        successful_results = [r for r in chunk_results if 'error' not in r]
        
        # Merge summaries
        summaries = [r.get('summary', '') for r in successful_results if r.get('summary')]
        merged_summary = self._merge_summaries(summaries)
        
        # Merge explanations
        explanations = [r.get('explanation', '') for r in successful_results if r.get('explanation')]
        merged_explanation = self._merge_explanations(explanations)
        
        # Merge quiz questions
        all_quiz_questions = []
        for result in successful_results:
            quiz = result.get('quiz', [])
            if isinstance(quiz, list):
                all_quiz_questions.extend(quiz)
        
        # Remove duplicate questions and limit total
        unique_quiz = self._deduplicate_quiz_questions(all_quiz_questions)[:15]
        
        # Calculate statistics
        total_chunks = len(chunks)
        successful_chunks = len(successful_results)
        failed_chunks = total_chunks - successful_chunks
        
        math_chunks = sum(1 for r in chunk_results if r.get('has_math', False))
        chemical_chunks = sum(1 for r in chunk_results if r.get('has_chemical', False))
        supersub_chunks = sum(1 for r in chunk_results if r.get('has_supersub', False))
        
        return {
            'merged_summary': merged_summary,
            'merged_explanation': merged_explanation,
            'merged_quiz': unique_quiz,
            'chunk_statistics': {
                'total_chunks': total_chunks,
                'successful_chunks': successful_chunks,
                'failed_chunks': failed_chunks,
                'math_chunks': math_chunks,
                'chemical_chunks': chemical_chunks,
                'supersub_chunks': supersub_chunks,
            },
            'processing_metadata': {
                'chunked_processing': True,
                'chunk_results': chunk_results,
            }
        }
    
    def _merge_summaries(self, summaries: List[str]) -> str:
        """Merge multiple summaries into a coherent summary"""
        if not summaries:
            return "No summary could be generated."
        
        if len(summaries) == 1:
            return summaries[0]
        
        # Simple merging strategy - could be enhanced with AI
        merged = "## Document Summary\n\n"
        for i, summary in enumerate(summaries, 1):
            merged += f"### Section {i}\n\n{summary}\n\n"
        
        return merged.strip()
    
    def _merge_explanations(self, explanations: List[str]) -> str:
        """Merge multiple explanations into a coherent explanation"""
        if not explanations:
            return "No explanation could be generated."
        
        if len(explanations) == 1:
            return explanations[0]
        
        # Simple merging strategy
        merged = "## Detailed Explanation\n\n"
        for i, explanation in enumerate(explanations, 1):
            merged += f"### Part {i}\n\n{explanation}\n\n"
        
        return merged.strip()
    
    def _deduplicate_quiz_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate quiz questions"""
        seen_questions = set()
        unique_questions = []
        
        for question in questions:
            if isinstance(question, dict):
                question_text = question.get('question', '').strip().lower()
                if question_text and question_text not in seen_questions:
                    seen_questions.add(question_text)
                    unique_questions.append(question)
        
        return unique_questions
    
    def estimate_processing_time(self, 
                               text_length: int, 
                               chunk_size: int = 4000,
                               max_concurrency: int = 3) -> Dict[str, Any]:
        """
        Estimate processing time for chunked processing
        """
        chunks_needed = max(1, math.ceil(text_length / chunk_size))
        
        # Base processing time per chunk (seconds)
        base_time_per_chunk = 5.0
        
        # Complexity factors
        complexity_multiplier = 1.0
        if text_length > 10000:
            complexity_multiplier = 1.5
        if text_length > 20000:
            complexity_multiplier = 2.0
        
        # Calculate total time considering concurrency
        total_sequential_time = chunks_needed * base_time_per_chunk * complexity_multiplier
        estimated_time = total_sequential_time / max_concurrency
        
        complexity = 'low'
        if chunks_needed > 3:
            complexity = 'medium'
        if chunks_needed > 8:
            complexity = 'high'
        
        return {
            'estimated_time_seconds': round(estimated_time),
            'chunks_required': chunks_needed,
            'complexity': complexity,
            'recommend_chunking': chunks_needed > 1,
        }

def preprocess_text_for_math(text: str) -> str:
    """
    Preprocess text to better handle mathematical content
    """
    # Normalize mathematical symbols
    text = text.replace('×', '*').replace('÷', '/')
    
    # Fix common OCR errors in mathematical contexts
    text = re.sub(r'(\d)\s*[oO]\s*(\d)', r'\1 0 \2', text)  # Fix 'o' as zero
    text = re.sub(r'([Il])\s*(\d)', r'1 \2', text)  # Fix 'I' or 'l' as 1
    
    # Preserve spacing around mathematical operators
    text = re.sub(r'(\d)\s*([+\-*/=])\s*(\d)', r'\1 \2 \3', text)
    
    # Normalize fractions
    text = re.sub(r'(\d+)/(\d+)', r'\\frac{\1}{\2}', text)
    
    return text
