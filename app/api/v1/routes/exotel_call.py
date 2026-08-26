"""
Exotel inbound call API — Dhiora voice agent and post-call lead creation.

Configure Exotel flow for number 08047361154:
  1. Voicebot Applet → dynamic URL: GET {APP_PUBLIC_URL}/api/v1/exotel/call/stream-url
  2. Passthru Applet (async) → GET/POST {APP_PUBLIC_URL}/api/v1/exotel/call/complete?token=...
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, Request, WebSocket, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_database_session
from app.api.v1.schemas.exotel_call_schema import (
    ExotelStreamUrlResponse,
    ExotelCallCompleteResponse,
    ExotelCallSessionResponse,
)
from app.api.v1.services.exotel_call_service import ExotelCallService, call_session_store
from app.api.v1.services.exotel_voice_agent import handle_exotel_voice_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exotel/call", tags=["Exotel Call"])


def _verify_exotel_token(token: Optional[str] = Query(None)) -> None:
    if not ExotelCallService.verify_webhook_token(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Exotel webhook token")


async def _read_exotel_params(request: Request) -> Dict[str, Any]:
    params: Dict[str, Any] = dict(request.query_params)
    try:
        form = await request.form()
        params.update({k: v for k, v in form.items()})
    except Exception:
        pass
    if request.method in {"POST", "PUT", "PATCH"}:
        try:
            body = await request.json()
            if isinstance(body, dict):
                params.update(body)
        except Exception:
            pass
    return params


@router.api_route("/stream-url", methods=["GET", "POST"], response_model=ExotelStreamUrlResponse)
async def resolve_exotel_stream_url(
    request: Request,
    sample_rate: int = Query(8000, ge=8000, le=24000),
    token: Optional[str] = Query(None),
):
    """
    Dynamic WebSocket URL resolver for Exotel Voicebot Applet.
    Point the Voicebot applet to this HTTPS URL, OR paste the returned wss:// URL directly.
    """
    _verify_exotel_token(token)
    # Prefer APP_PUBLIC_URL (tunnel) so Exotel gets a reachable public wss URL
    base = (settings.APP_PUBLIC_URL or str(request.base_url)).rstrip("/")
    wss_url = ExotelCallService.build_stream_url(base, sample_rate)
    logger.info("Exotel stream-url resolved → %s (from %s)", wss_url, request.client.host if request.client else "?")
    return ExotelStreamUrlResponse(url=wss_url)


@router.websocket("/stream")
async def exotel_voice_stream(
    websocket: WebSocket,
    sample_rate: int = Query(8000, ge=8000, le=24000),
    token: Optional[str] = Query(None),
):
    """
    Bidirectional AgentStream WebSocket for Exotel Voicebot.
    Bridges caller audio to OpenAI Realtime Dhiora agent.

    Note: Exotel often strips query-string params from the Voicebot WSS URL
    (see Stream[StreamUrl] without ?token=). So missing token is allowed here;
    HTTP stream-url / complete webhooks still enforce the token.
    """
    client = websocket.client.host if websocket.client else "?"
    logger.info(
        "Exotel Voicebot WebSocket connecting from %s sample_rate=%s token_present=%s",
        client,
        sample_rate,
        bool(token),
    )
    # Only reject if a token WAS sent and it is wrong.
    # Exotel frequently connects to bare /stream with no query string.
    expected = (settings.EXOTEL_WEBHOOK_TOKEN or "").strip()
    if token is not None and expected and token.strip() != expected:
        logger.warning("Exotel Voicebot WebSocket rejected — bad token from %s", client)
        await websocket.close(code=1008)
        return
    if not token and expected:
        logger.info(
            "Exotel Voicebot WebSocket accepted without query token "
            "(Exotel often strips ?token= from StreamUrl)"
        )
    await handle_exotel_voice_stream(websocket, sample_rate=sample_rate)


@router.api_route("/complete", methods=["GET", "POST"], response_model=ExotelCallCompleteResponse)
async def exotel_call_complete(
    request: Request,
    db: Session = Depends(get_database_session),
    token: Optional[str] = Query(None),
):
    """
    Passthru webhook after Voicebot ends — creates a lead from the call session.
    Configure as async Passthru after the Voicebot applet in Exotel flow.
    """
    _verify_exotel_token(token)
    params = await _read_exotel_params(request)
    logger.info("Exotel call complete webhook: %s", {k: params.get(k) for k in list(params)[:12]})

    lead = ExotelCallService.finalize_call_and_create_lead(db, params)
    if not lead:
        return ExotelCallCompleteResponse(
            status="ignored",
            message=(
                "No lead created. If CallType=call-attempt, Voicebot did not connect — "
                "paste the WSS URL into the Voicebot applet (not the /complete URL)."
            ),
        )
    return ExotelCallCompleteResponse(
        status="success",
        lead_id=lead.id,
        call_sid=lead.exotel_call_sid,
        message="Lead created from inbound call",
    )


@router.get("/session/{call_sid}", response_model=ExotelCallSessionResponse)
async def get_exotel_call_session(call_sid: str, token: Optional[str] = Query(None)):
    """Debug/helper endpoint to inspect an in-memory call session."""
    _verify_exotel_token(token)
    session = call_session_store.get(call_sid)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call session not found")
    return ExotelCallSessionResponse(**session.to_dict())


@router.get("/config")
async def get_exotel_call_config():
    """Public setup info for Exotel dashboard configuration (no secrets)."""
    public_base = (settings.APP_PUBLIC_URL or "https://your-domain.com").rstrip("/")
    token = (settings.EXOTEL_WEBHOOK_TOKEN or "").strip()
    token_q = f"?token={token}" if token else ""
    wss_base = public_base.replace("https://", "wss://").replace("http://", "ws://")
    return {
        "inbound_number": settings.EXOTEL_INBOUND_NUMBER,
        "configured": ExotelCallService.is_configured(),
        "company_id": settings.EXOTEL_DEFAULT_COMPANY_ID,
        "paste_into_voicebot_applet": f"{wss_base}{settings.API_V1_PREFIX}/exotel/call/stream",
        "or_use_https_resolver": f"{public_base}{settings.API_V1_PREFIX}/exotel/call/stream-url{token_q}",
        "paste_into_passthru_applet": f"{public_base}{settings.API_V1_PREFIX}/exotel/call/complete{token_q}",
        "important": (
            "Paste the bare WSS /stream URL into Voicebot (no ?token=). "
            "Exotel strips query params and was getting 403 bad handshake. "
            "Passthru still uses ?token=. Flow: Voicebot → Passthru."
        ),
        "success_log_line": "Exotel Voicebot WebSocket connecting",
    }
