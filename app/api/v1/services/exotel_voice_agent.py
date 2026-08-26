"""
Exotel AgentStream ↔ OpenAI Realtime (GA) voice bridge for Dhiora inbound calls.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import struct
from typing import Any, Optional

import websockets
from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.api.v1.services.exotel_call_service import ExotelCallService, call_session_store

logger = logging.getLogger(__name__)


def _upsample_pcm16(pcm_bytes: bytes, source_rate: int, target_rate: int) -> bytes:
    if source_rate == target_rate or not pcm_bytes:
        return pcm_bytes
    ratio = target_rate // source_rate
    if ratio <= 1:
        return pcm_bytes
    sample_count = len(pcm_bytes) // 2
    samples = struct.unpack(f"<{sample_count}h", pcm_bytes)
    upsampled = []
    for sample in samples:
        upsampled.extend([sample] * ratio)
    return struct.pack(f"<{len(upsampled)}h", *upsampled)


def _downsample_pcm16(pcm_bytes: bytes, source_rate: int, target_rate: int) -> bytes:
    if source_rate == target_rate or not pcm_bytes:
        return pcm_bytes
    ratio = source_rate // target_rate
    if ratio <= 1:
        return pcm_bytes
    sample_count = len(pcm_bytes) // 2
    samples = struct.unpack(f"<{sample_count}h", pcm_bytes)
    downsampled = samples[::ratio]
    return struct.pack(f"<{len(downsampled)}h", *downsampled)


class ExotelVoiceAgentBridge:
    OPENAI_RATE = 24000

    def __init__(self, exotel_ws: WebSocket, sample_rate: int = 8000) -> None:
        self.exotel_ws = exotel_ws
        self.sample_rate = sample_rate
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.caller_number: Optional[str] = None
        self._openai_ws: Optional[Any] = None
        self._session_ready = asyncio.Event()

    async def run(self) -> None:
        if not settings.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY missing — closing Exotel stream")
            await self.exotel_ws.close(code=1011)
            return

        model = settings.EXOTEL_OPENAI_REALTIME_MODEL or "gpt-realtime"
        url = f"wss://api.openai.com/v1/realtime?model={model}"
        # GA Realtime: Authorization only — do NOT send OpenAI-Beta: realtime=v1
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        }

        logger.info("Connecting OpenAI Realtime GA model=%s", model)
        async with websockets.connect(url, additional_headers=headers, max_size=10 * 1024 * 1024) as openai_ws:
            self._openai_ws = openai_ws
            await asyncio.gather(
                self._forward_exotel_to_openai(),
                self._forward_openai_to_exotel(),
            )

    async def _configure_openai_session(self) -> None:
        assert self._openai_ws is not None
        session_update = {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "instructions": ExotelCallService.dhiora_system_prompt(self.caller_number),
                "tools": ExotelCallService.lead_capture_tools(),
                "tool_choice": "auto",
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": self.OPENAI_RATE},
                        "transcription": {"model": "gpt-4o-transcribe"},
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 700,
                        },
                    },
                    "output": {
                        "format": {"type": "audio/pcm", "rate": self.OPENAI_RATE},
                        "voice": "alloy",
                    },
                },
            },
        }
        await self._openai_ws.send(json.dumps(session_update))

    async def _send_greeting(self) -> None:
        assert self._openai_ws is not None
        greeting = {
            "type": "response.create",
            "response": {
                "instructions": (
                    "Greet the caller warmly, introduce yourself as the Dhiora assistant, "
                    "and ask how you can help them today."
                ),
            },
        }
        await self._openai_ws.send(json.dumps(greeting))

    async def _forward_exotel_to_openai(self) -> None:
        assert self._openai_ws is not None
        try:
            while True:
                message = await self.exotel_ws.receive_text()
                event = json.loads(message)
                event_type = event.get("event")

                if event_type == "connected":
                    continue

                if event_type == "start":
                    start = event.get("start") or {}
                    self.stream_sid = start.get("stream_sid") or event.get("stream_sid")
                    self.call_sid = start.get("call_sid")
                    self.caller_number = ExotelCallService.normalize_phone(start.get("from"))
                    if self.call_sid:
                        session = call_session_store.get_or_create(self.call_sid)
                        session.stream_sid = self.stream_sid
                        session.mobile_number = self.caller_number
                    logger.info(
                        "Exotel stream started call_sid=%s stream_sid=%s from=%s",
                        self.call_sid,
                        self.stream_sid,
                        self.caller_number,
                    )
                    await self._configure_openai_session()
                    await self._session_ready.wait()
                    await self._send_greeting()
                    continue

                if event_type == "media":
                    payload = (event.get("media") or {}).get("payload")
                    if not payload:
                        continue
                    pcm = base64.b64decode(payload)
                    pcm_24k = _upsample_pcm16(pcm, self.sample_rate, self.OPENAI_RATE)
                    await self._openai_ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(pcm_24k).decode("ascii"),
                    }))
                    continue

                if event_type == "stop":
                    logger.info("Exotel stream stop for call %s", self.call_sid)
                    break
        except WebSocketDisconnect:
            logger.info("Exotel WebSocket disconnected for call %s", self.call_sid)
        except Exception as exc:
            logger.error("Exotel→OpenAI bridge error: %s", exc, exc_info=True)

    async def _forward_openai_to_exotel(self) -> None:
        assert self._openai_ws is not None
        try:
            async for message in self._openai_ws:
                event = json.loads(message)
                event_type = event.get("type")

                if event_type in {"session.created", "session.updated"}:
                    self._session_ready.set()
                    logger.info("OpenAI Realtime session ready: %s", event_type)
                    continue

                if event_type in {"response.output_audio.delta", "response.audio.delta"}:
                    delta = event.get("delta")
                    if delta and self.stream_sid:
                        pcm_24k = base64.b64decode(delta)
                        pcm_out = _downsample_pcm16(pcm_24k, self.OPENAI_RATE, self.sample_rate)
                        # Exotel expects chunk sizes that are multiples of 320 bytes
                        if len(pcm_out) >= 320:
                            await self.exotel_ws.send_json({
                                "event": "media",
                                "stream_sid": self.stream_sid,
                                "media": {"payload": base64.b64encode(pcm_out).decode("ascii")},
                            })
                    continue

                if event_type in {
                    "conversation.item.input_audio_transcription.completed",
                    "response.output_audio_transcript.done",
                    "response.audio_transcript.done",
                }:
                    text = event.get("transcript") or ""
                    if text and self.call_sid:
                        session = call_session_store.get_or_create(self.call_sid)
                        session.transcript_parts.append(text)
                    continue

                if event_type == "response.function_call_arguments.done":
                    await self._handle_function_call(event)
                    continue

                if event_type == "error":
                    logger.error("OpenAI Realtime error: %s", event)
        except Exception as exc:
            logger.error("OpenAI→Exotel bridge error: %s", exc, exc_info=True)
            self._session_ready.set()

    async def _handle_function_call(self, event: dict[str, Any]) -> None:
        if not self.call_sid or not self._openai_ws:
            return
        name = event.get("name")
        if name != "save_lead_details":
            return
        raw_args = event.get("arguments") or "{}"
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError:
            args = {}
        call_session_store.save_lead_fields(
            self.call_sid,
            name=args.get("name"),
            email=args.get("email"),
            requirement=args.get("requirement"),
        )
        call_id = event.get("call_id")
        if call_id:
            await self._openai_ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps({"status": "saved"}),
                },
            }))
            await self._openai_ws.send(json.dumps({"type": "response.create"}))


async def handle_exotel_voice_stream(websocket: WebSocket, sample_rate: int = 8000) -> None:
    await websocket.accept()
    bridge = ExotelVoiceAgentBridge(websocket, sample_rate=sample_rate)
    try:
        await bridge.run()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("Exotel voice stream failed: %s", exc, exc_info=True)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
