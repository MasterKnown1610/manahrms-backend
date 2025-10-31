"""
Script to check database connection and tables
"""
from app.db.session import engine
from app.core.config import settings
from app.db.base import Base
from sqlalchemy import inspect, text


def check_database():
    print("=" * 60)
    print("🔍 Checking Database Status")
    print("=" * 60)
    
    print(f"\n📊 Database Configuration:")
    print(f"   Database: {settings.DATABASE_NAME}")
    print(f"   Host: {settings.DATABASE_HOST}")
    print(f"   Port: {settings.DATABASE_PORT}")
    print(f"   User: {settings.DATABASE_USER}")
    print(f"   URL: {settings.DATABASE_URL}")
    
    try:
        # Test connection
        print("\n🔗 Testing connection...")
        with engine.connect() as connection:
            result = connection.execute(text("SELECT current_database(), current_user;"))
            db_name, db_user = result.fetchone()
            print(f"✅ Connected to database: {db_name} as user: {db_user}")
            
            # Check if users table exists
            print("\n📋 Checking for tables...")
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                print(f"✅ Found {len(tables)} table(s):")
                for table in tables:
                    print(f"   - {table}")
            else:
                print("⚠️  No tables found in database!")
                print("\n💡 Creating tables now...")
                Base.metadata.create_all(bind=engine)
                print("✅ Tables created!")
                
                # Check again
                result = connection.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public';
                """))
                tables = [row[0] for row in result.fetchall()]
                print(f"\n✅ Now found {len(tables)} table(s):")
                for table in tables:
                    print(f"   - {table}")
            
            # Check users table structure
            if 'users' in tables:
                print("\n📋 Users table structure:")
                result = connection.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'users'
                    ORDER BY ordinal_position;
                """))
                for row in result.fetchall():
                    print(f"   - {row[0]}: {row[1]} (nullable: {row[2]})")
                
                # Check if there are any users
                result = connection.execute(text("SELECT COUNT(*) FROM users;"))
                count = result.fetchone()[0]
                print(f"\n👥 Total users in database: {count}")
                
                if count > 0:
                    result = connection.execute(text("SELECT id, username, email FROM users;"))
                    print("\n📝 Existing users:")
                    for row in result.fetchall():
                        print(f"   - ID: {row[0]}, Username: {row[1]}, Email: {row[2]}")
            
            print("\n" + "=" * 60)
            print("✅ Database check complete!")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure PostgreSQL is running")
        print("   2. Check if database 'HRMS' exists")
        print("   3. Verify credentials in app/core/config.py")
        print("   4. Try: psql -U postgres -c 'CREATE DATABASE \"HRMS\";'")


if __name__ == "__main__":
    check_database()

