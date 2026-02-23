from fastapi import APIRouter

from app.api.v1.routes import auth, employees, departments, tasks, projects, attendance, ai_chat, vector_sync, leaves, dashboard, chat, websocket, meetings, events, calendar

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
api_router.include_router(websocket.router)
api_router.include_router(meetings.router)
api_router.include_router(events.router)
api_router.include_router(calendar.router)


