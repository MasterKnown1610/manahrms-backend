"""
Migration script — creates the roles table.
Run once: python migrate_roles.py

Safe to re-run (uses CREATE TABLE IF NOT EXISTS via SQLAlchemy checkfirst=True).
Does NOT drop or alter any existing table.
"""
import sys
import logging
from sqlalchemy import inspect

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run():
    from app.core.config import settings
    from app.db.session import engine
    from app.db.base import Base
    from app.api.v1.models.role_model import Role  # noqa: F401 — register metadata

    table_name = "roles"
    inspector = inspect(engine)
    existing = inspector.get_table_names()

    logger.info("=== ManaHRMS Roles Migration ===")
    logger.info(f"Database: {settings.DATABASE_URL[:50]}...")

    if table_name in existing:
        logger.info(f"Table '{table_name}' already exists. Nothing to do.")
        return

    logger.info(f"Creating table: {table_name}")
    Base.metadata.create_all(
        engine,
        checkfirst=True,
        tables=[Base.metadata.tables[table_name]],
    )

    inspector2 = inspect(engine)
    if table_name in inspector2.get_table_names():
        logger.info(f"  ✓ {table_name}")
    else:
        logger.error(f"  ✗ {table_name} — FAILED TO CREATE")
        sys.exit(1)

    logger.info("Done.")


if __name__ == "__main__":
    run()
