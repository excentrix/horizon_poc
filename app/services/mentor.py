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
        # Get or create conversation
        if not conversation_id:
            conversation_id = await self.memory_service.create_conversation(student_id)
        
        # Store conversation_id in an instance variable
        self.last_conversation_id = conversation_id
        
        # Get student information to include in the prompt
        student = await self.memory_service.get_student(student_id)
        student_info = f"STUDENT INFO:\n{json.dumps(student, default=str)}" if student else ""
        
        # Get conversation history
        message_history = self.memory_service.get_message_history(conversation_id)
        
        # Add the new message to history
        message_history.add_message(HumanMessage(content=message))
        
        # Get all messages
        history = message_history.messages
        
        # Create streaming callback
        callback = StreamingCallback()
        
        # Get the LLM with streaming
        llm, _ = self._create_ollama_llm(streaming=True)
        
        # Create runnable using LCEL
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=PRIMARY_MENTOR_PROMPT + "\n\n" + student_info),
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