"""
Migration — add custom_role_id + permissions columns to users.
Run once: python migrate_user_permissions.py
Safe to re-run.
"""
import sys
import logging
from sqlalchemy import inspect, text

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run():
    from app.core.config import settings
    from app.db.session import engine

    logger.info("=== ManaHRMS User Permissions Migration ===")
    logger.info(f"Database: {settings.DATABASE_URL[:50]}...")

    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("users")}

    statements = []
    if "custom_role_id" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN custom_role_id INTEGER "
            "REFERENCES roles(id) ON DELETE SET NULL"
        )
        statements.append(
            "CREATE INDEX IF NOT EXISTS ix_users_custom_role_id ON users (custom_role_id)"
        )
    if "permissions" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN permissions JSONB NOT NULL DEFAULT '{}'::jsonb"
        )

    if not statements:
        logger.info("Columns already exist. Nothing to do.")
        return

    with engine.begin() as conn:
        for stmt in statements:
            logger.info(f"Running: {stmt}")
            conn.execute(text(stmt))

    logger.info("Done.")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)
