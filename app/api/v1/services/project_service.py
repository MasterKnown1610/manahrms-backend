from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fastapi import HTTPException, status
from datetime import date

from app.api.v1.models.project_model import Project
from app.api.v1.models.user_model import User
from app.api.v1.models.task_model import Task, TaskStatus
from app.api.v1.schemas.project_schema import ProjectCreate, ProjectUpdate


class ProjectService:
    """
    Service class for project management operations.
    """

    @staticmethod
    def create_project(
        db: Session,
        company_id: int,
        data: ProjectCreate,
    ) -> Project:
        """
        Create a new project.
        Validates that the project lead (if provided) belongs to the company.
        """
        # Validate project lead belongs to company (if provided)
        if data.project_lead_id:
            project_lead = db.query(User).filter(
                User.id == data.project_lead_id,
                User.company_id == company_id,
                User.is_active == True
            ).first()
            if not project_lead:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project lead not found in company"
                )

        # Check if project name already exists in company
        existing = db.query(Project).filter(
            Project.name == data.name,
            Project.company_id == company_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project with this name already exists in your company"
            )

        project = Project(
            company_id=company_id,
            name=data.name,
            client=data.client,
            number_of_days=data.number_of_days,
            target_date=data.target_date,
            project_lead_id=data.project_lead_id,
            is_active=True
        )
        
        db.add(project)
        db.commit()
        db.refresh(project)
        
        return project

    @staticmethod
    def get_project_by_id(
        db: Session,
        company_id: int,
        project_id: int
    ) -> Project:
        """
        Get a project by ID, ensuring it belongs to the company.
        """
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.company_id == company_id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        return project

    @staticmethod
    def list_projects(
        db: Session,
        company_id: int,
        page: int = 1,
        limit: int = 20,
        is_active: Optional[bool] = None,
        project_lead_id: Optional[int] = None,
        include_task_stats: bool = False
    ) -> Tuple[List[Project], int]:
        """
        List all projects for a company with optional filtering.
        """
        query = db.query(Project).filter(
            Project.company_id == company_id
        )
        
        if is_active is not None:
            query = query.filter(Project.is_active == is_active)
        
        if project_lead_id is not None:
            query = query.filter(Project.project_lead_id == project_lead_id)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        projects = query.order_by(Project.created_at.desc()).offset(offset).limit(limit).all()
        
        return projects, total

    @staticmethod
    def update_project(
        db: Session,
        company_id: int,
        project_id: int,
        data: ProjectUpdate
    ) -> Project:
        """
        Update a project.
        Validates that the project lead (if provided) belongs to the company.
        """
        project = ProjectService.get_project_by_id(db, company_id, project_id)
        
        # Validate project lead if being updated
        if data.project_lead_id is not None:
            project_lead = db.query(User).filter(
                User.id == data.project_lead_id,
                User.company_id == company_id,
                User.is_active == True
            ).first()
            if not project_lead:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project lead not found in company"
                )
        
        # Check name uniqueness if name is being updated
        if data.name is not None and data.name != project.name:
            existing = db.query(Project).filter(
                Project.name == data.name,
                Project.company_id == company_id,
                Project.id != project_id
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project with this name already exists in your company"
                )
        
        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(project, field, value)
        
        db.commit()
        db.refresh(project)
        
        return project

    @staticmethod
    def deactivate_project(
        db: Session,
        company_id: int,
        project_id: int
    ) -> Project:
        """
        Deactivate a project (soft delete).
        """
        project = ProjectService.get_project_by_id(db, company_id, project_id)
        
        project.is_active = False
        db.commit()
        db.refresh(project)
        
        return project

    @staticmethod
    def get_project_task_stats(
        db: Session,
        project_id: int
    ) -> dict:
        """
        Get task statistics for a project.
        Returns counts of total, open, in_progress, and closed tasks.
        """
        stats = db.query(
            func.count(Task.id).label('total'),
            func.sum(func.case((Task.status == TaskStatus.OPEN, 1), else_=0)).label('open'),
            func.sum(func.case((Task.status == TaskStatus.IN_PROGRESS, 1), else_=0)).label('in_progress'),
            func.sum(func.case((Task.status == TaskStatus.CLOSED, 1), else_=0)).label('closed')
        ).filter(
            Task.project_id == project_id
        ).first()
        
        return {
            'total': stats.total or 0,
            'open': stats.open or 0,
            'in_progress': stats.in_progress or 0,
            'closed': stats.closed or 0
        }

    @staticmethod
    def get_projects_by_lead(
        db: Session,
        company_id: int,
        user_id: int
    ) -> List[Project]:
        """
        Get all projects where a specific user is the project lead.
        """
        return db.query(Project).filter(
            Project.company_id == company_id,
            Project.project_lead_id == user_id,
            Project.is_active == True
        ).all()

