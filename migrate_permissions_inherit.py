"""
Migration — make users.permissions nullable (NULL = inherit role live).
Clears existing employee permission snapshots so they inherit from role again.

Run: python migrate_permissions_inherit.py
"""
import sys
import logging
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run():
    from app.core.config import settings
    from app.db.session import engine

    logger.info("=== ManaHRMS Permissions Inherit Migration ===")
    logger.info(f"Database: {settings.DATABASE_URL[:50]}...")

    with engine.begin() as conn:
        logger.info("Allowing NULL on users.permissions...")
        conn.execute(text("ALTER TABLE users ALTER COLUMN permissions DROP NOT NULL"))
        conn.execute(text("ALTER TABLE users ALTER COLUMN permissions SET DEFAULT NULL"))

        # Drop stale snapshots so employees inherit live role permissions again
        result = conn.execute(
            text(
                "UPDATE users SET permissions = NULL "
                "WHERE role::text = 'EMPLOYEE'"
            )
        )
        logger.info(f"Cleared permission snapshots for {result.rowcount} employee users")

    logger.info("Done. Employees now inherit from department roles until individually overridden.")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)
