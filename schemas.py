from pydantic import BaseModel, EmailStr, Field
from typing import Optional
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