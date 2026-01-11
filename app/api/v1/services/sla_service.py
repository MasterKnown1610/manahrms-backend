from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime
import logging

from app.api.v1.repositories.workflow_repository import SLARepository, TaskWorkflowRepository
from app.api.v1.models.workflow_model import TaskSLATracking, SLAStatus
from app.api.v1.models.task_model import Task

logger = logging.getLogger(__name__)


class SLAService:
    """Service for SLA operations"""
    
    @staticmethod
    def get_task_sla(
        db: Session,
        task_id: int,
        company_id: int
    ) -> dict:
        """Get SLA status for task"""
        # Verify task exists
        task = TaskWorkflowRepository.get_task_with_workflow(db, task_id, company_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Get all SLA tracking for task
        all_tracking = SLARepository.get_task_sla_tracking(db, task_id)
        
        # Get current SLA (for current node)
        current_sla = None
        if task.current_node_id:
            current_tracking = SLARepository.get_task_sla_tracking(
                db=db,
                task_id=task_id,
                workflow_node_id=task.current_node_id
            )
            if current_tracking:
                current_sla = current_tracking[0]  # Most recent
        
        # Count by status
        breached_count = sum(1 for t in all_tracking if t.sla_status == SLAStatus.BREACHED)
        met_count = sum(1 for t in all_tracking if t.sla_status == SLAStatus.MET)
        pending_count = sum(1 for t in all_tracking if t.sla_status in [SLAStatus.PENDING, SLAStatus.IN_PROGRESS])
        
        return {
            "task_id": task_id,
            "current_sla": current_sla,
            "all_sla_tracking": all_tracking,
            "breached_count": breached_count,
            "met_count": met_count,
            "pending_count": pending_count
        }
    
    @staticmethod
    def check_and_update_sla_breach(
        db: Session,
        task_id: int,
        company_id: int
    ) -> dict:
        """Check and update SLA breach status for task"""
        # Verify task exists
        task = TaskWorkflowRepository.get_task_with_workflow(db, task_id, company_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Get all active SLA tracking
        all_tracking = SLARepository.get_task_sla_tracking(db, task_id)
        now = datetime.utcnow()
        updated_count = 0
        breached_count = 0
        
        for tracking in all_tracking:
            if tracking.sla_status in [SLAStatus.PENDING, SLAStatus.IN_PROGRESS]:
                # Check if breached
                breached = False
                
                if tracking.resolution_deadline and now > tracking.resolution_deadline:
                    breached = True
                elif tracking.response_deadline and now > tracking.response_deadline:
                    # Response deadline breached - mark as in progress (escalation may be needed)
                    if tracking.sla_status == SLAStatus.PENDING:
                        SLARepository.update_sla_status(
                            db=db,
                            sla_tracking_id=tracking.id,
                            status=SLAStatus.IN_PROGRESS
                        )
                        updated_count += 1
                
                if breached:
                    SLARepository.update_sla_status(
                        db=db,
                        sla_tracking_id=tracking.id,
                        status=SLAStatus.BREACHED,
                        breached_at=now
                    )
                    breached_count += 1
                    updated_count += 1
        
        logger.info(f"Checked SLA for task {task_id}: {breached_count} breached, {updated_count} updated")
        
        return {
            "task_id": task_id,
            "breached_count": breached_count,
            "updated_count": updated_count,
            "checked_at": now
        }

