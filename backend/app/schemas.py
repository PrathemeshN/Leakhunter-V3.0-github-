from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    email: str


class TokenData(BaseModel):
    email: Optional[str] = None


class BreachSourceCreate(BaseModel):
    name: str
    url: str
    source_type: str
    reliability_score: Optional[int] = 50
    scrape_frequency_minutes: Optional[int] = 60
    config: Optional[Dict[str, Any]] = {}


class ScrapedLeakPayload(BaseModel):
    source_id: str
    title: str
    description: Optional[str] = ""
    raw_content: str
    original_url: Optional[str] = ""
    source_reference: Optional[str] = ""
    breach_date: Optional[str] = None
    record_count: Optional[int] = 1


class TrainPayload(BaseModel):
    texts: List[str]
    labels: List[str]
