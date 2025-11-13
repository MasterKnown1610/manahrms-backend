from fastapi import APIRouter

from app.api.v1.routes import auth, employees, departments, tasks

# Create main API router
api_router = APIRouter()

# Include route modules
api_router.include_router(auth.router)
api_router.include_router(employees.router)
api_router.include_router(departments.router)
api_router.include_router(tasks.router)

# Note: users, attendance, payroll routes can be added as needed
# api_router.include_router(users.router)
# api_router.include_router(attendance.router)
# api_router.include_router(payroll.router)


