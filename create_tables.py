import sys
from sqlalchemy import inspect
from app.db.session import engine
from app.db.base import Base
# from app.core.config import settings

def drop_all_database_tables_with_confirmation():
    print("\nWARNING: This will delete all existing data!")
    confirmation = input("Type 'yes' to proceed: ")
    
    if confirmation.lower() == 'yes':
        Base.metadata.drop_all(bind=engine)
        print("All tables dropped successfully!")
        return True
    else:
        print("Operation cancelled.")
        return False

def create_all_database_tables_and_verify():
    try:
        from app.api.v1.models.company_model import Company
        from app.api.v1.models.department_model import Department
        from app.api.v1.models.employee_model import Employee
        from app.api.v1.models.user_model import User
        from app.api.v1.models.task_model import Task
        
        print(f"\nCreating tables: {', '.join(Base.metadata.tables.keys())}")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\nVerified {len(tables)} tables in database")
        
        return True
        
    except Exception as e:
        print(f"Error creating tables: {e}")
        print("Ensure PostgreSQL is running, database exists, and credentials are correct")
        return False

def display_database_table_management_menu():
    # print("\n" + "=" * 70)
    # print("Database Table Management")
    # print("=" * 70)
    # print(f"Database: {settings.DATABASE_NAME}")
    # print(f"Connection: {settings.DATABASE_URL}")
    # print("\nOptions:")
    # print("1. Create tables only (safe - won't drop existing)")
    # print("2. Drop and recreate all tables (WARNING: Deletes all data)")
    # print("3. Exit")
    # print("=" * 70)
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            if create_all_database_tables_and_verify():
                print("\nDone!")
        
        elif choice == '2':
            if drop_all_database_tables_with_confirmation():
                if create_all_database_tables_and_verify():
                    print("\nDatabase recreated successfully!")
        
        elif choice == '3':
            sys.exit(0)
        
        else:
            print("Invalid choice.")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    display_database_table_management_menu()
