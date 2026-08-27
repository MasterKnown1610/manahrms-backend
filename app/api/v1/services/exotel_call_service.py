"""
Exotel inbound call service — Dhiora voice agent sessions and lead creation.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.api.v1.models.lead_model import Lead, ProjectStatus
from app.api.v1.schemas.lead_schema import LeadCreate

logger = logging.getLogger(__name__)

DHIORA_DEFAULT_KNOWLEDGE = """
Dhiora is an all-in-one business operating platform that helps companies manage HR, operations,
sales, and customer relationships from a single system.

Key capabilities:
- HRMS: employee records, attendance, leave, shifts, payroll-ready data
- CRM & Leads: track prospects, clients, interactions, and sales pipeline
- Projects & Tasks: plan work, assign tasks, and monitor progress
- Inventory & Assets: stock tracking, asset assignment, maintenance logs
- Bookings & Calendar: appointments, reservations, meetings, and events
- Billing & Invoices: create invoices and track payments
- AI Assistant: built-in AI to answer business questions and automate workflows
- Industry-ready: supports hospitals, restaurants, temples, schools, events, and SMEs

Why customers choose Dhiora:
- One platform instead of many disconnected tools
- Role-based access for admins, managers, and employees
- Cloud-based — accessible from anywhere
- Customizable modules per business type
- Secure, multi-tenant architecture for organizations

Pricing & onboarding:
- Flexible plans based on company size and modules needed
- Demo and consultation available for new customers
- Implementation support for setup, migration, and training

Support:
- Email and phone support for active customers
- Help documentation and in-app AI assistant
""".strip()


@dataclass
class ExotelCallSession:
    call_sid: str
    mobile_number: Optional[str] = None
    stream_sid: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    requirement: Optional[str] = None
    recording_url: Optional[str] = None
    transcript_parts: list[str] = field(default_factory=list)
    lead_id: Optional[int] = None
    lead_created: bool = False
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

    def transcript(self) -> str:
        return "\n".join(part for part in self.transcript_parts if part).strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_sid": self.call_sid,
            "mobile_number": self.mobile_number,
            "stream_sid": self.stream_sid,
            "name": self.name,
            "email": self.email,
            "requirement": self.requirement,
            "recording_url": self.recording_url,
            "lead_id": self.lead_id,
            "lead_created": self.lead_created,
            "transcript_excerpt": self.transcript()[:500] or None,
        }


class ExotelCallSessionStore:
    """In-memory store for active/recent Exotel call sessions."""

    def __init__(self) -> None:
        self._sessions: Dict[str, ExotelCallSession] = {}

    def get_or_create(self, call_sid: str) -> ExotelCallSession:
        if call_sid not in self._sessions:
            self._sessions[call_sid] = ExotelCallSession(call_sid=call_sid)
        return self._sessions[call_sid]

    def get(self, call_sid: str) -> Optional[ExotelCallSession]:
        return self._sessions.get(call_sid)

    def save_lead_fields(
        self,
        call_sid: str,
        *,
        name: Optional[str] = None,
        email: Optional[str] = None,
        requirement: Optional[str] = None,
    ) -> ExotelCallSession:
        session = self.get_or_create(call_sid)
        if name and name.strip():
            session.name = name.strip()
        if email and email.strip():
            session.email = email.strip()
        if requirement and requirement.strip():
            session.requirement = requirement.strip()
        return session


call_session_store = ExotelCallSessionStore()


class ExotelCallService:
    @staticmethod
    def is_configured() -> bool:
        return bool(settings.OPENAI_API_KEY and settings.EXOTEL_DEFAULT_COMPANY_ID)

    @staticmethod
    def verify_webhook_token(token: Optional[str]) -> bool:
        expected = (settings.EXOTEL_WEBHOOK_TOKEN or "").strip()
        if not expected:
            return True
        return (token or "").strip() == expected

    @staticmethod
    def normalize_phone(number: Optional[str]) -> Optional[str]:
        if not number:
            return None
        cleaned = re.sub(r"[^\d+]", "", number.strip())
        if cleaned.startswith("0") and len(cleaned) == 11:
            cleaned = "+91" + cleaned[1:]
        elif cleaned.isdigit() and len(cleaned) == 10:
            cleaned = "+91" + cleaned
        return cleaned[:20]

    @staticmethod
    def dhiora_system_prompt(caller_number: Optional[str] = None) -> str:
        knowledge = (settings.DHIORA_KNOWLEDGE or DHIORA_DEFAULT_KNOWLEDGE).strip()
        caller_hint = ""
        if caller_number:
            caller_hint = f"\nThe caller's phone number is {caller_number}. You already know their mobile number — do not ask for it again."
        return f"""You are a warm, professional voice assistant for Dhiora on an inbound phone call.

Your goals:
1. Greet the caller and briefly introduce Dhiora.
2. Answer questions about Dhiora using the knowledge below — be concise (1-2 sentences per turn).
3. Collect these details before ending the call:
   - Full name
   - Email address
   - Their requirement or what they are looking for
4. When you have name and requirement, call the save_lead_details tool.
5. Confirm the details back to the caller and thank them.

Rules:
- Speak naturally for phone audio — short sentences, friendly tone.
- If the caller asks unrelated questions, politely redirect to Dhiora or lead collection.
- Do not invent pricing numbers; say the team will share a custom quote.
- Email is optional but encouraged.
{caller_hint}

Dhiora knowledge:
{knowledge}
"""

    @staticmethod
    def lead_capture_tools() -> list[dict]:
        return [
            {
                "type": "function",
                "name": "save_lead_details",
                "description": "Save caller lead details once name and requirement are collected.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Caller's full name"},
                        "email": {"type": "string", "description": "Caller's email address"},
                        "requirement": {
                            "type": "string",
                            "description": "What the caller needs or is interested in",
                        },
                    },
                    "required": ["name", "requirement"],
                },
            }
        ]

    @staticmethod
    def build_stream_url(request_base_url: str, sample_rate: int = 8000) -> str:
        public = (settings.APP_PUBLIC_URL or request_base_url).rstrip("/")
        ws_base = public.replace("https://", "wss://").replace("http://", "ws://")
        # Do not append ?token= — Exotel strips query params from Voicebot StreamUrl
        # and was failing with "bad handshake" / 403 when token was required.
        return f"{ws_base}{settings.API_V1_PREFIX}/exotel/call/stream?sample-rate={sample_rate}"

    @staticmethod
    def parse_passthru_params(params: Dict[str, Any]) -> Dict[str, Optional[str]]:
        def pick(*keys: str) -> Optional[str]:
            for key in keys:
                value = params.get(key) or params.get(key.lower()) or params.get(key.upper())
                if value is not None and str(value).strip():
                    return str(value).strip()
            return None

        return {
            "call_sid": pick("CallSid", "callsid", "call_sid"),
            "stream_sid": pick("StreamSid", "streamsid", "stream_sid"),
            "from_number": pick("From", "CallFrom", "from"),
            "to_number": pick("To", "CallTo", "to"),
            "recording_url": pick("RecordingUrl", "recordingurl", "Stream[RecordingUrl]"),
            "status": pick("Status", "status", "Stream[Status]"),
        }

    @staticmethod
    def extract_lead_from_transcript(transcript: str) -> Dict[str, Optional[str]]:
        if not transcript.strip() or not settings.OPENAI_API_KEY:
            return {}

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        prompt = (
            "Extract lead fields from this phone call transcript. "
            "Return JSON only with keys: name, email, requirement. "
            "Use null for missing values.\n\nTranscript:\n"
            f"{transcript[:6000]}"
        )
        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You extract structured lead data. Reply with JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            content = (response.choices[0].message.content or "").strip()
            if content.startswith("```"):
                content = content.split("```", 2)[1]
                if content.startswith("json"):
                    content = content[4:]
            data = json.loads(content)
            return {
                "name": data.get("name"),
                "email": data.get("email"),
                "requirement": data.get("requirement"),
            }
        except Exception as exc:
            logger.warning("Lead extraction from transcript failed: %s", exc)
            return {}

    @staticmethod
    def create_lead_from_call(
        db: Session,
        *,
        call_sid: str,
        mobile_number: Optional[str],
        name: Optional[str] = None,
        email: Optional[str] = None,
        requirement: Optional[str] = None,
        recording_url: Optional[str] = None,
        transcript: Optional[str] = None,
    ) -> Optional[Lead]:
        company_id = settings.EXOTEL_DEFAULT_COMPANY_ID
        if not company_id:
            logger.error("EXOTEL_DEFAULT_COMPANY_ID is not configured")
            return None

        if call_sid:
            existing = db.query(Lead).filter(Lead.exotel_call_sid == call_sid).first()
            if existing:
                return existing

        if transcript and (not name or not requirement):
            extracted = ExotelCallService.extract_lead_from_transcript(transcript)
            name = name or extracted.get("name")
            email = email or extracted.get("email")
            requirement = requirement or extracted.get("requirement")

        safe_name = (name or "").strip() or "Inbound Caller"
        safe_mobile = ExotelCallService.normalize_phone(mobile_number)
        safe_email = (email or "").strip() or None
        safe_requirement = (requirement or "").strip() or None

        if safe_email and "@" not in safe_email:
            safe_email = None

        lead_data = LeadCreate(
            name=safe_name[:200],
            email=safe_email,
            mobile_number=safe_mobile,
            requirement_description=safe_requirement,
            requirements=safe_requirement,
            project_status=ProjectStatus.NEW,
        )

        lead = Lead(
            company_id=company_id,
            source="exotel_inbound",
            exotel_call_sid=call_sid or None,
            call_recording_url=recording_url,
            **lead_data.model_dump(exclude={"project_status"}),
            project_status=ProjectStatus.NEW,
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        logger.info("Created lead %s from Exotel call %s", lead.id, call_sid)
        return lead

    @staticmethod
    def finalize_call_and_create_lead(
        db: Session,
        params: Dict[str, Any],
    ) -> Optional[Lead]:
        parsed = ExotelCallService.parse_passthru_params(params)
        call_sid = parsed.get("call_sid") or ""
        if not call_sid:
            logger.warning("Exotel complete webhook missing CallSid: %s", params)
            return None

        call_type = str(params.get("CallType") or params.get("calltype") or "").strip().lower()
        duration_raw = params.get("DialCallDuration") or params.get("dialcallduration") or "0"
        try:
            duration = int(float(str(duration_raw)))
        except (TypeError, ValueError):
            duration = 0

        session = call_session_store.get_or_create(call_sid)
        session.ended_at = datetime.utcnow()
        if parsed.get("from_number"):
            session.mobile_number = ExotelCallService.normalize_phone(parsed["from_number"])
        if parsed.get("recording_url"):
            session.recording_url = parsed["recording_url"]
        if parsed.get("stream_sid"):
            session.stream_sid = parsed["stream_sid"]

        # Voicebot never connected — only Passthru fired on a failed/attempted call
        has_voice_session = bool(session.stream_sid or session.transcript() or session.name or session.requirement)
        if call_type == "call-attempt" and duration <= 0 and not has_voice_session:
            logger.warning(
                "Skipping lead for CallSid=%s — Voicebot did not connect "
                "(CallType=call-attempt, duration=%s). Check Voicebot WSS URL in Exotel.",
                call_sid,
                duration,
            )
            return None

        if session.lead_created and session.lead_id:
            return db.query(Lead).filter(Lead.id == session.lead_id).first()

        lead = ExotelCallService.create_lead_from_call(
            db,
            call_sid=call_sid,
            mobile_number=session.mobile_number or parsed.get("from_number"),
            name=session.name,
            email=session.email,
            requirement=session.requirement,
            recording_url=session.recording_url,
            transcript=session.transcript(),
        )
        if lead:
            session.lead_created = True
            session.lead_id = lead.id
        return lead
