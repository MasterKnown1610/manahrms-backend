#!/usr/bin/env python3
"""
Create employee_attachments table if it doesn't exist
"""
from app.db.base import Base
from app.db.session import engine
from app.api.v1.models.employee_attachment_model import EmployeeAttachment

# Import all models to ensure they're registered
from app.api.v1.models import *  # noqa

print("Creating employee_attachments table...")

try:
    # Create only the employee_attachments table
    EmployeeAttachment.__table__.create(bind=engine, checkfirst=True)
    print("✅ employee_attachments table created successfully!")
except Exception as e:
    print(f"❌ Error creating table: {e}")
    # Try creating all tables
    try:
        print("Attempting to create all missing tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
    except Exception as e2:
        print(f"❌ Error: {e2}")
