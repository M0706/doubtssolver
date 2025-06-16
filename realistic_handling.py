"""
Realistic Question Processing Service
Handles unknown/uncertain question types gracefully
"""

import asyncio
import hashlib
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

class ClassificationConfidence(Enum):
    UNKNOWN = "unknown"
    LOW = "low"      # < 0.5
    MEDIUM = "medium" # 0.5 - 0.8
    HIGH = "high"     # > 0.8

@dataclass
class QuestionClassification:
    category: Optional[str] = None
    question_type: Optional[str] = None
    confidence: float = 0.0
    method: str = "unknown"
    raw_data: Dict[str, Any] = None

class QuestionProcessor:
    def __init__(self):
        self.fallback_prompts = {
            "default": """You are a helpful GMAT tutor. The user has asked a question but we're not sure what type it is. 
            Please analyze the question and provide the best possible answer with step-by-step reasoning.""",
            
            "math_suspected": """This appears to be a math question. Please solve it step by step, showing your work clearly.""",
            
            "verbal_suspected": """This appears to be a verbal/reading question. Please analyze it carefully and provide a clear explanation."""
        }
    
    async def process_question(
        self, 
        question_text: str, 
        user_hint_category: Optional[str] = None,
        user_hint_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a question with graceful handling of unknown types
        """
        
        # Step 1: Try to classify (but don't fail if this fails)
        classification = await self._attempt_classification(
            question_text, user_hint_category, user_hint_type
        )
        
        # Step 2: Choose the best prompt based on what we know
        prompt = self._select_prompt(question_text, classification)
        
        # Step 3: Process with AI (with fallbacks)
        response = await self._get_ai_response(prompt)
        
        # Step 4: Store with uncertainty info
        await self._store_question_with_uncertainty(
            question_text, classification, response
        )
        
        return {
            "answer": response,
            "classification": classification,
            "confidence": classification.confidence,
            "needs_review": classification.confidence < 0.5
        }
    
    async def _attempt_classification(
        self, 
        question_text: str, 
        user_category: Optional[str],
        user_type: Optional[str]
    ) -> QuestionClassification:
        """
        Try to classify, but gracefully handle failures
        """
        
        # Start with user hints if available
        if user_category and user_type:
            return QuestionClassification(
                category=user_category,
                question_type=user_type,
                confidence=0.6,  # Medium confidence for user input
                method="user_provided"
            )
        
        # Try AI classification
        try:
            ai_classification = await self._ai_classify(question_text)
            if ai_classification:
                return ai_classification
        except Exception as e:
            print(f"AI classification failed: {e}")
            # Continue to fallback
        
        # Try keyword-based classification
        keyword_classification = self._keyword_classify(question_text)
        if keyword_classification:
            return keyword_classification
        
        # Complete fallback
        return QuestionClassification(
            category="unknown",
            question_type="unknown", 
            confidence=0.0,
            method="fallback"
        )
    
    async def _ai_classify(self, question_text: str) -> Optional[QuestionClassification]:
        """
        AI classification with timeout and error handling
        """
        try:
            # Simplified classification prompt (not your 10k char contemplator)
            prompt = f"""
            Classify this GMAT question. Respond with just: CATEGORY|TYPE|CONFIDENCE
            
            Examples:
            - Math question → Quantitative|Problem Solving|0.9
            - Reading passage → Verbal|Reading Comprehension|0.8
            - Grammar question → Verbal|Sentence Correction|0.7
            
            Question: {question_text}
            
            Response:"""
            
            # Use shorter timeout for classification
            response = await asyncio.wait_for(
                self._quick_ai_call(prompt), 
                timeout=10.0
            )
            
            # Parse response
            parts = response.strip().split('|')
            if len(parts) == 3:
                return QuestionClassification(
                    category=parts[0].strip(),
                    question_type=parts[1].strip(),
                    confidence=float(parts[2].strip()),
                    method="ai_classified"
                )
                
        except asyncio.TimeoutError:
            print("AI classification timed out")
        except Exception as e:
            print(f"AI classification error: {e}")
        
        return None
    
    def _keyword_classify(self, question_text: str) -> Optional[QuestionClassification]:
        """
        Simple keyword-based classification as fallback
        """
        text_lower = question_text.lower()
        
        # Math keywords
        math_keywords = ['equation', 'solve', 'calculate', 'x =', 'find x', 'algebra', 'geometry']
        if any(keyword in text_lower for keyword in math_keywords):
            return QuestionClassification(
                category="Quantitative",
                question_type="Problem Solving",
                confidence=0.4,
                method="keyword_match"
            )
        
        # Verbal keywords  
        verbal_keywords = ['passage', 'author', 'paragraph', 'reading', 'comprehension']
        if any(keyword in text_lower for keyword in verbal_keywords):
            return QuestionClassification(
                category="Verbal",
                question_type="Reading Comprehension", 
                confidence=0.4,
                method="keyword_match"
            )
        
        return None
    
    def _select_prompt(self, question_text: str, classification: QuestionClassification) -> str:
        """
        Select the best prompt based on what we know (or don't know)
        """
        
        # If we have high confidence classification, use specific prompt
        if classification.confidence > 0.8:
            if "quantitative" in classification.category.lower():
                return f"{self.fallback_prompts['math_suspected']}\n\nQuestion: {question_text}"
            elif "verbal" in classification.category.lower():
                return f"{self.fallback_prompts['verbal_suspected']}\n\nQuestion: {question_text}"
        
        # Default: Generic helpful prompt
        return f"{self.fallback_prompts['default']}\n\nQuestion: {question_text}"
    
    async def _get_ai_response(self, prompt: str) -> str:
        """
        Get AI response with multiple fallback attempts
        """
        attempts = [
            {"model": "gpt-4", "timeout": 30},
            {"model": "gpt-3.5-turbo", "timeout": 20},
            {"model": "fallback", "timeout": 15}
        ]
        
        for attempt in attempts:
            try:
                response = await asyncio.wait_for(
                    self._ai_call(prompt, attempt["model"]), 
                    timeout=attempt["timeout"]
                )
                if response and len(response.strip()) > 20:
                    return response
            except Exception as e:
                print(f"AI attempt failed with {attempt['model']}: {e}")
                continue
        
        # Final fallback
        return "I apologize, but I'm having trouble processing your question right now. Please try again later."
    
    async def _store_question_with_uncertainty(
        self, 
        question_text: str, 
        classification: QuestionClassification,
        response: str
    ):
        """
        Store question data with uncertainty tracking
        """
        
        # Generate hash for similarity matching
        question_hash = hashlib.sha256(question_text.encode()).hexdigest()[:16]
        
        # Store in database with all uncertainty info
        question_data = {
            "question_text": question_text,
            "question_hash": question_hash,
            "user_category": None,  # We don't have this
            "user_type": None,      # We don't have this
            "inferred_category": classification.category,
            "inferred_type": classification.question_type,
            "classification_confidence": classification.confidence,
            "classification_method": classification.method,
            "needs_manual_review": classification.confidence < 0.5,
            "ai_response": response,
            "processed_at": "NOW()"
        }
        
        # Add to review queue if uncertain
        if classification.confidence < 0.5:
            await self._add_to_review_queue(question_data)
        
        return question_data
    
    async def _add_to_review_queue(self, question_data: Dict[str, Any]):
        """
        Add uncertain classifications to manual review queue
        """
        print(f"Added to review queue: {question_data['question_text'][:50]}...")
        # In real implementation, this would go to database
        pass
    
    # Placeholder methods for actual AI calls
    async def _quick_ai_call(self, prompt: str) -> str:
        # Simulate AI call for classification
        await asyncio.sleep(0.1)  # Simulate network delay
        return "Quantitative|Problem Solving|0.8"
    
    async def _ai_call(self, prompt: str, model: str) -> str:
        # Simulate AI call for full response
        await asyncio.sleep(0.5)  # Simulate network delay
        return "This is a math problem. To solve 2x + 5 = 13, subtract 5 from both sides to get 2x = 8, then divide by 2 to get x = 4."

# Usage example
async def main():
    processor = QuestionProcessor()
    
    # User just pastes a question - no type info
    result = await processor.process_question(
        "What is the value of x in the equation 2x + 5 = 13?"
    )
    
    print(f"Answer: {result['answer']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Classification: {result['classification'].category} - {result['classification'].question_type}")
    print(f"Needs Review: {result['needs_review']}")

if __name__ == "__main__":
    asyncio.run(main()) 