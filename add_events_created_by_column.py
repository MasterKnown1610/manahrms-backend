"""
Add events.created_by (nullable FK to users.id) to match Event ORM model.

Run from project root: python add_events_created_by_column.py
"""

from sqlalchemy import text, inspect

from app.db.session import engine


def run_migration() -> bool:
    print("=" * 70)
    print("Migration: Add created_by to events")
    print("=" * 70)

    try:
        inspector = inspect(engine)
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                if "events" not in inspector.get_table_names():
                    print("\n[SKIP] Table 'events' does not exist.")
                    trans.rollback()
                    return False

                cols = [c["name"] for c in inspector.get_columns("events")]
                if "created_by" in cols:
                    trans.commit()
                    print("\n[OK] Column events.created_by already exists.")
                    return True

                print("\nAdding column created_by...")
                conn.execute(
                    text(
                        """
                        ALTER TABLE events
                        ADD COLUMN created_by INTEGER NULL
                        REFERENCES users (id) ON DELETE SET NULL;
                        """
                    )
                )
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_events_created_by ON events (created_by);"
                    )
                )
                trans.commit()
                print("[OK] events.created_by added and index created.")
                print("=" * 70)
                return True
            except Exception as e:
                trans.rollback()
                print(f"\n[FAIL] Migration failed: {e}")
                raise
    except Exception as e:
        print(f"\n[FAIL] Database error: {e}")
        return False


if __name__ == "__main__":
    run_migration()
