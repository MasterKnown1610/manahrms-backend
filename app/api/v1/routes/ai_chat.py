"""
AI Chat routes - Agentic AI that performs real HRMS actions via natural language.
Endpoints: POST /ask (JSON), POST /ask/stream (SSE), POST /transcribe (STT), POST /speak (TTS).
"""
import json
import logging
import uuid
from typing import Dict, List, Tuple

from fastapi import APIRouter, Depends, status, Query, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from datetime import datetime

from app.db.session import get_database_session, SessionLocal
from app.api.v1.dependencies import get_current_authenticated_user
from app.api.v1.models.user_model import User, UserRole
from app.api.v1.models.subscription_model import AIUsage, CompanyAIUsage
from app.api.v1.schemas.ai_chat_schema import (
    ChatRequest,
    ChatResponse,
    TranscribeResponse,
    SpeakRequest,
    SpeakResponse,
)
from app.api.v1.services.agentic_ai_service import AgenticAIService
from app.api.v1.services.voice_service import VoiceService
from app.api.v1.services.ai_conversation_memory import (
    append_turn,
    get_messages,
    new_conversation_id,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-chat", tags=["AI Chat"])


def _resolve_thread(
    request: ChatRequest, company_id: int, user_id: int
) -> Tuple[List[Dict[str, str]], str]:
    """
    Returns (prior_messages_for_model, conversation_id).
    If client sends conversation_id, load server-side history. Otherwise start a new id
    and optionally seed from request.conversation_history once.
    """
    cid = (request.conversation_id or "").strip()
    if cid:
        try:
            uuid.UUID(cid)
        except ValueError:
            cid = new_conversation_id()
            prior: List[Dict[str, str]] = []
        else:
            prior = get_messages(company_id, user_id, cid)
    else:
        cid = new_conversation_id()
        prior = []
        if request.conversation_history:
            prior = [
                {"role": m.role, "content": m.content}
                for m in request.conversation_history
                if m.role in ("user", "assistant") and m.content
            ]
    return prior, cid


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


@router.post("/ask", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def ask_ai_chatbot(
    request: ChatRequest,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """
    Agentic AI assistant that understands natural language and performs real actions.

    **Admin can say things like:**
    - "Create an employee named John Doe, email john@acme.com, hire date today, password Welcome@123"
    - "Add a high priority task 'Fix login bug' and assign it to John"
    - "Schedule a Google Meet tomorrow at 3pm for 1 hour"
    - "Show me all pending leave requests"
    - "Approve leave request 5"
    - "How many employees are present today?"

    **Employee can say things like:**
    - "Mark my attendance" / "Punch in"
    - "Punch out"
    - "What are my pending tasks?"
    - "Mark task 12 as in progress"
    - "Apply for sick leave from April 15 to April 17"
    - "How many leave days do I have left?"
    - "Show my attendance this month"
    """
    try:
        try:
            agent = AgenticAIService()
        except ValueError:
            return ChatResponse(
                success=False,
                message="AI service is not configured. Please contact your administrator to set up the OpenAI API key.",
                question=request.question,
            )

        # Check AI usage limit
        from app.api.v1.services.subscription_service import SubscriptionService
        can_query, error_message = SubscriptionService.check_ai_usage_limit(
            db=db,
            company_id=current_user.company_id,
        )
        if not can_query:
            return ChatResponse(
                success=False,
                message=error_message or "AI usage limit reached. Please purchase an add-on to increase your limit.",
                question=request.question,
                conversation_id=(request.conversation_id or "").strip() or None,
            )

        prior_messages, conversation_id = _resolve_thread(
            request, current_user.company_id, current_user.id
        )

        # Run the agentic loop — returns (text, real_token_count)
        ai_response, tokens_used = agent.chat(
            db=db,
            user=current_user,
            question=request.question,
            conversation_history=prior_messages or None,
        )

        append_turn(
            current_user.company_id,
            current_user.id,
            conversation_id,
            request.question,
            ai_response,
        )

        # Record AI usage with real token count from OpenAI
        try:
            SubscriptionService.record_ai_usage(
                db=db,
                company_id=current_user.company_id,
                user_id=current_user.id,
                tokens_used=tokens_used,
                question=request.question,
            )
        except Exception as e:
            logger.error(f"Failed to record AI usage: {e}")

        return ChatResponse(
            success=True,
            message=ai_response,
            question=request.question,
            conversation_id=conversation_id,
        )

    except Exception as e:
        return ChatResponse(
            success=False,
            message=f"Error processing your request: {str(e)}",
            question=request.question,
            conversation_id=(request.conversation_id or "").strip() or None,
        )


@router.post("/ask/stream", summary="AI chat (Server-Sent Events)")
async def ask_ai_chatbot_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """
    Same agent as `/ask`, but streams the assistant reply as **SSE** (`text/event-stream`).

    Events (JSON in each `data:` line):
    - `{"type":"meta","conversation_id":"..."}` — reuse this id on the next call
    - `{"type":"token","text":"..."}` — partial assistant text (chunked)
    - `{"type":"done","success":true,"tokens":123}` — finished

    **Multi-turn:** send `conversation_id` from `meta` on every follow-up so missing fields
    (e.g. last name) can be supplied in the next `question`.
    """
    try:
        agent = AgenticAIService()
    except ValueError:

        def err_gen():
            yield _sse(
                {
                    "type": "error",
                    "message": "AI service is not configured (missing OPENAI_API_KEY).",
                }
            )

        return StreamingResponse(err_gen(), media_type="text/event-stream")

    from app.api.v1.services.subscription_service import SubscriptionService

    can_query, error_message = SubscriptionService.check_ai_usage_limit(
        db=db,
        company_id=current_user.company_id,
    )
    if not can_query:

        def limit_gen():
            yield _sse(
                {
                    "type": "error",
                    "message": error_message
                    or "AI usage limit reached. Please purchase an add-on to increase your limit.",
                }
            )

        return StreamingResponse(limit_gen(), media_type="text/event-stream")

    prior_messages, conversation_id = _resolve_thread(
        request, current_user.company_id, current_user.id
    )
    user_id = current_user.id
    company_id = current_user.company_id

    def event_generator():
        yield _sse({"type": "meta", "conversation_id": conversation_id})
        stream_db = SessionLocal()
        try:
            db_user = stream_db.query(User).filter(User.id == user_id).first()
            if not db_user:
                yield _sse({"type": "error", "message": "User not found"})
                return
            try:
                ai_response, tokens_used = agent.chat(
                    db=stream_db,
                    user=db_user,
                    question=request.question,
                    conversation_history=prior_messages or None,
                )
            except Exception as e:
                logger.exception("AI stream chat failed")
                yield _sse({"type": "error", "message": str(e)})
                return

            append_turn(
                company_id,
                user_id,
                conversation_id,
                request.question,
                ai_response,
            )

            try:
                SubscriptionService.record_ai_usage(
                    db=stream_db,
                    company_id=company_id,
                    user_id=user_id,
                    tokens_used=tokens_used,
                    question=request.question,
                )
            except Exception as e:
                logger.error(f"Failed to record AI usage: {e}")

            text = ai_response or ""
            step = 40
            for i in range(0, len(text), step):
                yield _sse({"type": "token", "text": text[i : i + step]})
            yield _sse({"type": "done", "success": True, "tokens": tokens_used})
        finally:
            stream_db.close()

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )


# ─── Voice (STT / TTS) ────────────────────────────────────────────────────────

@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    status_code=status.HTTP_200_OK,
    summary="Speech-to-text (Whisper)",
)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Recorded audio (webm, mp3, wav, m4a, ogg, …)"),
    language: Optional[str] = Form(
        default=None,
        description="Optional ISO-639-1 language hint (e.g. en, te). Omit for auto-detect.",
    ),
    current_user: User = Depends(get_current_authenticated_user),
):
    """
    Convert voice input to text. Frontend should send multipart FormData with field **`audio`**,
    then pass `transcript` as `question` to `/ask` or `/ask/stream`.
    """
    _ = current_user  # auth required; same company/user gate as /ask
    try:
        voice = VoiceService()
    except ValueError:
        return TranscribeResponse(
            success=False,
            transcript="",
            message="AI service is not configured. Please contact your administrator to set up the OpenAI API key.",
        )

    try:
        data = await audio.read()
        if not data:
            return TranscribeResponse(
                success=False,
                transcript="",
                message="Audio file is required.",
            )
        if len(data) > settings.MAX_VOICE_AUDIO_SIZE:
            mb = settings.MAX_VOICE_AUDIO_SIZE // (1024 * 1024)
            return TranscribeResponse(
                success=False,
                transcript="",
                message=f"Audio file is too large. Maximum size is {mb}MB.",
            )

        filename = audio.filename or "voice.webm"
        transcript = voice.transcribe(
            audio_bytes=data,
            filename=filename,
            language=language,
        )
        if not transcript:
            return TranscribeResponse(
                success=False,
                transcript="",
                message="Could not understand audio. Please try again.",
            )
        return TranscribeResponse(success=True, transcript=transcript, message=None)
    except ValueError as e:
        return TranscribeResponse(success=False, transcript="", message=str(e))
    except Exception as e:
        logger.exception("Voice transcribe failed")
        return TranscribeResponse(
            success=False,
            transcript="",
            message=f"Error transcribing audio: {str(e)}",
        )


@router.post(
    "/speak",
    response_model=SpeakResponse,
    status_code=status.HTTP_200_OK,
    summary="Text-to-speech (OpenAI TTS)",
)
async def speak_text(
    request: SpeakRequest,
    current_user: User = Depends(get_current_authenticated_user),
):
    """
    Convert assistant (or any) text to base64 audio for SPA playback.
    Typical flow: `/transcribe` → `/ask` → `/speak` with `text` = assistant `message`.
    """
    _ = current_user
    try:
        voice = VoiceService()
    except ValueError:
        return SpeakResponse(
            success=False,
            message="AI service is not configured. Please contact your administrator to set up the OpenAI API key.",
        )

    try:
        audio_b64, fmt, content_type = voice.speak(
            text=request.text,
            voice=request.voice,
            audio_format=request.format,
        )
        return SpeakResponse(
            success=True,
            audio_base64=audio_b64,
            format=fmt,
            content_type=content_type,
            message=None,
        )
    except ValueError as e:
        return SpeakResponse(success=False, message=str(e))
    except Exception as e:
        logger.exception("Voice speak failed")
        return SpeakResponse(
            success=False,
            message=f"Error generating speech: {str(e)}",
        )


# ─── Usage Tracking Endpoints ─────────────────────────────────────────────────

@router.get("/usage/me", summary="My AI Usage")
async def get_my_ai_usage(
    year: Optional[int] = Query(None, description="Year (default: current year)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month 1-12 (default: current month)"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """
    Get the current user's AI usage for a given month.
    Returns total queries, total tokens consumed, and a per-day breakdown.
    """
    now = datetime.utcnow()
    target_year = year or now.year
    target_month = month or now.month

    # Aggregate totals for this user this month
    records = db.query(AIUsage).filter(
        AIUsage.company_id == current_user.company_id,
        AIUsage.user_id == current_user.id,
        func.extract("year", AIUsage.created_at) == target_year,
        func.extract("month", AIUsage.created_at) == target_month,
    ).order_by(AIUsage.created_at.desc()).all()

    total_queries = len(records)
    total_tokens = sum(r.tokens_used for r in records)

    # Per-day breakdown
    daily: dict = {}
    for r in records:
        day = r.created_at.date().isoformat()
        if day not in daily:
            daily[day] = {"queries": 0, "tokens": 0}
        daily[day]["queries"] += 1
        daily[day]["tokens"] += r.tokens_used

    # Company-level limit for context
    company_usage = db.query(CompanyAIUsage).filter(
        CompanyAIUsage.company_id == current_user.company_id,
        CompanyAIUsage.year == target_year,
        CompanyAIUsage.month == target_month,
    ).first()

    return {
        "user_id": current_user.id,
        "user_name": current_user.full_name,
        "period": f"{target_year}-{target_month:02d}",
        "total_queries": total_queries,
        "total_tokens": total_tokens,
        "company_queries_used": company_usage.queries_used if company_usage else 0,
        "company_queries_limit": company_usage.total_limit if company_usage else 0,
        "company_queries_remaining": company_usage.remaining_queries if company_usage else 0,
        "daily_breakdown": [
            {"date": day, "queries": v["queries"], "tokens": v["tokens"]}
            for day, v in sorted(daily.items())
        ],
    }


@router.get("/usage/users", summary="All Users AI Usage (Admin only)")
async def get_all_users_ai_usage(
    year: Optional[int] = Query(None, description="Year (default: current year)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month 1-12 (default: current month)"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """
    Admin only. Returns per-user AI usage breakdown for the company this month.
    Shows each user's total queries and tokens consumed.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    now = datetime.utcnow()
    target_year = year or now.year
    target_month = month or now.month

    # Aggregate per user
    rows = db.query(
        AIUsage.user_id,
        func.count(AIUsage.id).label("total_queries"),
        func.sum(AIUsage.tokens_used).label("total_tokens"),
        func.max(AIUsage.created_at).label("last_used"),
    ).filter(
        AIUsage.company_id == current_user.company_id,
        func.extract("year", AIUsage.created_at) == target_year,
        func.extract("month", AIUsage.created_at) == target_month,
    ).group_by(AIUsage.user_id).all()

    # Fetch user names
    from app.api.v1.models.user_model import User as UserModel
    user_ids = [r.user_id for r in rows if r.user_id]
    users_map = {
        u.id: {"name": u.full_name, "email": u.email, "role": u.role.value}
        for u in db.query(UserModel).filter(UserModel.id.in_(user_ids)).all()
    }

    # Company summary
    company_usage = db.query(CompanyAIUsage).filter(
        CompanyAIUsage.company_id == current_user.company_id,
        CompanyAIUsage.year == target_year,
        CompanyAIUsage.month == target_month,
    ).first()

    user_stats = []
    for r in sorted(rows, key=lambda x: -(x.total_tokens or 0)):
        info = users_map.get(r.user_id, {"name": "Unknown", "email": "", "role": "unknown"})
        user_stats.append({
            "user_id": r.user_id,
            "user_name": info["name"],
            "email": info["email"],
            "role": info["role"],
            "total_queries": r.total_queries,
            "total_tokens": int(r.total_tokens or 0),
            "last_used": r.last_used.isoformat() if r.last_used else None,
        })

    return {
        "period": f"{target_year}-{target_month:02d}",
        "company_queries_used": company_usage.queries_used if company_usage else 0,
        "company_queries_limit": company_usage.total_limit if company_usage else 0,
        "company_queries_remaining": company_usage.remaining_queries if company_usage else 0,
        "total_tokens_this_month": sum(u["total_tokens"] for u in user_stats),
        "users": user_stats,
    }


@router.get("/usage/summary", summary="Company AI Usage Summary (Admin only)")
async def get_company_ai_usage_summary(
    months: int = Query(6, ge=1, le=12, description="Number of past months to include"),
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session),
):
    """
    Admin only. Returns a month-by-month AI usage summary for the company.
    Useful for charting usage trends on the frontend.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    now = datetime.utcnow()

    # Build list of (year, month) pairs going back N months
    periods = []
    y, m = now.year, now.month
    for _ in range(months):
        periods.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1

    result = []
    for y, m in reversed(periods):
        company_usage = db.query(CompanyAIUsage).filter(
            CompanyAIUsage.company_id == current_user.company_id,
            CompanyAIUsage.year == y,
            CompanyAIUsage.month == m,
        ).first()

        token_total = db.query(func.sum(AIUsage.tokens_used)).filter(
            AIUsage.company_id == current_user.company_id,
            func.extract("year", AIUsage.created_at) == y,
            func.extract("month", AIUsage.created_at) == m,
        ).scalar() or 0

        unique_users = db.query(func.count(func.distinct(AIUsage.user_id))).filter(
            AIUsage.company_id == current_user.company_id,
            func.extract("year", AIUsage.created_at) == y,
            func.extract("month", AIUsage.created_at) == m,
        ).scalar() or 0

        result.append({
            "period": f"{y}-{m:02d}",
            "year": y,
            "month": m,
            "queries_used": company_usage.queries_used if company_usage else 0,
            "queries_limit": company_usage.total_limit if company_usage else 0,
            "tokens_used": int(token_total),
            "active_users": unique_users,
        })

    return {
        "company_id": current_user.company_id,
        "months_included": months,
        "history": result,
    }
