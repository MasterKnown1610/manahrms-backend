"""
AI Chat routes for natural language queries about company data
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_database_session
from app.api.v1.dependencies import get_current_authenticated_user
from app.api.v1.models.user_model import User
from app.api.v1.schemas.ai_chat_schema import ChatRequest, ChatResponse
from app.api.v1.services.ai_chat_service import AIChatService


router = APIRouter(prefix="/ai-chat", tags=["AI Chat"])


@router.post("/ask", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def ask_ai_chatbot(
    request: ChatRequest,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Ask the AI chatbot a question about company data in natural language.
    
    The AI will answer based on the logged-in company's data including:
    - Employees
    - Departments
    - Projects
    - Tasks
    - Company information
    
    The response is optimized to use minimal tokens while providing accurate answers.
    """
    try:
        # Initialize AI chat service
        try:
            ai_service = AIChatService()
        except ValueError as e:
            # Handle missing OpenAI API key
            return ChatResponse(
                success=False,
                message="AI service is not configured. Please contact your administrator to set up the OpenAI API key.",
                question=request.question
            )
        
        # Convert conversation history if provided
        conversation_history = None
        if request.conversation_history:
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]
        
        # Get AI response
        ai_response = ai_service.chat(
            db=db,
            company_id=current_user.company_id,
            user_question=request.question,
            conversation_history=conversation_history
        )
        
        return ChatResponse(
            success=True,
            message=ai_response,
            question=request.question
        )
    
    except Exception as e:
        return ChatResponse(
            success=False,
            message=f"Error processing your question: {str(e)}",
            question=request.question
        )

