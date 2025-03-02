# app/models/conversation.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ExtractedFact(BaseModel):
    category: str
    key: str
    value: Any
    status: str  # NEW, UPDATED, CONFIRMATION
    confidence: float = 1.0

class Contradiction(BaseModel):
    existing: str
    new_information: str
    resolution: str

class FactExtractionResult(BaseModel):
    extracted_facts: List[ExtractedFact] = []
    contradictions: List[Contradiction] = []