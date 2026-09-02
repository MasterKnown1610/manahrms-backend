"""
Agentic AI Service for HRMS
Uses OpenAI Function Calling to perform real actions inside the HRMS system.
Role-based tool access: admins get management tools, employees get self-service tools.
Multi-turn agentic loop: keeps calling tools until the task is complete.
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from openai import OpenAI
from datetime import datetime, date
import html as html_lib
import json
import logging
import re

from app.core.config import settings
from app.api.v1.models.user_model import User, UserRole
from app.api.v1.models.employee_model import Employee
from app.api.v1.models.task_model import Task, TaskStatus, TaskPriority
from app.api.v1.models.department_model import Department
from app.api.v1.models.attendance_model import Attendance
from app.api.v1.models.leave_model import LeaveRequest, LeaveType, LeaveStatus, LeaveBalance
from app.api.v1.models.meeting_model import Meeting, MeetingParticipant
from app.api.v1.models.project_model import Project
from app.api.v1.models.company_profile_model import CompanyProfile, IndustryType
from app.api.v1.models.inventory_model import InventoryItem, InventoryTransaction, TransactionType
from app.api.v1.models.crm_model import Client, ClientInteraction
from app.api.v1.models.booking_model import Booking, BookingResource, BookingStatus
from app.api.v1.models.billing_ops_model import Invoice, InvoiceStatus
from app.api.v1.models.shift_model import Shift, ShiftAssignment
from app.api.v1.models.donation_model import Donation

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 8  # increased for multi-step agentic tasks across new modules

_RICH_TEXT_TAG_RE = re.compile(
    r"</?(?:p|div|ul|ol|li|h[1-6]|br|strong|em|b|i|span|blockquote)\b",
    re.IGNORECASE,
)


def format_task_description_for_rich_text(description: Optional[str]) -> Optional[str]:
    """
    Normalize an AI task description into HTML that a rich text editor can load.
    Used only for AI task creation.
    """
    if description is None:
        return None
    text = description.strip()
    if not text:
        return None
    if _RICH_TEXT_TAG_RE.search(text):
        return text

    def inline(value: str) -> str:
        escaped = html_lib.escape(value)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"__(.+?)__", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", escaped)
        return escaped

    blocks: List[str] = []
    list_items: List[str] = []
    list_type: Optional[str] = None

    def flush_list() -> None:
        nonlocal list_items, list_type
        if list_items and list_type:
            items = "".join(f"<li>{inline(item)}</li>" for item in list_items)
            blocks.append(f"<{list_type}>{items}</{list_type}>")
        list_items = []
        list_type = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush_list()
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            flush_list()
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            continue
        unordered = re.match(r"^[-*]\s+(.+)$", line)
        if unordered:
            if list_type != "ul":
                flush_list()
                list_type = "ul"
            list_items.append(unordered.group(1))
            continue
        ordered = re.match(r"^\d+[.)]\s+(.+)$", line)
        if ordered:
            if list_type != "ol":
                flush_list()
                list_type = "ol"
            list_items.append(ordered.group(1))
            continue
        flush_list()
        blocks.append(f"<p>{inline(line)}</p>")

    flush_list()
    return "".join(blocks) if blocks else f"<p>{inline(text)}</p>"


# ── Industry context helpers ──────────────────────────────────────────────────

_INDUSTRY_CONTEXT = {
    IndustryType.HOSPITAL: (
        "This is a hospital/clinic. Use medical terminology. "
        "Clients are 'patients'. Bookings are 'appointments'. "
        "Inventory items are medicines/supplies. Shifts are doctor/nurse shifts. "
        "When asked about scheduling, think doctor slots and OPD appointments."
    ),
    IndustryType.RESTAURANT: (
        "This is a restaurant/food business. "
        "Clients are 'customers'. Bookings are 'table reservations'. "
        "Inventory items are ingredients/raw materials. "
        "Shifts are kitchen/floor staff shifts. "
        "When asked about stock, think ingredient quantities and reorder levels."
    ),
    IndustryType.TEMPLE: (
        "This is a temple/religious organization. "
        "Clients are 'devotees' or 'donors'. "
        "Bookings are 'pooja slots' or 'event registrations'. "
        "Inventory is prasad/flowers/ritual supplies. "
        "Donations module is key here — track donor info and receipts."
    ),
    IndustryType.SCHOOL: (
        "This is a school/educational institution. "
        "Clients are 'students' or 'parents'. "
        "Bookings are 'classroom/lab reservations'. "
        "Inventory is stationery/lab equipment. "
        "Employees are teachers and administrative staff."
    ),
    IndustryType.EVENT: (
        "This is an event management company. "
        "Clients are 'event clients'. Bookings are 'event bookings' or 'venue reservations'. "
        "Inventory is AV equipment, decorations, logistics. "
        "Invoice clients per event. CRM tracks event requirements and feedback."
    ),
    IndustryType.SME: (
        "This is a small/medium enterprise. "
        "Clients are 'customers' or 'prospects'. "
        "Use CRM for sales pipeline. Invoice for billing. "
        "Inventory for office/product stock management."
    ),
    IndustryType.GENERIC: "",
}

# Kept empty — the no-fabrication rule lives in the system prompt once, not repeated per tool.
_TOOL_USE_REAL_DATA_ONLY = ""


# ─── Tool Definitions ─────────────────────────────────────────────────────────

ADMIN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_employee",
            "description": "Create a new employee (generates employee code). Confirm before calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string", "description": "Optional; defaults to first_name if omitted"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "position": {"type": "string"},
                    "department_id": {"type": "integer"},
                    "hire_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "initial_password": {"type": "string", "description": "Min 6 chars"},
                    "salary": {"type": "number"},
                    "address": {"type": "string"},
                },
                "required": ["first_name", "email", "hire_date", "initial_password"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_employees",
            "description": "List employees with optional filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {"type": "string", "description": "Search by name, email, or employee code"},
                    "department_id": {"type": "integer"},
                    "is_active": {"type": "boolean"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_employee_by_name",
            "description": "Find an employee by name or email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name or email to search"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a task and optionally assign it. Confirm before calling. Always generate a rich-text HTML description for the editor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {
                        "type": "string",
                        "description": (
                            "Required rich-text HTML for the task editor. "
                            "Use only these tags: p, h2, h3, ul, ol, li, strong, em, br. "
                            "Always include a short <p> overview, then optional <h3> sections "
                            "and <ul>/<ol> for steps or acceptance criteria. Do not use markdown."
                        ),
                    },
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "due_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "assigned_to_employee_id": {"type": "integer"},
                    "project_id": {"type": "integer"},
                },
                "required": ["title", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "List company tasks with optional filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["open", "in_progress", "closed"]},
                    "assigned_to_employee_id": {"type": "integer"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "Update a task's fields. Confirm before calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer"},
                    "status": {"type": "string", "enum": ["open", "in_progress", "closed"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "due_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "assigned_to_employee_id": {"type": "integer"},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_meeting",
            "description": "Schedule a meeting with participants. Confirm before calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "start_time": {"type": "string", "description": "ISO datetime e.g. 2025-04-15T10:00:00"},
                    "end_time": {"type": "string", "description": "ISO datetime"},
                    "timezone": {"type": "string", "description": "IANA zone; use Asia/Kolkata for IST"},
                    "meeting_link": {"type": "string"},
                    "meeting_platform": {"type": "string", "enum": ["GOOGLE_MEET", "ZOOM", "MS_TEAMS", "OTHER"]},
                    "participant_user_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["title", "start_time", "end_time", "meeting_link", "meeting_platform"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_upcoming_meetings",
            "description": "List upcoming company meetings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_departments",
            "description": "List all active departments.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_department",
            "description": "Create a new department. Confirm before calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_attendance_report",
            "description": "Get attendance records for a date or employee.",
            "parameters": {
                "type": "object",
                "properties": {
                    "attendance_date": {"type": "string", "description": "YYYY-MM-DD (default: today)"},
                    "employee_id": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_pending_leave_requests",
            "description": "List all pending leave requests awaiting admin approval.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "approve_reject_leave",
            "description": "Approve or reject a leave request. Confirm before calling. Use ID from list_pending_leave_requests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "leave_request_id": {"type": "integer"},
                    "action": {"type": "string", "enum": ["approve", "reject"]},
                    "rejection_reason": {"type": "string"},
                },
                "required": ["leave_request_id", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_leave_types",
            "description": "List all configured leave types with IDs.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_projects",
            "description": "List all active projects.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_summary",
            "description": "Get key company metrics: employee count, tasks, attendance today.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ── Inventory tools ───────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "list_inventory_items",
            "description": "List inventory items. For restaurant: ingredients. For hospital: medicines. For temple: prasad/ritual supplies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {"type": "string"},
                    "low_stock_only": {"type": "boolean", "description": "Only return items below reorder level"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_stock",
            "description": "Add stock to an inventory item (stock_in). Confirm before calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer"},
                    "quantity": {"type": "number"},
                    "notes": {"type": "string"},
                },
                "required": ["item_id", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consume_stock",
            "description": "Consume/use inventory stock (stock_out). Confirm before calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer"},
                    "quantity": {"type": "number"},
                    "notes": {"type": "string"},
                },
                "required": ["item_id", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_low_stock_alerts",
            "description": "Get list of items that are below their reorder level.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ── CRM tools ─────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "list_clients",
            "description": "List clients/patients/customers/devotees. Use industry terminology.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {"type": "string"},
                    "industry_label": {"type": "string", "description": "Filter by label e.g. 'patient', 'customer'"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_client",
            "description": "Add a new client/patient/customer. Confirm before calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "email": {"type": "string"},
                    "industry_label": {"type": "string", "description": "e.g. 'patient', 'customer', 'devotee'"},
                    "notes": {"type": "string"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_client_interaction",
            "description": "Log a note, call, or visit for a client. Confirm before calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_id": {"type": "integer"},
                    "interaction_type": {"type": "string", "enum": ["call", "visit", "email", "note", "appointment"]},
                    "subject": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["client_id", "notes"],
            },
        },
    },
    # ── Booking tools ─────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "list_bookings",
            "description": "List bookings/appointments/reservations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "confirmed", "cancelled", "completed", "no_show"]},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_booking",
            "description": "Create a booking/appointment/reservation. Confirm before calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "start_datetime": {"type": "string", "description": "ISO datetime e.g. 2025-04-15T10:00:00"},
                    "end_datetime": {"type": "string", "description": "ISO datetime"},
                    "client_id": {"type": "integer"},
                    "employee_id": {"type": "integer", "description": "Assigned doctor/chef/staff"},
                    "resource_id": {"type": "integer", "description": "Room/table/venue ID"},
                    "notes": {"type": "string"},
                },
                "required": ["title", "start_datetime", "end_datetime"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_booking_resources",
            "description": "List available bookable resources (rooms, tables, venues, doctor slots).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ── Invoice tools ─────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "list_invoices",
            "description": "List invoices with optional status filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["draft", "sent", "paid", "overdue", "cancelled"]},
                },
                "required": [],
            },
        },
    },
    # ── Shift tools ───────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "list_shifts",
            "description": "List all shift patterns (Morning, Night, Evening etc.).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_shift_assignments",
            "description": "List current employee shift assignments.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ── Donation tools ────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "list_donations",
            "description": "List donations (for temples/charitable organizations).",
            "parameters": {
                "type": "object",
                "properties": {
                    "purpose": {"type": "string"},
                    "donor_name": {"type": "string"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_donation",
            "description": "Record a donation. Confirm before calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "donor_name": {"type": "string"},
                    "amount": {"type": "number"},
                    "purpose": {"type": "string"},
                    "donation_mode": {"type": "string", "enum": ["cash", "online", "cheque", "demand_draft", "upi"]},
                    "donor_phone": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["donor_name", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_donation_summary",
            "description": "Get total donation count and amount collected.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

EMPLOYEE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "punch_in",
            "description": "Mark attendance punch-in for today. Confirm before calling.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "punch_out",
            "description": "Mark attendance punch-out for today. Confirm before calling.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_tasks",
            "description": "Get tasks assigned to me.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["open", "in_progress", "closed"]},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_attendance",
            "description": "Get my attendance records for a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "YYYY-MM-DD (default: first of month)"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD (default: today)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_for_leave",
            "description": "Apply for leave. Confirm before calling. Get leave_type_id from list_leave_types.",
            "parameters": {
                "type": "object",
                "properties": {
                    "leave_type_id": {"type": "integer"},
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "reason": {"type": "string"},
                },
                "required": ["leave_type_id", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_leave_balance",
            "description": "Check my remaining leave balance for all leave types.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_leave_types",
            "description": "List all configured leave types with IDs.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_profile",
            "description": "Get my employee profile information.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_my_task_status",
            "description": "Update status of a task assigned to me. Confirm before calling. Use task_id from get_my_tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer"},
                    "status": {"type": "string", "enum": ["in_progress", "closed"]},
                },
                "required": ["task_id", "status"],
            },
        },
    },
]


# ─── Main Service ─────────────────────────────────────────────────────────────

class AgenticAIService:
    """
    Agentic AI that can perform real HRMS actions via OpenAI function calling.
    - Admins: manage employees, tasks, meetings, leaves, departments
    - Employees: punch in/out, view tasks, apply leaves, check balance
    """

    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured.")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    def _get_tools(self, role: UserRole) -> List[dict]:
        if role == UserRole.ADMIN:
            return ADMIN_TOOLS
        return EMPLOYEE_TOOLS

    def _get_industry_context(self, db: Session, company_id: int) -> str:
        profile = db.query(CompanyProfile).filter(CompanyProfile.company_id == company_id).first()
        if not profile:
            return ""
        return _INDUSTRY_CONTEXT.get(profile.industry_type, "")

    def _system_prompt(self, user: User, role: UserRole, db: Optional[Session] = None) -> str:
        today = date.today().isoformat()
        role_desc = "company admin" if role == UserRole.ADMIN else "employee"
        if role == UserRole.ADMIN:
            confirm_tools = (
                "create_employee, create_task, update_task, schedule_meeting, create_department, "
                "approve_reject_leave, add_stock, consume_stock, add_client, log_client_interaction, "
                "create_booking, record_donation"
            )
        else:
            confirm_tools = "punch_in, punch_out, apply_for_leave, update_my_task_status, consume_stock, create_booking"

        industry_ctx = ""
        if db:
            industry_ctx = self._get_industry_context(db, user.company_id)

        return f"""You are an intelligent Business OS assistant for {user.full_name} ({role_desc}). Today: {today}.

{f"INDUSTRY CONTEXT: {industry_ctx}" if industry_ctx else ""}

CAPABILITIES: You help with HR (employees, attendance, leaves, tasks, meetings) AND business operations (inventory, assets, CRM clients/patients/customers, bookings/appointments, invoices, shifts, donations). Adapt your language to the industry context above.

RULES:
1. Never fabricate names, emails, IDs, dates, or any data. Use only what the user typed or tool results returned.
2. Mutating tools ({confirm_tools}) require confirmation:
   a. Use read-only tools first to resolve names/IDs.
   b. Ask for missing required info — never invent.
   c. Summarize the action with real values; ask "Reply yes to proceed or no to cancel."
   d. Call the mutating tool ONLY after explicit confirmation.
   e. On success, reply briefly with key details (never echo passwords).
3. Security: Never repeat passwords.
4. Be concise and professional. Use industry-appropriate terminology.
5. When calling create_task, always generate description as rich-text HTML for a rich text editor.
   Use only: p, h2, h3, ul, ol, li, strong, em, br.
   Example: "<p>Fix the login timeout on employee portal.</p><h3>Steps</h3><ul><li>Reproduce the issue</li><li>Patch session expiry</li></ul><h3>Acceptance criteria</h3><ol><li>Users stay signed in for the token lifetime</li></ol>"
   Never use markdown for create_task description."""

    # ─── Tool Executors ───────────────────────────────────────────────────────

    def _run_tool(self, name: str, args: dict, db: Session, user: User) -> Any:
        """Dispatch tool call to the appropriate handler."""
        handlers = {
            # Admin tools
            "create_employee": self._tool_create_employee,
            "list_employees": self._tool_list_employees,
            "get_employee_by_name": self._tool_get_employee_by_name,
            "create_task": self._tool_create_task,
            "list_tasks": self._tool_list_tasks,
            "update_task": self._tool_update_task,
            "schedule_meeting": self._tool_schedule_meeting,
            "list_upcoming_meetings": self._tool_list_upcoming_meetings,
            "list_departments": self._tool_list_departments,
            "create_department": self._tool_create_department,
            "get_attendance_report": self._tool_get_attendance_report,
            "list_pending_leave_requests": self._tool_list_pending_leave_requests,
            "approve_reject_leave": self._tool_approve_reject_leave,
            "list_leave_types": self._tool_list_leave_types,
            "list_projects": self._tool_list_projects,
            "get_dashboard_summary": self._tool_get_dashboard_summary,
            # Employee tools
            "punch_in": self._tool_punch_in,
            "punch_out": self._tool_punch_out,
            "get_my_tasks": self._tool_get_my_tasks,
            "get_my_attendance": self._tool_get_my_attendance,
            "apply_for_leave": self._tool_apply_for_leave,
            "get_my_leave_balance": self._tool_get_my_leave_balance,
            "get_my_profile": self._tool_get_my_profile,
            "update_my_task_status": self._tool_update_my_task_status,
            # New Business OS tools
            "list_inventory_items": self._tool_list_inventory_items,
            "add_stock": self._tool_add_stock,
            "consume_stock": self._tool_consume_stock,
            "get_low_stock_alerts": self._tool_get_low_stock_alerts,
            "list_clients": self._tool_list_clients,
            "add_client": self._tool_add_client,
            "log_client_interaction": self._tool_log_client_interaction,
            "list_bookings": self._tool_list_bookings,
            "create_booking": self._tool_create_booking,
            "list_booking_resources": self._tool_list_booking_resources,
            "list_invoices": self._tool_list_invoices,
            "list_shifts": self._tool_list_shifts,
            "list_shift_assignments": self._tool_list_shift_assignments,
            "list_donations": self._tool_list_donations,
            "record_donation": self._tool_record_donation,
            "get_donation_summary": self._tool_get_donation_summary,
        }
        handler = handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        try:
            return handler(args, db, user)
        except Exception as e:
            logger.error(f"Tool '{name}' failed: {e}")
            return {"error": str(e)}

    # ── Admin tool implementations ───────────────────────────────────────────

    def _tool_create_employee(self, args: dict, db: Session, user: User) -> dict:
        from app.api.v1.services.employee_service import EmployeeService
        from app.api.v1.schemas.employee_schema import EmployeeCreate
        from app.api.v1.models.employee_model import Gender

        last_name = (args.get("last_name") or "").strip() or args["first_name"].strip()
        data = EmployeeCreate(
            first_name=args["first_name"],
            last_name=last_name,
            email=args["email"],
            phone=args.get("phone"),
            position=args.get("position"),
            department_id=args.get("department_id"),
            hire_date=date.fromisoformat(args["hire_date"]),
            initial_password=args["initial_password"],
            salary=args.get("salary"),
            address=args.get("address"),
        )
        employee, login_user, _ = EmployeeService.create_employee_with_credentials(
            db, data, user.company_id
        )
        # Do not return password to the model — avoids echoing secrets in chat/logs.
        return {
            "success": True,
            "employee_id": employee.id,
            "employee_code": employee.employee_code,
            "full_name": f"{employee.first_name} {employee.last_name}",
            "email": employee.email,
            "username": login_user.username,
        }

    def _tool_list_employees(self, args: dict, db: Session, user: User) -> dict:
        from sqlalchemy import or_
        query = db.query(Employee).filter(
            Employee.company_id == user.company_id,
            Employee.deleted_at.is_(None),
        )
        is_active = args.get("is_active", True)
        if is_active is not None:
            query = query.filter(Employee.is_active == is_active)
        search = args.get("search")
        if search:
            query = query.filter(
                or_(
                    Employee.first_name.ilike(f"%{search}%"),
                    Employee.last_name.ilike(f"%{search}%"),
                    Employee.email.ilike(f"%{search}%"),
                    Employee.employee_code.ilike(f"%{search}%"),
                )
            )
        dept_id = args.get("department_id")
        if dept_id:
            query = query.filter(Employee.department_id == dept_id)

        employees = query.order_by(Employee.first_name).limit(20).all()
        return {
            "total": len(employees),
            "employees": [
                {
                    "id": e.id,
                    "employee_code": e.employee_code,
                    "full_name": f"{e.first_name} {e.last_name}",
                    "email": e.email,
                    "position": e.position,
                    "department": e.department.name if e.department else None,
                }
                for e in employees
            ],
        }

    def _tool_get_employee_by_name(self, args: dict, db: Session, user: User) -> dict:
        from sqlalchemy import or_
        search = args["name"]
        employees = db.query(Employee).filter(
            Employee.company_id == user.company_id,
            Employee.deleted_at.is_(None),
            or_(
                Employee.first_name.ilike(f"%{search}%"),
                Employee.last_name.ilike(f"%{search}%"),
                Employee.email.ilike(f"%{search}%"),
            ),
        ).limit(5).all()

        if not employees:
            return {"found": False, "message": f"No employee found matching '{search}'"}
        return {
            "found": True,
            "employees": [
                {
                    "id": e.id,
                    "employee_code": e.employee_code,
                    "full_name": f"{e.first_name} {e.last_name}",
                    "email": e.email,
                    "position": e.position,
                    "department": e.department.name if e.department else None,
                    "phone": e.phone,
                    "is_active": e.is_active,
                }
                for e in employees
            ],
        }

    def _tool_create_task(self, args: dict, db: Session, user: User) -> dict:
        from app.api.v1.services.task_service import TaskService
        from app.api.v1.schemas.task_schema import TaskCreate

        due_date = None
        if args.get("due_date"):
            due_date = date.fromisoformat(args["due_date"])

        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
        }
        description = format_task_description_for_rich_text(args.get("description"))
        if not description:
            description = f"<p>{html_lib.escape(args['title'])}</p>"

        data = TaskCreate(
            title=args["title"],
            description=description,
            priority=priority_map.get(args.get("priority", "medium"), TaskPriority.MEDIUM),
            due_date=due_date,
            assigned_to_employee_id=args.get("assigned_to_employee_id"),
            project_id=args.get("project_id"),
        )
        task = TaskService.create_task(db, user.company_id, user.id, data)
        return {
            "success": True,
            "task_id": task.id,
            "title": task.title,
            "status": task.status.value,
            "priority": task.priority.value,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "assigned_to_employee_id": task.assigned_to_employee_id,
        }

    def _tool_list_tasks(self, args: dict, db: Session, user: User) -> dict:
        query = db.query(Task).filter(Task.company_id == user.company_id)
        if args.get("status"):
            try:
                query = query.filter(Task.status == TaskStatus(args["status"]))
            except ValueError:
                pass
        if args.get("assigned_to_employee_id"):
            query = query.filter(Task.assigned_to_employee_id == args["assigned_to_employee_id"])
        if args.get("priority"):
            try:
                query = query.filter(Task.priority == TaskPriority(args["priority"]))
            except ValueError:
                pass

        tasks = query.order_by(Task.created_at.desc()).limit(20).all()
        return {
            "total": len(tasks),
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "assigned_to": (
                        f"{t.assigned_to_employee.first_name} {t.assigned_to_employee.last_name}"
                        if t.assigned_to_employee else "Unassigned"
                    ),
                }
                for t in tasks
            ],
        }

    def _tool_update_task(self, args: dict, db: Session, user: User) -> dict:
        task = db.query(Task).filter(
            Task.id == args["task_id"],
            Task.company_id == user.company_id,
        ).first()
        if not task:
            return {"error": "Task not found"}

        if args.get("status"):
            try:
                task.status = TaskStatus(args["status"])
            except ValueError:
                pass
        if args.get("priority"):
            try:
                task.priority = TaskPriority(args["priority"])
            except ValueError:
                pass
        if args.get("title"):
            task.title = args["title"]
        if args.get("description"):
            task.description = args["description"]
        if args.get("due_date"):
            task.due_date = date.fromisoformat(args["due_date"])
        if args.get("assigned_to_employee_id") is not None:
            task.assigned_to_employee_id = args["assigned_to_employee_id"]

        task.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
        return {
            "success": True,
            "task_id": task.id,
            "title": task.title,
            "status": task.status.value,
            "priority": task.priority.value,
        }

    def _tool_schedule_meeting(self, args: dict, db: Session, user: User) -> dict:
        from app.api.v1.services.meeting_service import MeetingService
        from app.api.v1.schemas.meeting_schema import MeetingCreate
        from app.api.v1.models.meeting_model import MeetingPlatform

        platform_map = {
            "GOOGLE_MEET": MeetingPlatform.GOOGLE_MEET,
            "ZOOM": MeetingPlatform.ZOOM,
            "MS_TEAMS": MeetingPlatform.MS_TEAMS,
            "OTHER": MeetingPlatform.OTHER,
        }
        timezone = args.get("timezone", "Asia/Kolkata")
        data = MeetingCreate(
            title=args["title"],
            description=args.get("description"),
            meeting_link=args["meeting_link"],
            meeting_platform=platform_map.get(args["meeting_platform"], MeetingPlatform.OTHER),
            start_time=datetime.fromisoformat(args["start_time"]),
            end_time=datetime.fromisoformat(args["end_time"]),
            timezone=timezone,
            participants=args.get("participant_user_ids", []),
        )
        meeting = MeetingService.create_meeting(db, user.company_id, user.id, data)
        return {
            "success": True,
            "meeting_id": meeting.id,
            "title": meeting.title,
            "start_time": meeting.start_time_utc.isoformat() if meeting.start_time_utc else None,
            "end_time": meeting.end_time_utc.isoformat() if meeting.end_time_utc else None,
            "meeting_link": meeting.meeting_link,
            "platform": meeting.meeting_platform.value if meeting.meeting_platform else None,
        }

    def _tool_list_upcoming_meetings(self, args: dict, db: Session, user: User) -> dict:
        limit = args.get("limit", 10)
        now = datetime.utcnow()
        meetings = db.query(Meeting).filter(
            Meeting.company_id == user.company_id,
            Meeting.start_time_utc >= now,
        ).order_by(Meeting.start_time_utc).limit(limit).all()
        return {
            "total": len(meetings),
            "meetings": [
                {
                    "id": m.id,
                    "title": m.title,
                    "start_time": m.start_time_utc.isoformat() if m.start_time_utc else None,
                    "end_time": m.end_time_utc.isoformat() if m.end_time_utc else None,
                    "platform": m.meeting_platform.value if m.meeting_platform else None,
                    "meeting_link": m.meeting_link,
                }
                for m in meetings
            ],
        }

    def _tool_list_departments(self, args: dict, db: Session, user: User) -> dict:
        depts = db.query(Department).filter(
            Department.company_id == user.company_id,
            Department.is_active == True,
        ).order_by(Department.name).all()
        return {
            "total": len(depts),
            "departments": [
                {"id": d.id, "name": d.name, "description": d.description}
                for d in depts
            ],
        }

    def _tool_create_department(self, args: dict, db: Session, user: User) -> dict:
        existing = db.query(Department).filter(
            Department.company_id == user.company_id,
            Department.name == args["name"],
        ).first()
        if existing:
            return {"error": f"Department '{args['name']}' already exists"}

        dept = Department(
            company_id=user.company_id,
            name=args["name"],
            description=args.get("description"),
            is_active=True,
        )
        db.add(dept)
        db.commit()
        db.refresh(dept)
        return {"success": True, "department_id": dept.id, "name": dept.name}

    def _tool_get_attendance_report(self, args: dict, db: Session, user: User) -> dict:
        target_date = date.fromisoformat(args["attendance_date"]) if args.get("attendance_date") else date.today()
        query = db.query(Attendance).filter(
            Attendance.company_id == user.company_id,
            Attendance.attendance_date == target_date,
        )
        if args.get("employee_id"):
            query = query.filter(Attendance.employee_id == args["employee_id"])

        records = query.all()
        return {
            "date": target_date.isoformat(),
            "total_records": len(records),
            "present": sum(1 for r in records if r.is_present),
            "absent": sum(1 for r in records if not r.is_present),
            "records": [
                {
                    "employee_id": r.employee_id,
                    "employee_name": (
                        f"{r.employee.first_name} {r.employee.last_name}" if r.employee else "N/A"
                    ),
                    "punch_in": r.punch_in_time.isoformat() if r.punch_in_time else None,
                    "punch_out": r.punch_out_time.isoformat() if r.punch_out_time else None,
                    "is_present": r.is_present,
                }
                for r in records
            ],
        }

    def _tool_list_pending_leave_requests(self, args: dict, db: Session, user: User) -> dict:
        requests = db.query(LeaveRequest).filter(
            LeaveRequest.company_id == user.company_id,
            LeaveRequest.status == LeaveStatus.PENDING,
        ).order_by(LeaveRequest.created_at.desc()).all()
        return {
            "total": len(requests),
            "leave_requests": [
                {
                    "id": r.id,
                    "employee_name": (
                        f"{r.employee.first_name} {r.employee.last_name}" if r.employee else "N/A"
                    ),
                    "leave_type": r.leave_type.name if r.leave_type else "N/A",
                    "start_date": r.start_date.isoformat(),
                    "end_date": r.end_date.isoformat(),
                    "number_of_days": r.number_of_days,
                    "reason": r.reason,
                    "applied_on": r.created_at.isoformat() if r.created_at else None,
                }
                for r in requests
            ],
        }

    def _tool_approve_reject_leave(self, args: dict, db: Session, user: User) -> dict:
        from app.api.v1.services.leave_service import LeaveService
        approved = args["action"] == "approve"
        leave_service = LeaveService()
        leave_request = leave_service.approve_leave(
            db=db,
            leave_request_id=args["leave_request_id"],
            approver_user_id=user.id,
            approved=approved,
            rejection_reason=args.get("rejection_reason"),
        )
        return {
            "success": True,
            "leave_request_id": leave_request.id,
            "status": leave_request.status.value,
            "action": args["action"],
        }

    def _tool_list_leave_types(self, args: dict, db: Session, user: User) -> dict:
        types = db.query(LeaveType).filter(
            LeaveType.company_id == user.company_id,
            LeaveType.is_active == True,
        ).all()
        return {
            "leave_types": [
                {
                    "id": lt.id,
                    "name": lt.name,
                    "code": lt.code,
                    "max_days_per_year": lt.max_days_per_year,
                    "is_paid": lt.is_paid,
                }
                for lt in types
            ]
        }

    def _tool_list_projects(self, args: dict, db: Session, user: User) -> dict:
        projects = db.query(Project).filter(
            Project.company_id == user.company_id,
            Project.is_active == True,
        ).order_by(Project.name).all()
        return {
            "total": len(projects),
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "client": p.client,
                    "target_date": p.target_date.isoformat() if p.target_date else None,
                }
                for p in projects
            ],
        }

    def _tool_get_dashboard_summary(self, args: dict, db: Session, user: User) -> dict:
        from sqlalchemy import func
        total_employees = db.query(func.count(Employee.id)).filter(
            Employee.company_id == user.company_id,
            Employee.is_active == True,
            Employee.deleted_at.is_(None),
        ).scalar() or 0

        today = date.today()
        present_today = db.query(func.count(Attendance.id)).filter(
            Attendance.company_id == user.company_id,
            Attendance.attendance_date == today,
            Attendance.is_present == True,
        ).scalar() or 0

        open_tasks = db.query(func.count(Task.id)).filter(
            Task.company_id == user.company_id,
            Task.status == TaskStatus.OPEN,
        ).scalar() or 0

        pending_leaves = db.query(func.count(LeaveRequest.id)).filter(
            LeaveRequest.company_id == user.company_id,
            LeaveRequest.status == LeaveStatus.PENDING,
        ).scalar() or 0

        return {
            "total_employees": total_employees,
            "present_today": present_today,
            "open_tasks": open_tasks,
            "pending_leave_requests": pending_leaves,
            "date": today.isoformat(),
        }

    # ── Employee tool implementations ────────────────────────────────────────

    def _tool_punch_in(self, args: dict, db: Session, user: User) -> dict:
        if not user.employee_id:
            return {"error": "No employee profile linked to your account"}
        from app.api.v1.services.attendance_service import AttendanceService
        attendance = AttendanceService.punch_in(db, user.company_id, user.employee_id)
        return {
            "success": True,
            "attendance_date": attendance.attendance_date.isoformat(),
            "punch_in_time": attendance.punch_in_time.isoformat() if attendance.punch_in_time else None,
            "message": "Attendance marked successfully. Have a great day!",
        }

    def _tool_punch_out(self, args: dict, db: Session, user: User) -> dict:
        if not user.employee_id:
            return {"error": "No employee profile linked to your account"}
        from app.api.v1.services.attendance_service import AttendanceService
        attendance = AttendanceService.punch_out(db, user.company_id, user.employee_id)
        return {
            "success": True,
            "attendance_date": attendance.attendance_date.isoformat(),
            "punch_out_time": attendance.punch_out_time.isoformat() if attendance.punch_out_time else None,
            "message": "Punch-out recorded. See you tomorrow!",
        }

    def _tool_get_my_tasks(self, args: dict, db: Session, user: User) -> dict:
        if not user.employee_id:
            return {"error": "No employee profile linked to your account"}
        query = db.query(Task).filter(
            Task.company_id == user.company_id,
            Task.assigned_to_employee_id == user.employee_id,
        )
        if args.get("status"):
            try:
                query = query.filter(Task.status == TaskStatus(args["status"]))
            except ValueError:
                pass

        tasks = query.order_by(Task.due_date.asc().nullslast(), Task.priority.desc()).limit(20).all()
        return {
            "total": len(tasks),
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                }
                for t in tasks
            ],
        }

    def _tool_get_my_attendance(self, args: dict, db: Session, user: User) -> dict:
        if not user.employee_id:
            return {"error": "No employee profile linked to your account"}
        today = date.today()
        start_date = date.fromisoformat(args["start_date"]) if args.get("start_date") else today.replace(day=1)
        end_date = date.fromisoformat(args["end_date"]) if args.get("end_date") else today

        records = db.query(Attendance).filter(
            Attendance.company_id == user.company_id,
            Attendance.employee_id == user.employee_id,
            Attendance.attendance_date >= start_date,
            Attendance.attendance_date <= end_date,
        ).order_by(Attendance.attendance_date.desc()).all()

        return {
            "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
            "total_days": len(records),
            "present_days": sum(1 for r in records if r.is_present),
            "records": [
                {
                    "date": r.attendance_date.isoformat(),
                    "punch_in": r.punch_in_time.isoformat() if r.punch_in_time else None,
                    "punch_out": r.punch_out_time.isoformat() if r.punch_out_time else None,
                    "is_present": r.is_present,
                }
                for r in records
            ],
        }

    def _tool_apply_for_leave(self, args: dict, db: Session, user: User) -> dict:
        if not user.employee_id:
            return {"error": "No employee profile linked to your account"}
        from app.api.v1.services.leave_service import LeaveService
        leave_service = LeaveService()
        leave_request = leave_service.apply_for_leave(
            db=db,
            company_id=user.company_id,
            employee_id=user.employee_id,
            leave_type_id=args["leave_type_id"],
            start_date=date.fromisoformat(args["start_date"]),
            end_date=date.fromisoformat(args["end_date"]),
            reason=args.get("reason"),
        )
        return {
            "success": True,
            "leave_request_id": leave_request.id,
            "status": leave_request.status.value,
            "number_of_days": leave_request.number_of_days,
            "start_date": leave_request.start_date.isoformat(),
            "end_date": leave_request.end_date.isoformat(),
            "message": "Leave request submitted successfully and is pending approval.",
        }

    def _tool_get_my_leave_balance(self, args: dict, db: Session, user: User) -> dict:
        if not user.employee_id:
            return {"error": "No employee profile linked to your account"}
        current_year = date.today().year
        balances = db.query(LeaveBalance).filter(
            LeaveBalance.company_id == user.company_id,
            LeaveBalance.employee_id == user.employee_id,
            LeaveBalance.year == current_year,
        ).all()

        leave_types = db.query(LeaveType).filter(
            LeaveType.company_id == user.company_id,
            LeaveType.is_active == True,
        ).all()

        result = []
        for lt in leave_types:
            bal = next((b for b in balances if b.leave_type_id == lt.id), None)
            result.append({
                "leave_type": lt.name,
                "total_days": float(bal.total_days) if bal else 0,
                "used_days": float(bal.used_days) if bal else 0,
                "pending_days": float(bal.pending_days) if bal else 0,
                "available_days": float(bal.available_days) if bal else (lt.max_days_per_year or 0),
            })
        return {"year": current_year, "balances": result}

    def _tool_get_my_profile(self, args: dict, db: Session, user: User) -> dict:
        if not user.employee_id:
            return {"error": "No employee profile linked to your account"}
        emp = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if not emp:
            return {"error": "Employee profile not found"}
        return {
            "employee_code": emp.employee_code,
            "full_name": f"{emp.first_name} {emp.last_name}",
            "email": emp.email,
            "phone": emp.phone,
            "position": emp.position,
            "department": emp.department.name if emp.department else None,
            "hire_date": emp.hire_date.isoformat() if emp.hire_date else None,
            "is_active": emp.is_active,
        }

    def _tool_update_my_task_status(self, args: dict, db: Session, user: User) -> dict:
        if not user.employee_id:
            return {"error": "No employee profile linked to your account"}
        task = db.query(Task).filter(
            Task.id == args["task_id"],
            Task.company_id == user.company_id,
            Task.assigned_to_employee_id == user.employee_id,
        ).first()
        if not task:
            return {"error": "Task not found or not assigned to you"}
        try:
            task.status = TaskStatus(args["status"])
        except ValueError:
            return {"error": f"Invalid status: {args['status']}"}
        task.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
        return {
            "success": True,
            "task_id": task.id,
            "title": task.title,
            "new_status": task.status.value,
        }

    # ── Business OS tool implementations ────────────────────────────────────

    def _tool_list_inventory_items(self, args: dict, db: Session, user: User) -> dict:
        from sqlalchemy import or_
        query = db.query(InventoryItem).filter(
            InventoryItem.company_id == user.company_id,
            InventoryItem.deleted_at.is_(None),
            InventoryItem.is_active == True,
        )
        search = args.get("search")
        if search:
            query = query.filter(InventoryItem.name.ilike(f"%{search}%"))
        items = query.order_by(InventoryItem.name).limit(30).all()
        result = []
        for i in items:
            is_low = i.reorder_level is not None and i.quantity_on_hand <= i.reorder_level
            if args.get("low_stock_only") and not is_low:
                continue
            result.append({
                "id": i.id,
                "name": i.name,
                "sku": i.sku,
                "quantity_on_hand": float(i.quantity_on_hand),
                "unit": i.unit,
                "reorder_level": float(i.reorder_level) if i.reorder_level else None,
                "is_low_stock": is_low,
                "item_type": i.item_type.value,
            })
        return {"total": len(result), "items": result}

    def _tool_add_stock(self, args: dict, db: Session, user: User) -> dict:
        from app.api.v1.models.inventory_model import TransactionType
        item = db.query(InventoryItem).filter(
            InventoryItem.id == args["item_id"],
            InventoryItem.company_id == user.company_id,
            InventoryItem.deleted_at.is_(None),
        ).first()
        if not item:
            return {"error": "Item not found"}
        qty = args["quantity"]
        item.quantity_on_hand += qty
        txn = InventoryTransaction(
            company_id=user.company_id,
            item_id=item.id,
            transaction_type=TransactionType.STOCK_IN,
            quantity=qty,
            notes=args.get("notes"),
            performed_by_user_id=user.id,
        )
        db.add(txn)
        db.commit()
        return {"success": True, "item": item.name, "added": qty, "new_quantity": float(item.quantity_on_hand)}

    def _tool_consume_stock(self, args: dict, db: Session, user: User) -> dict:
        from app.api.v1.models.inventory_model import TransactionType
        item = db.query(InventoryItem).filter(
            InventoryItem.id == args["item_id"],
            InventoryItem.company_id == user.company_id,
            InventoryItem.deleted_at.is_(None),
        ).first()
        if not item:
            return {"error": "Item not found"}
        qty = args["quantity"]
        if item.quantity_on_hand < qty:
            return {"error": f"Insufficient stock. Available: {float(item.quantity_on_hand)} {item.unit or ''}"}
        item.quantity_on_hand -= qty
        txn = InventoryTransaction(
            company_id=user.company_id,
            item_id=item.id,
            transaction_type=TransactionType.STOCK_OUT,
            quantity=qty,
            notes=args.get("notes"),
            performed_by_user_id=user.id,
        )
        db.add(txn)
        db.commit()
        return {"success": True, "item": item.name, "consumed": qty, "remaining": float(item.quantity_on_hand)}

    def _tool_get_low_stock_alerts(self, args: dict, db: Session, user: User) -> dict:
        items = db.query(InventoryItem).filter(
            InventoryItem.company_id == user.company_id,
            InventoryItem.deleted_at.is_(None),
            InventoryItem.is_active == True,
            InventoryItem.reorder_level.isnot(None),
        ).all()
        alerts = [
            {"id": i.id, "name": i.name, "quantity": float(i.quantity_on_hand),
             "reorder_level": float(i.reorder_level), "unit": i.unit}
            for i in items if i.quantity_on_hand <= i.reorder_level
        ]
        return {"total_alerts": len(alerts), "items": alerts}

    def _tool_list_clients(self, args: dict, db: Session, user: User) -> dict:
        query = db.query(Client).filter(
            Client.company_id == user.company_id,
            Client.deleted_at.is_(None),
            Client.is_active == True,
        )
        search = args.get("search")
        if search:
            query = query.filter(Client.name.ilike(f"%{search}%"))
        label = args.get("industry_label")
        if label:
            query = query.filter(Client.industry_label == label)
        clients = query.order_by(Client.name).limit(20).all()
        return {
            "total": len(clients),
            "clients": [
                {"id": c.id, "name": c.name, "phone": c.phone, "email": c.email,
                 "industry_label": c.industry_label}
                for c in clients
            ],
        }

    def _tool_add_client(self, args: dict, db: Session, user: User) -> dict:
        from app.api.v1.models.crm_model import ClientType
        client = Client(
            company_id=user.company_id,
            name=args["name"],
            phone=args.get("phone"),
            email=args.get("email"),
            industry_label=args.get("industry_label"),
            notes=args.get("notes"),
            client_type=ClientType.INDIVIDUAL,
        )
        db.add(client)
        db.commit()
        db.refresh(client)
        return {"success": True, "client_id": client.id, "name": client.name}

    def _tool_log_client_interaction(self, args: dict, db: Session, user: User) -> dict:
        from app.api.v1.models.crm_model import InteractionType
        client = db.query(Client).filter(
            Client.id == args["client_id"],
            Client.company_id == user.company_id,
        ).first()
        if not client:
            return {"error": "Client not found"}
        itype_str = args.get("interaction_type", "note")
        try:
            itype = InteractionType(itype_str)
        except ValueError:
            itype = InteractionType.NOTE
        interaction = ClientInteraction(
            company_id=user.company_id,
            client_id=client.id,
            interaction_type=itype,
            subject=args.get("subject"),
            notes=args.get("notes"),
            performed_by_user_id=user.id,
            interaction_date=datetime.utcnow(),
        )
        db.add(interaction)
        db.commit()
        return {"success": True, "interaction_id": interaction.id, "client": client.name}

    def _tool_list_bookings(self, args: dict, db: Session, user: User) -> dict:
        query = db.query(Booking).filter(Booking.company_id == user.company_id)
        status_str = args.get("status")
        if status_str:
            try:
                query = query.filter(Booking.status == BookingStatus(status_str))
            except ValueError:
                pass
        bookings = query.order_by(Booking.start_datetime).limit(20).all()
        return {
            "total": len(bookings),
            "bookings": [
                {
                    "id": b.id,
                    "title": b.title,
                    "status": b.status.value,
                    "start": b.start_datetime.isoformat() if b.start_datetime else None,
                    "end": b.end_datetime.isoformat() if b.end_datetime else None,
                }
                for b in bookings
            ],
        }

    def _tool_create_booking(self, args: dict, db: Session, user: User) -> dict:
        if args["end_datetime"] <= args["start_datetime"]:
            return {"error": "end_datetime must be after start_datetime"}
        start = datetime.fromisoformat(args["start_datetime"])
        end = datetime.fromisoformat(args["end_datetime"])
        booking = Booking(
            company_id=user.company_id,
            title=args["title"],
            start_datetime=start,
            end_datetime=end,
            client_id=args.get("client_id"),
            employee_id=args.get("employee_id"),
            resource_id=args.get("resource_id"),
            notes=args.get("notes"),
            booked_by_user_id=user.id,
            status=BookingStatus.CONFIRMED,
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return {
            "success": True,
            "booking_id": booking.id,
            "title": booking.title,
            "start": booking.start_datetime.isoformat(),
            "end": booking.end_datetime.isoformat(),
            "status": booking.status.value,
        }

    def _tool_list_booking_resources(self, args: dict, db: Session, user: User) -> dict:
        resources = db.query(BookingResource).filter(
            BookingResource.company_id == user.company_id,
            BookingResource.is_active == True,
        ).order_by(BookingResource.name).all()
        return {
            "total": len(resources),
            "resources": [
                {"id": r.id, "name": r.name, "resource_type": r.resource_type, "capacity": r.capacity}
                for r in resources
            ],
        }

    def _tool_list_invoices(self, args: dict, db: Session, user: User) -> dict:
        query = db.query(Invoice).filter(Invoice.company_id == user.company_id)
        status_str = args.get("status")
        if status_str:
            try:
                query = query.filter(Invoice.status == InvoiceStatus(status_str))
            except ValueError:
                pass
        invoices = query.order_by(Invoice.created_at.desc()).limit(20).all()
        return {
            "total": len(invoices),
            "invoices": [
                {
                    "id": i.id,
                    "invoice_number": i.invoice_number,
                    "status": i.status.value,
                    "total_amount": float(i.total_amount),
                    "issue_date": i.issue_date.isoformat() if i.issue_date else None,
                    "due_date": i.due_date.isoformat() if i.due_date else None,
                }
                for i in invoices
            ],
        }

    def _tool_list_shifts(self, args: dict, db: Session, user: User) -> dict:
        shifts = db.query(Shift).filter(
            Shift.company_id == user.company_id,
            Shift.is_active == True,
        ).order_by(Shift.name).all()
        return {
            "total": len(shifts),
            "shifts": [
                {"id": s.id, "name": s.name, "start_time": str(s.start_time), "end_time": str(s.end_time)}
                for s in shifts
            ],
        }

    def _tool_list_shift_assignments(self, args: dict, db: Session, user: User) -> dict:
        assignments = db.query(ShiftAssignment).filter(
            ShiftAssignment.company_id == user.company_id,
            ShiftAssignment.effective_to.is_(None),
        ).limit(30).all()
        return {
            "total": len(assignments),
            "assignments": [
                {
                    "id": a.id,
                    "employee_id": a.employee_id,
                    "shift_id": a.shift_id,
                    "effective_from": a.effective_from.isoformat() if a.effective_from else None,
                }
                for a in assignments
            ],
        }

    def _tool_list_donations(self, args: dict, db: Session, user: User) -> dict:
        query = db.query(Donation).filter(Donation.company_id == user.company_id)
        if args.get("purpose"):
            query = query.filter(Donation.purpose.ilike(f"%{args['purpose']}%"))
        if args.get("donor_name"):
            query = query.filter(Donation.donor_name.ilike(f"%{args['donor_name']}%"))
        donations = query.order_by(Donation.donated_at.desc()).limit(20).all()
        return {
            "total": len(donations),
            "donations": [
                {
                    "id": d.id,
                    "donor_name": d.donor_name,
                    "amount": float(d.amount),
                    "purpose": d.purpose,
                    "mode": d.donation_mode.value,
                    "receipt": d.receipt_number,
                    "date": d.donated_at.isoformat() if d.donated_at else None,
                }
                for d in donations
            ],
        }

    def _tool_record_donation(self, args: dict, db: Session, user: User) -> dict:
        from app.api.v1.models.donation_model import DonationMode
        from app.api.v1.services.donation_service import _generate_receipt_number
        receipt = _generate_receipt_number(db, user.company_id)
        try:
            mode = DonationMode(args.get("donation_mode", "cash"))
        except ValueError:
            mode = DonationMode.CASH
        donation = Donation(
            company_id=user.company_id,
            donor_name=args["donor_name"],
            amount=args["amount"],
            purpose=args.get("purpose"),
            donation_mode=mode,
            donor_phone=args.get("donor_phone"),
            notes=args.get("notes"),
            receipt_number=receipt,
            donated_at=datetime.utcnow(),
            received_by_user_id=user.id,
        )
        db.add(donation)
        db.commit()
        db.refresh(donation)
        return {
            "success": True,
            "donation_id": donation.id,
            "receipt_number": donation.receipt_number,
            "donor": donation.donor_name,
            "amount": float(donation.amount),
        }

    def _tool_get_donation_summary(self, args: dict, db: Session, user: User) -> dict:
        from sqlalchemy import func
        total = db.query(func.sum(Donation.amount)).filter(Donation.company_id == user.company_id).scalar() or 0
        count = db.query(func.count(Donation.id)).filter(Donation.company_id == user.company_id).scalar() or 0
        return {"total_donations": count, "total_amount": float(total)}

    # ─── Agentic Loop ─────────────────────────────────────────────────────────

    def chat(
        self,
        db: Session,
        user: User,
        question: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> tuple[str, int]:
        """
        Agentic chat loop:
        1. Send user message + tools to OpenAI
        2. If model calls a tool → execute it → send result back
        3. Repeat until model gives a final text response

        Returns:
            (response_text, total_tokens_used) — tokens are real counts from OpenAI API
        """
        tools = self._get_tools(user.role)
        messages = [{"role": "system", "content": self._system_prompt(user, user.role, db)}]

        if conversation_history:
            # Keep last 6 messages (3 turns) — enough for multi-turn context without bloating tokens
            messages.extend(conversation_history[-6:])
        messages.append({"role": "user", "content": question})

        total_tokens = 0

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=600,
            )

            # Accumulate real token counts from OpenAI
            if response.usage:
                total_tokens += response.usage.total_tokens

            msg = response.choices[0].message

            # No tool call → final answer
            if not msg.tool_calls:
                return msg.content.strip(), total_tokens

            # Execute all tool calls
            messages.append(msg)
            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                try:
                    fn_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                logger.info(f"Agent calling tool: {fn_name} with args: {fn_args}")
                result = self._run_tool(fn_name, fn_args, db, user)

                # Cap tool result size to ~2000 chars to prevent large payloads
                # inflating subsequent rounds in the loop
                result_str = json.dumps(result)
                if len(result_str) > 2000:
                    result_str = result_str[:2000] + "...(truncated)"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_str,
                })

        # Fallback if loop exhausted
        return "I completed the requested actions. Please check the system for the updates.", total_tokens
