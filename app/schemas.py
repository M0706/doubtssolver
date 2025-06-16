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


class HistoryResponse(BaseModel):
    questions: List[QuestionHistoryItem] = Field(..., description="List of previous questions and answers")
    total_count: int = Field(..., description="Total number of questions in history")
    limit: int = Field(..., description="Number of questions returned")
    offset: int = Field(..., description="Number of questions skipped") 