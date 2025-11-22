"""
AI Chat Service for HRMS
Uses OpenAI API with RAG (Retrieval Augmented Generation) to answer questions
about company data efficiently using minimal tokens.
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from openai import OpenAI
import json

from app.core.config import settings
from app.api.v1.models.company_model import Company
from app.api.v1.models.employee_model import Employee
from app.api.v1.models.department_model import Department
from app.api.v1.models.project_model import Project
from app.api.v1.models.task_model import Task
from app.api.v1.models.attendance_model import Attendance
from app.api.v1.utils.error_handler import raise_http_exception
from fastapi import status


class AIChatService:
    """Service for AI-powered chat using company data"""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured. Please set OPENAI_API_KEY in environment variables or .env file.")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
    
    def _extract_company_context(self, db: Session, company_id: int) -> Dict:
        """
        Extract relevant company data to create context.
        This is done efficiently to minimize token usage.
        """
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return {}
        
        # Get summary counts and key information
        employees = db.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.is_active == True
        ).all()
        
        departments = db.query(Department).filter(
            Department.company_id == company_id,
            Department.is_active == True
        ).all()
        
        projects = db.query(Project).filter(
            Project.company_id == company_id,
            Project.is_active == True
        ).all()
        
        # Get tasks with relationships loaded
        tasks = db.query(Task).filter(
            Task.company_id == company_id
        ).all()
        
        # Create employee lookup for quick access
        employee_lookup = {emp.id: emp for emp in employees}
        
        # Build detailed task information
        tasks_detail = []
        for task in tasks[:50]:  # Limit to 50 most recent tasks
            assigned_employee = None
            if task.assigned_to_employee_id and task.assigned_to_employee_id in employee_lookup:
                emp = employee_lookup[task.assigned_to_employee_id]
                assigned_employee = {
                    "name": f"{emp.first_name} {emp.last_name}",
                    "code": emp.employee_code,
                    "email": emp.email,
                    "position": emp.position,
                }
            
            task_info = {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status.value,
                "priority": task.priority.value,
                "due_date": str(task.due_date) if task.due_date else None,
                "assigned_to": assigned_employee,
                "project": task.project.name if task.project else None,
            }
            tasks_detail.append(task_info)
        
        # Build concise context
        context = {
            "company": {
                "name": company.company_name,
                "code": company.company_code,
                "type": company.company_type,
                "email": company.email,
                "phone": company.phone,
            },
            "employees": [
                {
                    "name": f"{emp.first_name} {emp.last_name}",
                    "code": emp.employee_code,
                    "email": emp.email,
                    "position": emp.position,
                    "department": emp.department.name if emp.department else None,
                }
                for emp in employees[:50]  # Limit to 50 most recent
            ],
            "departments": [
                {
                    "name": dept.name,
                    "description": dept.description,
                }
                for dept in departments
            ],
            "projects": [
                {
                    "name": proj.name,
                    "client": proj.client,
                    "target_date": str(proj.target_date) if proj.target_date else None,
                }
                for proj in projects[:20]  # Limit to 20 most recent
            ],
            "tasks": tasks_detail,
            "tasks_summary": {
                "total": len(tasks),
                "open": len([t for t in tasks if t.status.value == "open"]),
                "in_progress": len([t for t in tasks if t.status.value == "in_progress"]),
                "closed": len([t for t in tasks if t.status.value == "closed"]),
            },
            "statistics": {
                "total_employees": len(employees),
                "total_departments": len(departments),
                "total_projects": len(projects),
            }
        }
        
        return context
    
    def _create_system_prompt(self, company_context: Dict) -> str:
        """Create a system prompt with company context"""
        context_str = json.dumps(company_context, indent=2)
        
        return f"""You are an AI assistant for an HRMS (Human Resource Management System) helping employees and administrators answer questions about their company data.

Company Context:
{context_str}

Instructions:
1. Answer questions based ONLY on the provided company context
2. Be concise and accurate - use minimal tokens
3. If information is not available in the context, say so clearly
4. For employee-related questions, use the employee list provided
5. For department questions, refer to the departments list
6. For project questions, use the projects information
7. For task questions, use the detailed tasks list which includes assigned employees, status, priority, and due dates
8. When asked about tasks, provide details including title, assigned employee name, status, and priority
9. Always be helpful and professional
10. If asked about data not in context, suggest checking the HRMS system directly

Remember: Keep responses brief and token-efficient while being helpful."""
    
    def chat(
        self,
        db: Session,
        company_id: int,
        user_question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Process a chat question and return AI response.
        
        Args:
            db: Database session
            company_id: Company ID to filter data
            user_question: User's question in natural language
            conversation_history: Optional list of previous messages [{"role": "user/assistant", "content": "..."}]
        
        Returns:
            AI response string
        """
        if not settings.OPENAI_API_KEY:
            raise_http_exception(
                message="OpenAI API key is not configured",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code="OPENAI_NOT_CONFIGURED"
            )
        
        # Extract company context
        company_context = self._extract_company_context(db, company_id)
        
        # Create system prompt
        system_prompt = self._create_system_prompt(company_context)
        
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current question
        messages.append({"role": "user", "content": user_question})
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500,  # Limit response length for token efficiency
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            raise_http_exception(
                message=f"Error processing AI chat request: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="AI_CHAT_ERROR"
            )

