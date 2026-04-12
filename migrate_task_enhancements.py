"""
Migration: Task Enhancements
- Adds `branch` column to tasks table
- Creates task_permissions table
- Creates task_comments table
- Creates task_commits table

Run once:  python migrate_task_enhancements.py
"""

import sys
import logging
from sqlalchemy import text
from app.db.session import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


MIGRATIONS = [
    # 1. Add branch column to tasks (idempotent)
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='tasks' AND column_name='branch'
        ) THEN
            ALTER TABLE tasks ADD COLUMN branch VARCHAR(255);
        END IF;
    END$$;
    """,

    # 2. task_permissions table
    """
    CREATE TABLE IF NOT EXISTS task_permissions (
        id SERIAL PRIMARY KEY,
        company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        granted_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        CONSTRAINT uq_task_permission_company_user UNIQUE (company_id, user_id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_task_permissions_company_id ON task_permissions(company_id);",
    "CREATE INDEX IF NOT EXISTS ix_task_permissions_user_id ON task_permissions(user_id);",

    # 3. task_comments table
    """
    CREATE TABLE IF NOT EXISTS task_comments (
        id SERIAL PRIMARY KEY,
        task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
        user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_task_comments_task_id ON task_comments(task_id);",
    "CREATE INDEX IF NOT EXISTS ix_task_comments_company_id ON task_comments(company_id);",

    # 4. task_commits table
    """
    CREATE TABLE IF NOT EXISTS task_commits (
        id SERIAL PRIMARY KEY,
        task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
        branch VARCHAR(255),
        commit_hash VARCHAR(100),
        commit_message TEXT,
        author_name VARCHAR(255),
        commit_url VARCHAR(500),
        committed_at TIMESTAMP WITHOUT TIME ZONE,
        added_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_task_commits_task_id ON task_commits(task_id);",
    "CREATE INDEX IF NOT EXISTS ix_task_commits_company_id ON task_commits(company_id);",
]


def run():
    with engine.begin() as conn:
        for i, sql in enumerate(MIGRATIONS, 1):
            logger.info("Running migration step %d …", i)
            conn.execute(text(sql))
    logger.info("All migration steps completed successfully.")


if __name__ == "__main__":
    try:
        run()
        sys.exit(0)
    except Exception as e:
        logger.error("Migration failed: %s", e, exc_info=True)
        sys.exit(1)
