# app/services/intelligence.py
import json
from typing import Dict, List, Any, Optional

# Modern imports
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from pydantic import BaseModel, Field  # Use Pydantic v2 directly

from app.models.conversation import FactExtractionResult, ExtractedFact, Contradiction
from app.services.memory import MemoryService
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL


# Define Pydantic models for the parser
class FactSchema(BaseModel):
    category: str = Field(description="Category of the fact: ACADEMIC, CAREER, or PERSONAL")
    key: str = Field(description="Key identifier for the fact")
    value: Any = Field(description="Value of the fact")
    status: str = Field(description="NEW, UPDATED, or CONFIRMATION")
    confidence: float = Field(description="Confidence level between 0 and 1", default=1.0)

class ContradictionSchema(BaseModel):
    existing: str = Field(description="The existing information")
    new_information: str = Field(description="The new contradictory information")
    resolution: str = Field(description="How to resolve the contradiction")

class FactOutputSchema(BaseModel):
    extracted_facts: List[FactSchema] = Field(description="List of extracted facts", default_factory=list)
    contradictions: List[ContradictionSchema] = Field(description="List of contradictions found", default_factory=list)

class IntelligenceService:
    def __init__(self):
        self.memory_service = MemoryService()
        self.llm = OllamaLLM(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL, temperature=0.2)
    
    async def extract_facts(self, 
                          student_id: str, 
                          conversation_id: str, 
                          message: str, 
                          response: str) -> FactExtractionResult:
        """Extract facts from a conversation using modern approach"""
        # Get existing student facts
        existing_facts = await self.memory_service.get_student_facts(student_id)
        
        # Set up the output parser
        parser = PydanticOutputParser(pydantic_object=FactOutputSchema)
        
        # Create fact extraction prompt
        fact_template = """
        You are an AI assistant specialized in extracting structured facts about students from conversations.
        
        Based on the following conversation excerpt:
        
        USER: {user_message}
        ASSISTANT: {assistant_response}
        
        Please extract any facts about the student, considering these existing facts:
        {existing_facts}
        
        Extract facts in these categories:
        1. ACADEMIC: courses, study habits, academic performance, interests, challenges
        2. CAREER: goals, interests, skills, experiences, plans
        3. PERSONAL: preferences, challenges, support needs, wellbeing status
        
        For each fact, indicate if it's NEW, UPDATED, or a CONFIRMATION of existing information.
        
        {format_instructions}
        
        Include only definite facts, not speculations.
        """
        
        try:
            # Create the prompt
            prompt = PromptTemplate(
                template=fact_template,
                input_variables=["user_message", "assistant_response", "existing_facts"],
                partial_variables={"format_instructions": parser.get_format_instructions()}
            )
            
            # Create the chain using LCEL
            chain = prompt | self.llm | parser
            
            # Run the chain
            result = await chain.ainvoke({
                "user_message": message,
                "assistant_response": response,
                "existing_facts": json.dumps(existing_facts, default=str)
            })
            
            # Convert to our application's model
            fact_result = FactExtractionResult(
                extracted_facts=[
                    ExtractedFact(
                        category=fact.category,
                        key=fact.key,
                        value=fact.value,
                        status=fact.status,
                        confidence=fact.confidence
                    ) for fact in result.extracted_facts
                ],
                contradictions=[
                    Contradiction(
                        existing=contradiction.existing,
                        new_information=contradiction.new_information,
                        resolution=contradiction.resolution
                    ) for contradiction in result.contradictions
                ]
            )
            
            # Update student facts in database
            await self.memory_service.update_student_facts(student_id, fact_result)
            
            return fact_result
            
        except Exception as e:
            print(f"Error extracting facts: {e}")
            # Return empty result on error
            return FactExtractionResult()
        
    async def summarize_conversation(self, conversation_id: str) -> str:
        """Generate a summary of a conversation for future reference"""
        # Get the conversation history
        message_history = self.memory_service.get_message_history(conversation_id)
        messages = message_history.messages
        
        # Format messages for the prompt
        formatted_messages = []
        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'system':
                continue  # Skip system messages
            role = 'Student' if hasattr(msg, 'type') and msg.type == 'human' else 'Mentor'
            formatted_messages.append(f"{role}: {msg.content}")
        
        conversation_text = "\n".join(formatted_messages)
        
        # Create the summarization prompt
        prompt = PromptTemplate(
            template="""
            Below is a conversation between a student and an AI mentor.
            Please provide a concise summary of the main topics discussed, any issues raised, 
            and any actions or advice given.
            
            CONVERSATION:
            {conversation}
            
            SUMMARY:
            """,
            input_variables=["conversation"]
        )
        
        # Create and run the chain
        chain = prompt | self.llm | StrOutputParser()
        summary = await chain.ainvoke({"conversation": conversation_text})
        
        # Store the summary in the conversation document
        await self.memory_service.update_conversation_summary(conversation_id, summary)
        
        return summary