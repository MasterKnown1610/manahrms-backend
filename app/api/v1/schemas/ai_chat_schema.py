"""
Schemas for AI Chat functionality
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class ChatMessage(BaseModel):
    """Single chat message for multi-turn conversation history"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request schema for the AI chat endpoint"""

    question: str = Field(..., min_length=1, description="User's message or command in natural language")
    conversation_id: Optional[str] = Field(
        default=None,
        description=(
            "Stable id for this chat thread. Send the same value on follow-up messages so the server "
            "keeps prior user/assistant turns (recommended). Omit on first message to receive a new id in the response."
        ),
    )
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description=(
            "Optional client-held history. If conversation_id is set, the server uses stored history instead "
            "(client transcript is ignored for prior turns). Use conversation_id for reliable multi-turn."
        ),
    )

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Mark my attendance",
                "conversation_id": None,
                "conversation_history": None,
            }
        }


class ChatResponse(BaseModel):
    """Response schema for AI chat"""

    success: bool = True
    message: str = Field(..., description="AI assistant's response")
    question: str = Field(..., description="The question that was asked")
    conversation_id: Optional[str] = Field(
        default=None,
        description="Pass this on the next request as conversation_id to continue the same thread.",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Done! Your attendance has been marked. Punch-in time: 09:32 AM. Have a great day!",
                "question": "Mark my attendance",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
