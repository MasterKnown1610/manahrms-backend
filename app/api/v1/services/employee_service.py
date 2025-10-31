from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import date

from app.api.v1.models.employee_model import Employee
from app.api.v1.models.user_model import User, UserRole
from app.api.v1.models.department_model import Department
from app.api.v1.schemas.employee_schema import EmployeeCreate, EmployeeUpdate
from app.core.security import get_password_hash


class EmployeeService:
    """
    Service class for employee management operations.
    Handles employee CRUD and related operations.
    """
    
    @staticmethod
    def create_employee(db: Session, employee_data: EmployeeCreate, company_id: int) -> tuple[Employee, User, str]:
        """
        Create a new employee with login credentials.
        
        Args:
            db: Database session
            employee_data: Employee creation data
            company_id: Company ID the employee belongs to
            
        Returns:
            Tuple of (employee object, user object, temporary password)
            
        Raises:
            HTTPException: If employee code or email already exists
        """
        # Check if employee code already exists
        existing_code = db.query(Employee).filter(
            Employee.employee_code == employee_data.employee_code
        ).first()
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee code already exists"
            )
        
        # Check if email already exists
        existing_email = db.query(Employee).filter(
            Employee.email == employee_data.email
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee email already registered"
            )
        
        # Check if department exists (if provided)
        if employee_data.department_id:
            department = db.query(Department).filter(
                Department.id == employee_data.department_id,
                Department.company_id == company_id
            ).first()
            if not department:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Department not found"
                )
        
        try:
            # Create employee record
            new_employee = Employee(
                company_id=company_id,
                employee_code=employee_data.employee_code,
                first_name=employee_data.first_name,
                last_name=employee_data.last_name,
                email=employee_data.email,
                phone=employee_data.phone,
                date_of_birth=employee_data.date_of_birth,
                position=employee_data.position,
                hire_date=employee_data.hire_date,
                salary=employee_data.salary,
                department_id=employee_data.department_id,
                is_active=True
            )
            db.add(new_employee)
            db.flush()  # Get employee ID
            
            # Create user account for employee
            # Generate username from employee code or email
            username = employee_data.employee_code.lower().replace(" ", "_")
            
            # Check if username already exists, if so append employee ID
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                username = f"{username}_{new_employee.id}"
            
            # Hash the initial password
            hashed_password = get_password_hash(employee_data.initial_password)
            
            employee_user = User(
                company_id=company_id,
                email=employee_data.email,
                username=username,
                full_name=f"{employee_data.first_name} {employee_data.last_name}",
                hashed_password=hashed_password,
                role=UserRole.EMPLOYEE,
                employee_id=new_employee.id,
                is_active=True,
                is_superuser=False,
                force_password_change=True  # Force password change on first login
            )
            db.add(employee_user)
            
            db.commit()
            db.refresh(new_employee)
            db.refresh(employee_user)
            
            return new_employee, employee_user, employee_data.initial_password
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create employee: {str(e)}"
            )
    
    @staticmethod
    def get_employee_by_id(db: Session, employee_id: int, company_id: int) -> Employee:
        """
        Get employee by ID.
        
        Args:
            db: Database session
            employee_id: Employee ID
            company_id: Company ID to ensure employee belongs to the company
            
        Returns:
            Employee object
            
        Raises:
            HTTPException: If employee not found
        """
        employee = db.query(Employee).filter(
            Employee.id == employee_id,
            Employee.company_id == company_id
        ).first()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        return employee
    
    @staticmethod
    def get_all_employees(
        db: Session, 
        company_id: int, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[Employee]:
        """
        Get all employees for a company.
        
        Args:
            db: Database session
            company_id: Company ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Filter by active status (optional)
            
        Returns:
            List of employee objects
        """
        query = db.query(Employee).filter(Employee.company_id == company_id)
        
        if is_active is not None:
            query = query.filter(Employee.is_active == is_active)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update_employee(
        db: Session, 
        employee_id: int, 
        company_id: int, 
        employee_data: EmployeeUpdate
    ) -> Employee:
        """
        Update employee information.
        
        Args:
            db: Database session
            employee_id: Employee ID
            company_id: Company ID
            employee_data: Updated employee data
            
        Returns:
            Updated employee object
            
        Raises:
            HTTPException: If employee not found
        """
        employee = EmployeeService.get_employee_by_id(db, employee_id, company_id)
        
        # Update only provided fields
        update_data = employee_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(employee, field, value)
        
        db.commit()
        db.refresh(employee)
        
        return employee
    
    @staticmethod
    def delete_employee(db: Session, employee_id: int, company_id: int) -> None:
        """
        Soft delete an employee (set is_active to False).
        
        Args:
            db: Database session
            employee_id: Employee ID
            company_id: Company ID
            
        Raises:
            HTTPException: If employee not found
        """
        employee = EmployeeService.get_employee_by_id(db, employee_id, company_id)
        employee.is_active = False
        
        # Also deactivate the associated user account
        if employee.user:
            employee.user.is_active = False
        
        db.commit()
    
    @staticmethod
    def get_employee_by_code(db: Session, employee_code: str, company_id: int) -> Optional[Employee]:
        """
        Get employee by employee code.
        
        Args:
            db: Database session
            employee_code: Employee code
            company_id: Company ID
            
        Returns:
            Employee object or None
        """
        return db.query(Employee).filter(
            Employee.employee_code == employee_code,
            Employee.company_id == company_id
        ).first()

