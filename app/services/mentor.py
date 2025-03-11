# app/services/mentor.py
from typing import Dict, Any, List, AsyncGenerator, Optional
import asyncio
import json

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import OllamaLLM
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.callbacks.base import BaseCallbackHandler

from langchain_core.runnables import RunnableConfig

from app.services.memory import MemoryService
from app.utils.prompts import PRIMARY_MENTOR_PROMPT
from app.models.conversation import MessageRole, Message

class StreamingCallback(BaseCallbackHandler):
    """Callback handler for streaming LLM responses"""
    
    def __init__(self):
        self.tokens = []
    
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Collect tokens as they're generated"""
        self.tokens.append(token)

class MentorService:
    def __init__(self):
        self.memory_service = MemoryService()
        self.last_conversation_id = None
        
    def _create_ollama_llm(self, streaming=True):
        """Create an Ollama LLM instance"""
        from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
        
        # Set up callback for streaming
        if streaming:
            callback = StreamingCallback()
            llm = OllamaLLM(
                base_url=OLLAMA_BASE_URL,
                model=OLLAMA_MODEL,
                temperature=0.7,
                callbacks=[callback]
            )
            return llm, callback
        else:
            llm = OllamaLLM(
                base_url=OLLAMA_BASE_URL,
                model=OLLAMA_MODEL,
                temperature=0.7
            )
            return llm, None
    
    def _create_mentor_chain(self):
        """Create a conversation chain using LCEL"""
        # Get the LLM
        llm, _ = self._create_ollama_llm(streaming=False)
        
        # Create chat prompt template using modern LCEL approach
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=PRIMARY_MENTOR_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            HumanMessage(content="{input}")
        ])
        
        # Create the chain using LCEL
        chain = prompt | llm | StrOutputParser()
        
        return chain
    
    async def respond_to_student(self, 
                           student_id: str, 
                           message: str, 
                           conversation_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Generate a streaming response to a student message"""
        # Get or create conversation using the unified approach
        if not conversation_id:
            conversation_id = await self.memory_service.get_or_create_student_conversation(student_id)
        
        # Store conversation_id in an instance variable
        self.last_conversation_id = conversation_id
        
        # Get student information to include in the prompt
        student = await self.memory_service.get_student(student_id)
        student_facts = student.get("facts", {}) if student else {}
        
        # Format student context using the helper method
        student_info = self._format_student_context(student, student_facts)
        
        # Get conversation history
        message_history = self.memory_service.get_message_history(conversation_id)
        
        # Add the new message to history
        message_history.add_message(HumanMessage(content=message))
        
        # Get all messages - ENSURE WE HAVE ALL PREVIOUS MESSAGES
        history = message_history.messages
        
        # Apply token limit handling for very long conversations, but ensure context is preserved
        history = self._handle_history_token_limit(history)
        
        # For debugging (remove in production)
        print(f"Number of messages in history: {len(history)}")
        for i, msg in enumerate(history):
            print(f"Message {i}: {type(msg).__name__}: {msg.content[:30]}...")
        
        # Create streaming callback
        callback = StreamingCallback()
        
        # Get the LLM with streaming
        llm, _ = self._create_ollama_llm(streaming=True)
        
        # Create runnable using LCEL with explicit memory context
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=PRIMARY_MENTOR_PROMPT + "\n\n" + student_info + 
                        "\n\nIMPORTANT: You must reference previous parts of the conversation when relevant. You have full access to the conversation history."),
            MessagesPlaceholder(variable_name="history"),
            HumanMessage(content="{input}")
        ])
        
        chain = prompt | llm | StrOutputParser()
        
        # Configure streaming
        config = RunnableConfig(
            callbacks=[callback]
        )
        
        # Start a task to run the chain
        task = asyncio.create_task(
            chain.ainvoke(
                {"history": history, "input": message},
                config=config
            )
        )
            
        # Stream tokens as they're generated
        full_response = ""
        previous_token_count = 0
        
        while not task.done():
            await asyncio.sleep(0.05)  # Small delay to allow token collection
            
            if callback and len(callback.tokens) > previous_token_count:
                new_tokens = callback.tokens[previous_token_count:]
                for token in new_tokens:
                    full_response += token
                    yield token
                previous_token_count = len(callback.tokens)
        
        # Get any remaining tokens after the task is done
        if callback and len(callback.tokens) > previous_token_count:
            new_tokens = callback.tokens[previous_token_count:]
            for token in new_tokens:
                full_response += token
                yield token
        
        # Save the AI's response to the history
        message_history.add_message(AIMessage(content=full_response))
        
        # After generating the response, extract facts in the background
        asyncio.create_task(
            self._extract_facts(student_id, conversation_id, message, full_response)
        )
        
        # Yield a special token to indicate the end and include the conversation ID
        yield f"<CONVERSATION_ID>{conversation_id}</CONVERSATION_ID>"
        
    def _format_student_context(self, student, student_facts):
        """Format student information into a rich context for the LLM"""
        if not student:
            return ""
            
        context = f"""
        STUDENT PROFILE:
        Name: {student.get('name', 'Unknown')}
        University: {student.get('university', 'Unknown')}
        Program: {student.get('program', 'Unknown')}
        Year: {student.get('year', 'Unknown')}
        """
        
        # Add facts if available
        if student_facts:
            # Academic facts
            if "academic" in student_facts and student_facts["academic"]:
                context += "\nACADEMIC INFORMATION:\n"
                for key, value in student_facts["academic"].items():
                    fact_value = value.get('value', value) if isinstance(value, dict) else value
                    context += f"- {key.replace('_', ' ').title()}: {fact_value}\n"
            
            # Career facts
            if "career" in student_facts and student_facts["career"]:
                context += "\nCAREER INFORMATION:\n"
                for key, value in student_facts["career"].items():
                    fact_value = value.get('value', value) if isinstance(value, dict) else value
                    context += f"- {key.replace('_', ' ').title()}: {fact_value}\n"
            
            # Personal facts
            if "personal" in student_facts and student_facts["personal"]:
                context += "\nPERSONAL INFORMATION:\n"
                for key, value in student_facts["personal"].items():
                    fact_value = value.get('value', value) if isinstance(value, dict) else value
                    context += f"- {key.replace('_', ' ').title()}: {fact_value}\n"
                    
        return context
    
    def _handle_history_token_limit(self, history):
        """Handle potential token limitations for very long conversation histories"""
        # If history is short enough, return all of it
        if len(history) < 30:  # Increased from 20 to ensure enough context
            return history
            
        # Otherwise, keep system message, early context, and most recent messages
        system_messages = [msg for msg in history if isinstance(msg, SystemMessage)]
        non_system = [msg for msg in history if not isinstance(msg, SystemMessage)]
        
        # Keep first few messages for context and most recent messages
        early_context = non_system[:3]  # Keep first 3 messages for context
        recent_messages = non_system[-20:]  # Keep last 20 messages
        
        # Return system messages plus context messages plus recent messages
        return system_messages + early_context + recent_messages
        
    async def get_last_conversation_id(self) -> str:
        """Get the ID of the last conversation used"""
        return self.last_conversation_id
    
    async def _extract_facts(self, student_id: str, conversation_id: str, message: str, response: str):
        """Extract facts from conversation and update student knowledge"""
        from app.services.intelligence import IntelligenceService
        intelligence = IntelligenceService()
        try:
            await intelligence.extract_facts(student_id, conversation_id, message, response)
        except Exception as e:
            print(f"Error extracting facts: {e}")