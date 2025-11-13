from sqlalchemy.ext.declarative import declarative_base

# Create Base class for all models
Base = declarative_base()

# Import all models here so they are registered with Base
# This ensures tables are created when Base.metadata.create_all() is called
# Import order matters due to foreign key relationships

from app.api.v1.models.company_model import Company  # noqa
from app.api.v1.models.department_model import Department  # noqa
from app.api.v1.models.employee_model import Employee  # noqa
from app.api.v1.models.user_model import User  # noqa
from app.api.v1.models.task_model import Task  # noqa
