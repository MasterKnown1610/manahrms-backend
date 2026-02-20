from sqlalchemy import text, inspect
from sqlalchemy.exc import ProgrammingError
import logging
from app.db.session import engine
from app.db.base import Base

logger = logging.getLogger(__name__)


def initialize_database_on_startup():
    try:
        # Check which tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        # Define all required tables
        required_tables = [
            'companies',
            'users',
            'employees',
            'departments',
            'department_access',
            'projects',
            'tasks',
            'attendances',
            'employee_attachments',  # Employee file attachments
            'vector_store',  # For RAG with pgvector
            'leave_types',
            'leave_requests',
            'leave_balances',  # Leave management
            'chat_rooms',  # Chat functionality
            'chat_room_members',  # Chat room members
            'chat_messages'  # Chat messages
        ]
        
        # Check for missing tables
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Enable pgvector extension if needed (for vector_store table)
                # Note: For Neon DB, extension should be enabled via SQL Editor first
                try:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                    # Commit the extension creation
                    trans.commit()
                    # Start a new transaction for table operations
                    trans = conn.begin()
                except Exception as e:
                    # Extension might not be available or already enabled
                    # For Neon DB, user needs to enable it via SQL Editor
                    trans.rollback()
                    # Start a new transaction for table operations
                    trans = conn.begin()
                    error_msg = str(e).lower()
                    # pgvector extension might not be available
                    pass
                    # Continue with table creation anyway
                
                # If companies table doesn't exist, create all tables
                if 'companies' not in existing_tables:
                    # Table doesn't exist, create all tables
                    Base.metadata.create_all(bind=engine)
                    trans.commit()
                    return True
                
                # If any required table is missing, create missing tables
                if missing_tables:
                    Base.metadata.create_all(bind=engine)
                    trans.commit()
                    
                    # After creating tables, check if tasks table needs project_id column
                    # Refresh inspector to get updated table list
                    inspector = inspect(engine)
                    current_tables = inspector.get_table_names()
                    if 'tasks' in current_tables and 'projects' in current_tables:
                        tasks_columns = [col['name'] for col in inspector.get_columns('tasks')]
                        if 'project_id' not in tasks_columns:
                            with engine.connect() as conn2:
                                trans2 = conn2.begin()
                                try:
                                    conn2.execute(text("""
                                        ALTER TABLE tasks 
                                        ADD COLUMN IF NOT EXISTS project_id INTEGER;
                                    """))
                                    # Add foreign key constraint
                                    try:
                                        conn2.execute(text("""
                                            ALTER TABLE tasks 
                                            ADD CONSTRAINT tasks_project_id_fkey 
                                            FOREIGN KEY (project_id) 
                                            REFERENCES projects(id) ON DELETE SET NULL;
                                        """))
                                    except ProgrammingError:
                                        pass  # Constraint might already exist
                                    # Create index
                                    conn2.execute(text("""
                                        CREATE INDEX IF NOT EXISTS tasks_project_id_idx 
                                        ON tasks(project_id) WHERE project_id IS NOT NULL;
                                    """))
                                    trans2.commit()
                                except Exception as e:
                                    trans2.rollback()
                                    pass
                    
                    return True
                
                # All tables exist, check for missing columns
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
                
                # Check for project_id column in tasks table (if tasks table exists)
                # This should be checked regardless of companies table status
                current_tables = inspector.get_table_names()
                
                # Check for missing columns in employees table
                employees_columns = []
                employees_missing_columns = []
                if 'employees' in current_tables:
                    employees_columns = [col['name'] for col in inspector.get_columns('employees')]
                    employees_required_columns = {
                        'gender': 'gender',
                        'address': 'TEXT',
                        'city': 'VARCHAR(100)',
                        'pin_code': 'VARCHAR(10)',
                        'notes': 'TEXT'
                    }
                    
                    for col_name in employees_required_columns.keys():
                        if col_name not in employees_columns:
                            employees_missing_columns.append(col_name)
                tasks_updated = False
                if 'tasks' in current_tables:
                    tasks_columns = [col['name'] for col in inspector.get_columns('tasks')]
                    if 'project_id' not in tasks_columns:
                        # First ensure projects table exists (it should, but check)
                        if 'projects' in current_tables:
                            conn.execute(text("""
                                ALTER TABLE tasks 
                                ADD COLUMN IF NOT EXISTS project_id INTEGER;
                            """))
                            # Add foreign key constraint
                            try:
                                conn.execute(text("""
                                    ALTER TABLE tasks 
                                    ADD CONSTRAINT tasks_project_id_fkey 
                                    FOREIGN KEY (project_id) 
                                    REFERENCES projects(id) ON DELETE SET NULL;
                                """))
                            except ProgrammingError:
                                # Constraint might already exist, try to drop and recreate
                                try:
                                    conn.execute(text("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_project_id_fkey;"))
                                    conn.execute(text("""
                                        ALTER TABLE tasks 
                                        ADD CONSTRAINT tasks_project_id_fkey 
                                        FOREIGN KEY (project_id) 
                                        REFERENCES projects(id) ON DELETE SET NULL;
                                    """))
                                except ProgrammingError:
                                    pass  # Skip if still fails
                            # Create index for project_id
                            conn.execute(text("""
                                CREATE INDEX IF NOT EXISTS tasks_project_id_idx 
                                ON tasks(project_id) WHERE project_id IS NOT NULL;
                            """))
                            tasks_updated = True
                
                if not missing_columns and not employees_missing_columns:
                    if tasks_updated:
                        trans.commit()
                        return True
                    trans.commit()
                    return True
                
                # Add missing columns for companies table
                if missing_columns:
                    # Create CompanyType enum if it doesn't exist
                    if 'company_type' in missing_columns:
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
                
                # Add missing columns for employees table
                if employees_missing_columns:
                    # Create Gender enum if it doesn't exist
                    if 'gender' in employees_missing_columns:
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
                    
                    # Add missing columns
                    employees_required_columns = {
                        'gender': 'gender',
                        'address': 'TEXT',
                        'city': 'VARCHAR(100)',
                        'pin_code': 'VARCHAR(10)',
                        'notes': 'TEXT'
                    }
                    
                    for col_name in employees_missing_columns:
                        col_type = employees_required_columns[col_name]
                        
                        if col_type == 'gender':
                            conn.execute(text(f"""
                                ALTER TABLE employees 
                                ADD COLUMN IF NOT EXISTS {col_name} {col_type};
                            """))
                        else:
                            conn.execute(text(f"""
                                ALTER TABLE employees 
                                ADD COLUMN IF NOT EXISTS {col_name} {col_type};
                            """))
                
                # Set default values for existing rows (only if there are any)
                if missing_columns:
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
                                pass
                    else:
                        pass
                
                # Note: Employee new columns don't need default values as they're all nullable
                
                # Add NOT NULL constraints if needed (only if no existing rows)
                if missing_columns:
                    result = conn.execute(text("SELECT COUNT(*) FROM companies;"))
                    total_rows = result.scalar()
                    
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
                
                # Create indexes if they don't exist
                if missing_columns:
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
                
                if missing_columns or employees_missing_columns:
                    return True
                
                return True
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        # Try to drop and recreate tables as fallback (only if migration failed)
        try:
            with engine.connect() as conn:
                # Drop all tables
                Base.metadata.drop_all(bind=engine)
                # Create all tables fresh
                Base.metadata.create_all(bind=engine)
            return True
        except Exception as fallback_error:
            return False
