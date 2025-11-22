from fastapi import APIRouter

from app.api.v1.routes import auth, employees, departments, tasks, projects, attendance, ai_chat

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(employees.router)
api_router.include_router(departments.router)
api_router.include_router(tasks.router)
api_router.include_router(projects.router)
api_router.include_router(attendance.router)
api_router.include_router(ai_chat.router)


