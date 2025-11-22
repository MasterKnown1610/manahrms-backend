"""
Vector Sync Service for maintaining embeddings in sync with company data
Updates vector store when employees, projects, tasks, etc. are created/updated/deleted
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.api.v1.models.vector_store_model import VectorStore
from app.api.v1.models.employee_model import Employee
from app.api.v1.models.project_model import Project
from app.api.v1.models.task_model import Task
from app.api.v1.models.department_model import Department
from app.api.v1.models.company_model import Company
from app.api.v1.services.embedding_service import EmbeddingService
import json


class VectorSyncService:
    """Service for syncing embeddings with company data"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
    
    def sync_company_data(self, db: Session, company_id: int) -> dict:
        """
        Sync all company data to vector store.
        This should be called periodically or when bulk updates occur.
        
        Args:
            db: Database session
            company_id: Company ID to sync
            
        Returns:
            Dictionary with sync statistics
        """
        stats = {
            "employees": 0,
            "projects": 0,
            "tasks": 0,
            "departments": 0,
            "company": 0,
            "errors": []
        }
        
        try:
            # Sync company info
            self.sync_company(db, company_id)
            stats["company"] = 1
            
            # Sync departments
            departments = db.query(Department).filter(
                Department.company_id == company_id,
                Department.is_active == True
            ).all()
            for dept in departments:
                try:
                    self.sync_department(db, dept.id)
                    stats["departments"] += 1
                except Exception as e:
                    stats["errors"].append(f"Department {dept.id}: {str(e)}")
            
            # Sync employees
            employees = db.query(Employee).filter(
                Employee.company_id == company_id,
                Employee.is_active == True
            ).all()
            for emp in employees:
                try:
                    self.sync_employee(db, emp.id)
                    stats["employees"] += 1
                except Exception as e:
                    stats["errors"].append(f"Employee {emp.id}: {str(e)}")
            
            # Sync projects
            projects = db.query(Project).filter(
                Project.company_id == company_id,
                Project.is_active == True
            ).all()
            for proj in projects:
                try:
                    self.sync_project(db, proj.id)
                    stats["projects"] += 1
                except Exception as e:
                    stats["errors"].append(f"Project {proj.id}: {str(e)}")
            
            # Sync tasks
            tasks = db.query(Task).filter(
                Task.company_id == company_id
            ).all()
            for task in tasks:
                try:
                    self.sync_task(db, task.id)
                    stats["tasks"] += 1
                except Exception as e:
                    stats["errors"].append(f"Task {task.id}: {str(e)}")
            
        except Exception as e:
            stats["errors"].append(f"Sync error: {str(e)}")
        
        return stats
    
    def sync_employee(self, db: Session, employee_id: int) -> Optional[VectorStore]:
        """Sync a single employee to vector store"""
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            return None
        
        # Prepare employee data
        emp_data = {
            "name": f"{employee.first_name} {employee.last_name}",
            "code": employee.employee_code,
            "email": employee.email,
            "position": employee.position or "N/A",
            "department": employee.department.name if employee.department else None,
            "phone": employee.phone,
        }
        
        # Create content text
        content_text = self.embedding_service.create_content_text("employee", emp_data)
        
        # Generate embedding
        embedding = self.embedding_service.generate_embedding(content_text)
        
        # Store or update in vector store
        vector_store = db.query(VectorStore).filter(
            and_(
                VectorStore.company_id == employee.company_id,
                VectorStore.content_type == "employee",
                VectorStore.content_id == employee_id
            )
        ).first()
        
        if vector_store:
            vector_store.content_text = content_text
            vector_store.embedding = embedding
            vector_store.content_metadata = json.dumps(emp_data)
        else:
            vector_store = VectorStore(
                company_id=employee.company_id,
                content_type="employee",
                content_id=employee_id,
                content_text=content_text,
                embedding=embedding,
                content_metadata=json.dumps(emp_data)
            )
            db.add(vector_store)
        
        db.commit()
        return vector_store
    
    def sync_project(self, db: Session, project_id: int) -> Optional[VectorStore]:
        """Sync a single project to vector store"""
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None
        
        # Safely access project lead relationship
        lead_name = None
        if project.project_lead_id and project.project_lead:
            try:
                lead_name = f"{project.project_lead.first_name} {project.project_lead.last_name}"
            except:
                lead_name = None
        
        proj_data = {
            "name": project.name,
            "client": project.client,
            "target_date": str(project.target_date) if project.target_date else None,
            "lead": lead_name,
        }
        
        content_text = self.embedding_service.create_content_text("project", proj_data)
        embedding = self.embedding_service.generate_embedding(content_text)
        
        vector_store = db.query(VectorStore).filter(
            and_(
                VectorStore.company_id == project.company_id,
                VectorStore.content_type == "project",
                VectorStore.content_id == project_id
            )
        ).first()
        
        if vector_store:
            vector_store.content_text = content_text
            vector_store.embedding = embedding
            vector_store.content_metadata = json.dumps(proj_data)
        else:
            vector_store = VectorStore(
                company_id=project.company_id,
                content_type="project",
                content_id=project_id,
                content_text=content_text,
                embedding=embedding,
                content_metadata=json.dumps(proj_data)
            )
            db.add(vector_store)
        
        db.commit()
        return vector_store
    
    def sync_task(self, db: Session, task_id: int) -> Optional[VectorStore]:
        """Sync a single task to vector store"""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None
        
        # Safely access relationships
        assigned_to_name = None
        if task.assigned_to_employee_id and task.assigned_to_employee:
            try:
                assigned_to_name = f"{task.assigned_to_employee.first_name} {task.assigned_to_employee.last_name}"
            except:
                assigned_to_name = None
        
        project_name = None
        if task.project_id and task.project:
            try:
                project_name = task.project.name
            except:
                project_name = None
        
        task_data = {
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "due_date": str(task.due_date) if task.due_date else None,
            "assigned_to": assigned_to_name,
            "project": project_name,
        }
        
        content_text = self.embedding_service.create_content_text("task", task_data)
        embedding = self.embedding_service.generate_embedding(content_text)
        
        vector_store = db.query(VectorStore).filter(
            and_(
                VectorStore.company_id == task.company_id,
                VectorStore.content_type == "task",
                VectorStore.content_id == task_id
            )
        ).first()
        
        if vector_store:
            vector_store.content_text = content_text
            vector_store.embedding = embedding
            vector_store.content_metadata = json.dumps(task_data)
        else:
            vector_store = VectorStore(
                company_id=task.company_id,
                content_type="task",
                content_id=task_id,
                content_text=content_text,
                embedding=embedding,
                content_metadata=json.dumps(task_data)
            )
            db.add(vector_store)
        
        db.commit()
        return vector_store
    
    def sync_department(self, db: Session, department_id: int) -> Optional[VectorStore]:
        """Sync a single department to vector store"""
        dept = db.query(Department).filter(Department.id == department_id).first()
        if not dept:
            return None
        
        dept_data = {
            "name": dept.name,
            "description": dept.description,
        }
        
        content_text = self.embedding_service.create_content_text("department", dept_data)
        embedding = self.embedding_service.generate_embedding(content_text)
        
        vector_store = db.query(VectorStore).filter(
            and_(
                VectorStore.company_id == dept.company_id,
                VectorStore.content_type == "department",
                VectorStore.content_id == department_id
            )
        ).first()
        
        if vector_store:
            vector_store.content_text = content_text
            vector_store.embedding = embedding
            vector_store.content_metadata = json.dumps(dept_data)
        else:
            vector_store = VectorStore(
                company_id=dept.company_id,
                content_type="department",
                content_id=department_id,
                content_text=content_text,
                embedding=embedding,
                content_metadata=json.dumps(dept_data)
            )
            db.add(vector_store)
        
        db.commit()
        return vector_store
    
    def sync_company(self, db: Session, company_id: int) -> Optional[VectorStore]:
        """Sync company information to vector store"""
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return None
        
        company_data = {
            "name": company.company_name,
            "code": company.company_code,
            "type": company.company_type,
            "email": company.email,
            "phone": company.phone,
        }
        
        content_text = self.embedding_service.create_content_text("company", company_data)
        embedding = self.embedding_service.generate_embedding(content_text)
        
        vector_store = db.query(VectorStore).filter(
            and_(
                VectorStore.company_id == company_id,
                VectorStore.content_type == "company",
                VectorStore.content_id == company_id
            )
        ).first()
        
        if vector_store:
            vector_store.content_text = content_text
            vector_store.embedding = embedding
            vector_store.content_metadata = json.dumps(company_data)
        else:
            vector_store = VectorStore(
                company_id=company_id,
                content_type="company",
                content_id=company_id,
                content_text=content_text,
                embedding=embedding,
                content_metadata=json.dumps(company_data)
            )
            db.add(vector_store)
        
        db.commit()
        return vector_store
    
    def delete_content(self, db: Session, company_id: int, content_type: str, content_id: int):
        """Delete vector store entry when content is deleted"""
        db.query(VectorStore).filter(
            and_(
                VectorStore.company_id == company_id,
                VectorStore.content_type == content_type,
                VectorStore.content_id == content_id
            )
        ).delete()
        db.commit()

