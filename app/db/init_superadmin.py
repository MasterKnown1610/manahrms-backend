"""
Initialize SuperAdmin account.
Run this script once to create the platform superadmin user.

Usage:
    python -m app.db.init_superadmin
"""
import sys
import os

# Add project root to path so imports work when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.base import Base
from app.core.security import hash_password_for_storage
import logging

logger = logging.getLogger(__name__)

SUPERADMIN_EMAIL = "admin@manahrms.com"
SUPERADMIN_USERNAME = "superadmin"
SUPERADMIN_FULL_NAME = "ManaHRMS Platform Admin"
SUPERADMIN_PASSWORD = "manahrms@1610"


def create_superadmin(db: Session) -> None:
    # Import here so Base is already set up
    from app.api.v1.models.superadmin_model import SuperAdmin

    existing = db.query(SuperAdmin).filter(SuperAdmin.email == SUPERADMIN_EMAIL).first()
    if existing:
        print(f"SuperAdmin already exists: {SUPERADMIN_EMAIL}")
        return

    hashed = hash_password_for_storage(SUPERADMIN_PASSWORD)
    admin = SuperAdmin(
        email=SUPERADMIN_EMAIL,
        username=SUPERADMIN_USERNAME,
        full_name=SUPERADMIN_FULL_NAME,
        hashed_password=hashed,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    print(f"SuperAdmin created successfully!")
    print(f"  Email    : {SUPERADMIN_EMAIL}")
    print(f"  Username : {SUPERADMIN_USERNAME}")
    print(f"  Password : {SUPERADMIN_PASSWORD}")


def init_superadmin() -> None:
    from app.db.session import engine
    # Create super_admins table if it doesn't exist
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        create_superadmin(db)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_superadmin()
