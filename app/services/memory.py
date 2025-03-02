# app/services/memory.py
from pymongo import MongoClient
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import json

# Use modern imports
from langchain_mongodb import MongoDBChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import BaseChatMessageHistory

from app.config import MONGODB_URI, MONGODB_DB
from app.models.student import Student, Fact, StudentFacts
from app.models.conversation import MessageRole, Message, ExtractedFact, FactExtractionResult

class MemoryService:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[MONGODB_DB]
        self.students = self.db.students
        self.conversations = self.db.conversations
        self.facts = self.db.facts
    
    # Student Management
    async def get_student(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Get a student by ID"""
        return self.students.find_one({"_id": student_id})
    
    async def get_student_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a student by email address"""
        return self.students.find_one({"email": email})
    
    async def create_student(self, student: Student) -> str:
        """Create a new student"""
        student_dict = student.dict(exclude={"id"})
        # Initialize with empty facts structure
        student_dict["facts"] = {"academic": {}, "career": {}, "personal": {}}
        result = self.students.insert_one(student_dict)
        return str(result.inserted_id)
    
    async def update_student(self, student_id: str, data: Dict[str, Any]) -> bool:
        """Update student information"""
        data["updated_at"] = datetime.now()
        result = self.students.update_one(
            {"_id": student_id},
            {"$set": data}
        )
        return result.modified_count > 0
    
    # Conversation management using BaseChatMessageHistory
    def get_message_history(self, conversation_id: str) -> BaseChatMessageHistory:
        """Get a message history for a conversation ID"""
        return MongoDBChatMessageHistory(
            connection_string=MONGODB_URI,
            database_name=MONGODB_DB,
            collection_name="conversations",
            session_id=conversation_id
        )
    
    async def create_conversation(self, student_id: str, mentor_type: str = "primary") -> str:
        """Create a new conversation and return its ID"""
        conversation = {
            "student_id": student_id,
            "mentor_type": mentor_type,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        result = self.conversations.insert_one(conversation)
        conversation_id = str(result.inserted_id)
        
        # Create initial system message in the conversation
        message_history = self.get_message_history(conversation_id)
        message_history.add_message(SystemMessage(
            content="I am an AI mentor for undergraduate students, providing support in academics, career planning, and mental wellbeing."
        ))
        
        return conversation_id
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID"""
        return self.conversations.find_one({"_id": conversation_id})
    
    async def get_recent_conversations(self, student_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversations for a student"""
        return list(
            self.conversations.find({"student_id": student_id})
            .sort("updated_at", -1)
            .limit(limit)
        )
    
    # Fact Management
    async def update_student_facts(self, student_id: str, facts: FactExtractionResult) -> bool:
        """Update student facts based on extraction results"""
        success = True
        
        # Store extracted facts in facts collection for history
        for fact in facts.extracted_facts:
            fact_record = {
                "student_id": student_id,
                "category": fact.category,
                "key": fact.key,
                "value": fact.value,
                "status": fact.status,
                "confidence": fact.confidence,
                "extracted_at": datetime.now()
            }
            self.facts.insert_one(fact_record)
            
            # Update the student document with the new/updated fact
            category = fact.category.lower()
            key = fact.key
            value = fact.value
            
            # Path to the fact within the document
            fact_path = f"facts.{category}.{key}"
            
            # Update the student document
            result = self.students.update_one(
                {"_id": student_id},
                {"$set": {
                    fact_path: {
                        "value": value,
                        "last_updated": datetime.now(),
                        "confidence": fact.confidence
                    }
                }}
            )
            
            if result.modified_count == 0:
                success = False
        
        return success
    
    async def get_student_facts(self, student_id: str) -> Dict[str, Any]:
        """Get all facts for a student"""
        student = await self.get_student(student_id)
        if student and "facts" in student:
            return student["facts"]
        return {"academic": {}, "career": {}, "personal": {}}