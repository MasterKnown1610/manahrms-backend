"""
Migration script to add new fields to employees table:
- gender (enum: male, female, other, prefer_not_to_say)
- address (TEXT)
- city (VARCHAR(100))
- pin_code (VARCHAR(10))
- notes (TEXT)

Run this script to update your database schema.
"""

from sqlalchemy import text, inspect
from sqlalchemy.exc import ProgrammingError
from app.db.session import engine


def run_migration():
    """
    Migrate database schema to add new employee fields.
    """
    print("=" * 70)
    print("Migration: Add Gender, Address, City, Pin Code, Notes to Employees")
    print("=" * 70)
    
    try:
        inspector = inspect(engine)
        
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                # Check if employees table exists
                existing_tables = inspector.get_table_names()
                if 'employees' not in existing_tables:
                    print("\n❌ Employees table does not exist!")
                    print("   Please create the employees table first.")
                    trans.rollback()
                    return False
                
                # Get current columns
                employees_columns = [col['name'] for col in inspector.get_columns('employees')]
                
                # Step 1: Create Gender enum if it doesn't exist
                print("\n1. Creating Gender enum...")
                try:
                    conn.execute(text("""
                        DO $$ BEGIN
                            CREATE TYPE gender AS ENUM (
                                'male',
                                'female',
                                'other',
                                'prefer_not_to_say'
                            );
                        EXCEPTION
                            WHEN duplicate_object THEN null;
                        END $$;
                    """))
                    print("   ✅ Gender enum created/verified")
                except Exception as e:
                    print(f"   ⚠️  Gender enum may already exist: {e}")
                
                # Step 2: Add gender column
                if 'gender' not in employees_columns:
                    print("\n2. Adding gender column...")
                    try:
                        conn.execute(text("""
                            ALTER TABLE employees 
                            ADD COLUMN gender gender;
                        """))
                        print("   ✅ gender column added")
                    except Exception as e:
                        print(f"   ❌ Failed to add gender column: {e}")
                        trans.rollback()
                        return False
                else:
                    print("\n2. gender column already exists, skipping...")
                
                # Step 3: Add address column
                if 'address' not in employees_columns:
                    print("\n3. Adding address column...")
                    try:
                        conn.execute(text("""
                            ALTER TABLE employees 
                            ADD COLUMN address TEXT;
                        """))
                        print("   ✅ address column added")
                    except Exception as e:
                        print(f"   ❌ Failed to add address column: {e}")
                        trans.rollback()
                        return False
                else:
                    print("\n3. address column already exists, skipping...")
                
                # Step 4: Add city column
                if 'city' not in employees_columns:
                    print("\n4. Adding city column...")
                    try:
                        conn.execute(text("""
                            ALTER TABLE employees 
                            ADD COLUMN city VARCHAR(100);
                        """))
                        print("   ✅ city column added")
                    except Exception as e:
                        print(f"   ❌ Failed to add city column: {e}")
                        trans.rollback()
                        return False
                else:
                    print("\n4. city column already exists, skipping...")
                
                # Step 5: Add pin_code column
                if 'pin_code' not in employees_columns:
                    print("\n5. Adding pin_code column...")
                    try:
                        conn.execute(text("""
                            ALTER TABLE employees 
                            ADD COLUMN pin_code VARCHAR(10);
                        """))
                        print("   ✅ pin_code column added")
                    except Exception as e:
                        print(f"   ❌ Failed to add pin_code column: {e}")
                        trans.rollback()
                        return False
                else:
                    print("\n5. pin_code column already exists, skipping...")
                
                # Step 6: Add notes column
                if 'notes' not in employees_columns:
                    print("\n6. Adding notes column...")
                    try:
                        conn.execute(text("""
                            ALTER TABLE employees 
                            ADD COLUMN notes TEXT;
                        """))
                        print("   ✅ notes column added")
                    except Exception as e:
                        print(f"   ❌ Failed to add notes column: {e}")
                        trans.rollback()
                        return False
                else:
                    print("\n6. notes column already exists, skipping...")
                
                # Commit transaction
                trans.commit()
                
                print("\n" + "=" * 70)
                print("✅ Migration completed successfully!")
                print("=" * 70)
                print("\nNew fields added to employees table:")
                print("  - gender (enum)")
                print("  - address (TEXT)")
                print("  - city (VARCHAR(100))")
                print("  - pin_code (VARCHAR(10))")
                print("  - notes (TEXT)")
                print("\nAll fields are nullable and can be set when creating/updating employees.")
                
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ Migration failed: {e}")
                raise e
                
    except Exception as e:
        print(f"\n❌ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    run_migration()
