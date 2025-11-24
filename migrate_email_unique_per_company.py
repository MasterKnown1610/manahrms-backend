"""
Migration script to:
1. Add deleted_at column to employees table
2. Change email uniqueness from global to per-company for employees and users tables
3. Create composite unique constraints for (company_id, email)

Run this script to update your database schema.
"""

from sqlalchemy import text, inspect
from sqlalchemy.exc import ProgrammingError
from app.db.session import engine


def run_migration():
    """
    Migrate database schema to support:
    - Email uniqueness per company (not globally)
    - Soft delete for employees (deleted_at field)
    """
    print("=" * 70)
    print("Migration: Make Email Unique Per Company & Add Soft Delete")
    print("=" * 70)
    
    try:
        inspector = inspect(engine)
        
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                # Step 1: Add deleted_at column to employees table if it doesn't exist
                print("\n1. Adding deleted_at column to employees table...")
                try:
                    conn.execute(text("""
                        ALTER TABLE employees 
                        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;
                    """))
                    print("   ✅ deleted_at column added")
                except Exception as e:
                    print(f"   ⚠️  deleted_at column may already exist: {e}")
                
                # Step 2: Create index on deleted_at for better query performance
                print("\n2. Creating index on deleted_at...")
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_employees_deleted_at 
                        ON employees(deleted_at);
                    """))
                    print("   ✅ Index created")
                except Exception as e:
                    print(f"   ⚠️  Index may already exist: {e}")
                
                # Step 3: Drop existing unique constraint on employees.email (if exists)
                print("\n3. Dropping existing unique constraint on employees.email...")
                try:
                    # Check if unique constraint exists
                    result = conn.execute(text("""
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE table_name = 'employees' 
                        AND constraint_type = 'UNIQUE'
                        AND constraint_name LIKE '%email%';
                    """))
                    constraints = result.fetchall()
                    
                    for constraint in constraints:
                        constraint_name = constraint[0]
                        print(f"   Dropping constraint: {constraint_name}")
                        conn.execute(text(f"""
                            ALTER TABLE employees 
                            DROP CONSTRAINT IF EXISTS {constraint_name};
                        """))
                    print("   ✅ Unique constraint on email removed")
                except Exception as e:
                    print(f"   ⚠️  Error removing constraint (may not exist): {e}")
                
                # Step 4: Create composite unique constraint on (company_id, email) for employees
                print("\n4. Creating composite unique constraint on (company_id, email) for employees...")
                try:
                    conn.execute(text("""
                        ALTER TABLE employees 
                        ADD CONSTRAINT uq_employee_company_email 
                        UNIQUE (company_id, email);
                    """))
                    print("   ✅ Composite unique constraint created for employees")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print("   ⚠️  Constraint may already exist")
                    else:
                        raise e
                
                # Step 5: Drop existing unique constraint on users.email (if exists)
                print("\n5. Dropping existing unique constraint on users.email...")
                try:
                    result = conn.execute(text("""
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE table_name = 'users' 
                        AND constraint_type = 'UNIQUE'
                        AND constraint_name LIKE '%email%';
                    """))
                    constraints = result.fetchall()
                    
                    for constraint in constraints:
                        constraint_name = constraint[0]
                        print(f"   Dropping constraint: {constraint_name}")
                        conn.execute(text(f"""
                            ALTER TABLE users 
                            DROP CONSTRAINT IF EXISTS {constraint_name};
                        """))
                    print("   ✅ Unique constraint on email removed")
                except Exception as e:
                    print(f"   ⚠️  Error removing constraint (may not exist): {e}")
                
                # Step 6: Create composite unique constraint on (company_id, email) for users
                print("\n6. Creating composite unique constraint on (company_id, email) for users...")
                try:
                    conn.execute(text("""
                        ALTER TABLE users 
                        ADD CONSTRAINT uq_user_company_email 
                        UNIQUE (company_id, email);
                    """))
                    print("   ✅ Composite unique constraint created for users")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print("   ⚠️  Constraint may already exist")
                    else:
                        raise e
                
                # Commit transaction
                trans.commit()
                
                print("\n" + "=" * 70)
                print("✅ Migration completed successfully!")
                print("=" * 70)
                print("\nChanges applied:")
                print("  - Added deleted_at column to employees table")
                print("  - Changed email uniqueness from global to per-company")
                print("  - Employees and users can now use the same email across different companies")
                print("  - Soft delete functionality enabled for employees")
                print("\n")
                
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ Migration failed: {e}")
                print("Transaction rolled back.")
                raise e
                
    except Exception as e:
        print(f"\n❌ Migration error: {e}")
        return False


if __name__ == "__main__":
    run_migration()

