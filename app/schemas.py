from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    id: int
    email: EmailStr
    username: str

class DoubtEntryCreate(BaseModel):
    question_text: str
    subject_category: Optional[str] = None
    options: Optional[dict] = None
    question_type: Optional[str] = None

class DoubtEntryOut(BaseModel):
    id: int
    user_id: int
    question_text: str
    full_prompt_sent: str
    ai_response: str
    timestamp: datetime
    subject_category: Optional[str] = None


# Q&A API Models
class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=10, max_length=2000, description="The question to be answered")
    subject_category: Optional[str] = Field(None, max_length=50, description="Subject category like Math, Science, etc.")
    question_type: Optional[str] = Field(None, max_length=50, description="Type of question like MCQ, descriptive, etc.")


class QuestionResponse(BaseModel):
    question_id: int = Field(..., description="Unique identifier for the question")
    question: str = Field(..., description="The original question")
    answer: str = Field(..., description="AI-generated answer")
    subject_category: Optional[str] = Field(None, description="Subject category")
    question_type: Optional[str] = Field(None, description="Type of question")
    timestamp: datetime = Field(..., description="When the question was processed")


class QuestionHistoryItem(BaseModel):
    question_id: int
    question: str
    answer: str
    subject_category: Optional[str] = None
    question_type: Optional[str] = None
    timestamp: datetime
    
    # Optional uncertainty fields (for admin/debugging)
    confidence: Optional[float] = None
    method: Optional[str] = None
    needs_review: Optional[bool] = None
    status: Optional[str] = None


class HistoryResponse(BaseModel):
    questions: List[QuestionHistoryItem] = Field(..., description="List of previous questions and answers")
    total_count: int = Field(..., description="Total number of questions in history")
    limit: int = Field(..., description="Number of questions returned")
    offset: int = Field(..., description="Number of questions skipped")


# Feedback Schemas
class QuestionFeedback(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback_text: Optional[str] = Field(None, max_length=1000, description="Optional feedback text")
    classification_feedback: Optional[dict] = Field(None, description="Feedback on classification accuracy")


class CacheFeedback(BaseModel):
    feedback_type: str = Field(..., description="Type of feedback: helpful, wrong, irrelevant, partially_helpful")
    feedback_text: Optional[str] = Field(None, max_length=500, description="Optional feedback text")


# Admin/Analytics Schemas
class QuestionStats(BaseModel):
    total_questions: int
    questions_by_category: dict
    questions_by_confidence: dict
    cache_hit_rate: float
    review_queue_size: int


class CacheStats(BaseModel):
    total_entries: int
    active_entries: int
    disabled_entries: int
    avg_usage_count: float
    total_cache_hits: int
    hit_rate_last_24h: float