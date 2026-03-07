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
        
        # Check AI usage limit
        from app.api.v1.services.subscription_service import SubscriptionService
        can_query, error_message = SubscriptionService.check_ai_usage_limit(
            db=db,
            company_id=current_user.company_id
        )
        
        if not can_query:
            return ChatResponse(
                success=False,
                message=error_message or "AI usage limit reached. Please purchase an add-on to increase your limit.",
                question=request.question
            )
        
        # Get AI response
        ai_response = ai_service.chat(
            db=db,
            company_id=current_user.company_id,
            user_question=request.question,
            conversation_history=conversation_history
        )
        
        # Estimate tokens used (rough estimate: 1 token ≈ 4 characters)
        # This is a simple estimation; in production, use tiktoken for accurate counting
        estimated_tokens = len(request.question) // 4 + len(ai_response) // 4
        
        # Record AI usage
        try:
            SubscriptionService.record_ai_usage(
                db=db,
                company_id=current_user.company_id,
                user_id=current_user.id,
                tokens_used=estimated_tokens,
                question=request.question
            )
        except Exception as e:
            # Log error but don't fail the request
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to record AI usage: {e}")
        
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

