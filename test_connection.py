"""
Simple script to test PostgreSQL database connection
"""
from app.db.session import engine
from app.core.config import settings


def test_connection():
    print("=" * 50)
    print("Testing PostgreSQL Database Connection")
    print("=" * 50)
    print(f"\nDatabase: {settings.DATABASE_NAME}")
    print(f"Host: {settings.DATABASE_HOST}")
    print(f"Port: {settings.DATABASE_PORT}")
    print(f"User: {settings.DATABASE_USER}")
    print(f"\nConnection String: {settings.DATABASE_URL}")
    print("\n" + "=" * 50)
    
    try:
        # Test connection
        with engine.connect() as connection:
            # Use exec_driver_sql for raw SQL in SQLAlchemy 2.x
            result = connection.exec_driver_sql("SELECT version();")
            version = result.fetchone()[0]
            
            print("✅ CONNECTION SUCCESSFUL!")
            print(f"\nPostgreSQL Version:")
            print(version)
            print("\n" + "=" * 50)
            return True
            
    except Exception as e:
        print("❌ CONNECTION FAILED!")
        print(f"\nError: {str(e)}")
        print("\nPlease check:")
        print("1. PostgreSQL is running")
        print("2. Database 'HRMS' exists")
        print("3. Credentials are correct (password: 123456)")
        print("4. PostgreSQL is accepting connections on localhost:5432")
        print("\n" + "=" * 50)
        return False


if __name__ == "__main__":
    test_connection()


