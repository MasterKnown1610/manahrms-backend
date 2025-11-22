"""
Schemas for AI Chat functionality
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request schema for AI chat"""
    question: str = Field(..., min_length=1, description="User's question in natural language")
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Optional conversation history for context"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "question": "How many employees do we have?",
                "conversation_history": None
            }
        }


class ChatResponse(BaseModel):
    """Response schema for AI chat"""
    success: bool = True
    message: str = Field(..., description="AI assistant's response")
    question: str = Field(..., description="The question that was asked")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Based on the company data, you have 25 active employees across 5 departments.",
                "question": "How many employees do we have?"
            }
        }

