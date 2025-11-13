"""
Manually create database tables for HRMS Multi-Tenant System
"""
import sys
from app.db.session import engine
from app.db.base import Base
from app.core.config import settings

print("=" * 70)
print("🔧 HRMS Database Table Management")
print("=" * 70)
print(f"\nDatabase: {settings.DATABASE_NAME}")
print(f"Connection: {settings.DATABASE_URL}")

def drop_all_tables():
    """Drop all existing tables"""
    print("\n⚠️  WARNING: This will delete all existing data!")
    confirmation = input("Type 'yes' to proceed with dropping all tables: ")
    
    if confirmation.lower() == 'yes':
        print("\n🗑️  Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("✅ All tables dropped successfully!")
        return True
    else:
        print("❌ Operation cancelled.")
        return False

def create_all_tables():
    """Create all tables"""
    try:
        # Import all models to ensure they're registered
        from app.api.v1.models.company_model import Company
        from app.api.v1.models.department_model import Department
        from app.api.v1.models.employee_model import Employee
        from app.api.v1.models.user_model import User
        from app.api.v1.models.task_model import Task
        
        print(f"\n📋 Models to create:")
        for table_name in Base.metadata.tables.keys():
            print(f"   - {table_name}")
        
        print("\n🔨 Creating tables...")
        Base.metadata.create_all(bind=engine)
        
        print("✅ Tables created successfully!")
        
        # Verify
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\n✅ Verified tables in database:")
        for table in tables:
            columns = inspector.get_columns(table)
            print(f"   - {table} ({len(columns)} columns)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error creating tables: {e}")
        print("\n💡 Make sure:")
        print("   1. PostgreSQL is running")
        print("   2. Database exists")
        print("   3. Credentials are correct")
        return False

def main():
    """Main function with menu"""
    print("\n" + "=" * 70)
    print("Options:")
    print("1. Create tables only (safe - won't drop existing)")
    print("2. Drop and recreate all tables (⚠️  WARNING: Deletes all data)")
    print("3. Exit")
    print("=" * 70)
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            print("\n📦 Creating tables...")
            if create_all_tables():
                print("\n" + "=" * 70)
                print("✅ Done!")
                print("=" * 70)
        
        elif choice == '2':
            if drop_all_tables():
                if create_all_tables():
                    print("\n" + "=" * 70)
                    print("✅ Database recreated successfully!")
                    print("=" * 70)
                    print("\n📝 Next steps:")
                    print("   1. Start the server: ./start_server.sh")
                    print("   2. Register a company: POST /api/v1/auth/register-company")
                    print("   3. See IMPLEMENTATION_GUIDE.md for details")
                    print("=" * 70)
        
        elif choice == '3':
            print("👋 Goodbye!")
            sys.exit(0)
        
        else:
            print("❌ Invalid choice. Please run the script again.")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
