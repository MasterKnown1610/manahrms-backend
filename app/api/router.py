from fastapi import APIRouter

from app.api.v1.routes import (
    auth, employees, departments, tasks, projects, attendance, ai_chat,
    vector_sync, leaves, dashboard, chat, meetings, events, calendar,
    subscriptions, webhooks, superadmin,
    # New Business OS modules
    company_profile, inventory, assets, crm, booking, billing_ops, shifts, donations, leads,
    exotel_call, roles,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(employees.router)
api_router.include_router(departments.router)
api_router.include_router(tasks.router)
api_router.include_router(projects.router)
api_router.include_router(attendance.router)
api_router.include_router(ai_chat.router)
api_router.include_router(vector_sync.router)
api_router.include_router(leaves.router)
api_router.include_router(dashboard.router)
api_router.include_router(chat.router)
# WebSocket router is included directly in main.py (not here) to avoid /api/v1 prefix
api_router.include_router(meetings.router)
api_router.include_router(events.router)
api_router.include_router(calendar.router)
api_router.include_router(subscriptions.router)
api_router.include_router(webhooks.router)
api_router.include_router(superadmin.router)
# ── New Business OS modules ──────────────────────────────────────────────────
api_router.include_router(company_profile.router)
api_router.include_router(inventory.router)
api_router.include_router(assets.router)
api_router.include_router(crm.router)
api_router.include_router(booking.router)
api_router.include_router(billing_ops.router)
api_router.include_router(shifts.router)
api_router.include_router(donations.router)
api_router.include_router(leads.router)
api_router.include_router(exotel_call.router)
api_router.include_router(roles.router)


