# app/models/student.py
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class FactCategory(str, Enum):
    ACADEMIC = "academic"
    CAREER = "career"
    PERSONAL = "personal"

class Fact(BaseModel):
    category: FactCategory
    key: str
    value: Any
    last_updated: datetime = Field(default_factory=datetime.now)
    source: str = "conversation"
    confidence: float = 1.0

class StudentFacts(BaseModel):
    academic: Dict[str, Any] = {}
    career: Dict[str, Any] = {}
    personal: Dict[str, Any] = {}

class Student(BaseModel):
    id: Optional[str] = None
    name: str
    email: str
    university: Optional[str] = None
    program: Optional[str] = None
    year: Optional[int] = None
    facts: StudentFacts = Field(default_factory=StudentFacts)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)