"""
Database initialization utility
Automatically creates tables and adds missing columns
"""
from sqlalchemy import text, inspect
from sqlalchemy.exc import ProgrammingError
from app.db.session import engine
from app.db.base import Base


def init_database():
    """
    Initialize database: create tables if they don't exist,
    and add missing columns if tables exist but are outdated.
    """
    try:
        # Check if companies table exists
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                if 'companies' not in tables:
                    # Table doesn't exist, create all tables
                    print("📦 Creating all database tables...")
                    Base.metadata.create_all(bind=engine)
                    print("✅ All tables created successfully!")
                    trans.commit()
                    return True
                
                # Table exists, check for missing columns
                print("🔍 Checking for missing columns...")
                companies_columns = [col['name'] for col in inspector.get_columns('companies')]
                
                missing_columns = []
                required_columns = {
                    'company_code': 'VARCHAR(50)',
                    'company_type': 'companytype',
                    'company_type_other': 'VARCHAR(255)',
                    'gst_number': 'VARCHAR(50)',
                    'pan_number': 'VARCHAR(50)'
                }
                
                for col_name in required_columns.keys():
                    if col_name not in companies_columns:
                        missing_columns.append(col_name)
                
                if not missing_columns:
                    print("✅ All columns exist. Database is up to date!")
                    trans.commit()
                    return True
                
                # Add missing columns
                print(f"📝 Adding {len(missing_columns)} missing column(s)...")
                
                # Create CompanyType enum if it doesn't exist
                if 'company_type' in missing_columns:
                    print("   Creating CompanyType enum...")
                    # Create enum if it doesn't exist (using DO block to handle if exists)
                    conn.execute(text("""
                        DO $$ BEGIN
                            CREATE TYPE companytype AS ENUM (
                                'Solo Proprietor',
                                'Organization',
                                'Private Limited',
                                'LLP',
                                'Partnership',
                                'Public Limited',
                                'Other'
                            );
                        EXCEPTION
                            WHEN duplicate_object THEN null;
                        END $$;
                    """))
                
                # Add missing columns
                for col_name in missing_columns:
                    col_type = required_columns[col_name]
                    print(f"   Adding column: {col_name} ({col_type})...")
                    
                    if col_type == 'companytype':
                        conn.execute(text(f"""
                            ALTER TABLE companies 
                            ADD COLUMN IF NOT EXISTS {col_name} {col_type};
                        """))
                    else:
                        conn.execute(text(f"""
                            ALTER TABLE companies 
                            ADD COLUMN IF NOT EXISTS {col_name} {col_type};
                        """))
                
                # Set default values for existing rows (only if there are any)
                print("   Setting default values for existing rows...")
                
                # Check if there are any rows at all
                result = conn.execute(text("SELECT COUNT(*) FROM companies;"))
                total_rows = result.scalar()
                
                if total_rows > 0:
                    # Check which rows need defaults
                    result = conn.execute(text("""
                        SELECT COUNT(*) FROM companies 
                        WHERE company_code IS NULL OR pan_number IS NULL OR company_type IS NULL;
                    """))
                    rows_needing_defaults = result.scalar()
                    
                    if rows_needing_defaults > 0:
                        # First set company_code and pan_number (non-enum fields)
                        conn.execute(text("""
                            UPDATE companies 
                            SET 
                                company_code = COALESCE(company_code, 'CMP' || LPAD(id::text, 8, '0')),
                                pan_number = COALESCE(pan_number, 'NOT_SET')
                            WHERE company_code IS NULL OR pan_number IS NULL;
                        """))
                        
                        # Then set company_type separately (enum field)
                        # Only update if company_type column exists and is NULL
                        try:
                            conn.execute(text("""
                                UPDATE companies 
                                SET company_type = CAST('Organization' AS companytype)
                                WHERE company_type IS NULL;
                            """))
                        except Exception as e:
                            # If enum update fails, skip it - columns are added anyway
                            print(f"   Warning: Could not set default company_type: {e}")
                        
                        print(f"   Updated {rows_needing_defaults} existing row(s)")
                else:
                    print("   No existing rows to update")
                
                # Add NOT NULL constraints if needed (only if no existing rows)
                print("   Adding constraints...")
                
                if total_rows == 0:
                    # Only set NOT NULL if there are no rows (safe to do)
                    try:
                        conn.execute(text("""
                            ALTER TABLE companies 
                            ALTER COLUMN company_code SET NOT NULL;
                        """))
                    except ProgrammingError:
                        pass  # Already NOT NULL or has NULL values
                    
                    try:
                        conn.execute(text("""
                            ALTER TABLE companies 
                            ALTER COLUMN company_type SET NOT NULL;
                        """))
                    except ProgrammingError:
                        pass  # Already NOT NULL or has NULL values
                    
                    try:
                        conn.execute(text("""
                            ALTER TABLE companies 
                            ALTER COLUMN pan_number SET NOT NULL;
                        """))
                    except ProgrammingError:
                        pass  # Already NOT NULL or has NULL values
                else:
                    print("   Skipping NOT NULL constraints (existing rows present)")
                
                # Create indexes if they don't exist
                print("   Creating indexes...")
                
                conn.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS companies_company_code_key 
                    ON companies(company_code);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS companies_gst_number_idx 
                    ON companies(gst_number) WHERE gst_number IS NOT NULL;
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS companies_pan_number_idx 
                    ON companies(pan_number);
                """))
                
                # Commit transaction
                trans.commit()
                
                print(f"✅ Successfully added {len(missing_columns)} column(s)!")
                print("   - company_code")
                print("   - company_type")
                print("   - company_type_other")
                print("   - gst_number")
                print("   - pan_number")
                
                return True
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        # Try to drop and recreate tables as fallback (only if migration failed)
        try:
            print("🔄 Attempting to recreate tables (this will drop existing tables)...")
            with engine.connect() as conn:
                # Drop all tables
                Base.metadata.drop_all(bind=engine)
                # Create all tables fresh
                Base.metadata.create_all(bind=engine)
            print("✅ Tables recreated using fallback method!")
            return True
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            return False
