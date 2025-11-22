"""
Setup script for pgvector extension and vector_store table
Run this script once to enable pgvector and create the vector store table
Works with Neon DB (serverless PostgreSQL) and regular PostgreSQL
"""
from sqlalchemy import text, inspect
from app.db.session import engine
from app.db.base import Base
from app.core.config import settings


def setup_pgvector():
    """Enable pgvector extension and create vector_store table"""
    print("=" * 60)
    print("🔧 Setting up pgvector for RAG")
    print("=" * 60)
    print(f"📊 Database: {settings.DATABASE_NAME}")
    print(f"🔗 Host: {settings.DATABASE_HOST}")
    
    # Check if using Neon DB (common indicators)
    is_neon = "neon" in settings.DATABASE_HOST.lower() or "neon.tech" in str(settings.DATABASE_URL).lower()
    if is_neon:
        print("✨ Detected Neon DB (serverless PostgreSQL)")
    
    try:
        with engine.connect() as conn:
            # Check if pgvector extension exists
            print("\n1. Checking pgvector extension...")
            result = conn.execute(text("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension WHERE extname = 'vector'
                );
            """))
            extension_exists = result.fetchone()[0]
            
            if not extension_exists:
                print("   ⚠️  pgvector extension not found. Creating...")
                try:
                    # For Neon DB, the extension should be available but might need explicit creation
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                    conn.commit()
                    print("   ✅ pgvector extension created successfully!")
                except Exception as e:
                    error_msg = str(e).lower()
                    print(f"   ❌ Failed to create pgvector extension: {e}")
                    
                    if is_neon or "neon" in error_msg:
                        print("\n   📝 For Neon DB:")
                        print("   1. Go to your Neon dashboard: https://console.neon.tech")
                        print("   2. Open the SQL Editor for your database")
                        print("   3. Run: CREATE EXTENSION IF NOT EXISTS vector;")
                        print("   4. Then run this script again")
                        print("\n   Note: Neon DB supports pgvector, but you may need to enable it manually")
                    else:
                        print("\n   Please install pgvector extension in PostgreSQL:")
                        print("   For Ubuntu/Debian: sudo apt-get install postgresql-XX-pgvector")
                        print("   Or compile from source: https://github.com/pgvector/pgvector")
                    return False
            else:
                print("   ✅ pgvector extension already exists")
            
            # Check if vector_store table exists
            print("\n2. Checking vector_store table...")
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            
            if 'vector_store' not in existing_tables:
                print("   ⚠️  vector_store table not found. Creating...")
                try:
                    # Create the table using SQLAlchemy
                    Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables['vector_store']])
                    conn.commit()
                    print("   ✅ vector_store table created successfully!")
                except Exception as e:
                    print(f"   ❌ Failed to create vector_store table: {e}")
                    return False
            else:
                print("   ✅ vector_store table already exists")
            
            # Verify vector column type
            print("\n3. Verifying vector column...")
            result = conn.execute(text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'vector_store' 
                AND column_name = 'embedding';
            """))
            column_info = result.fetchone()
            
            if column_info:
                print(f"   ✅ Vector column exists (type: {column_info[0]})")
            else:
                print("   ⚠️  Vector column not found. This might indicate an issue.")
            
            # Check indexes
            print("\n4. Verifying indexes...")
            result = conn.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'vector_store';
            """))
            indexes = [row[0] for row in result.fetchall()]
            if indexes:
                print(f"   ✅ Found {len(indexes)} index(es): {', '.join(indexes)}")
            else:
                print("   ⚠️  No indexes found (this is okay for small datasets)")
            
            print("\n" + "=" * 60)
            print("✅ pgvector setup completed successfully!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Run vector sync to populate embeddings:")
            print("   python sync_vectors.py")
            print("2. Or use the API endpoint to sync vectors for a company")
            return True
            
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("\nTroubleshooting:")
        if is_neon:
            print("1. For Neon DB: Enable pgvector extension via SQL Editor in Neon dashboard")
            print("2. Run: CREATE EXTENSION IF NOT EXISTS vector; in Neon SQL Editor")
            print("3. Check your Neon database connection string")
            print("4. Ensure your Neon project has pgvector enabled")
        else:
            print("1. Ensure PostgreSQL is running")
            print("2. Ensure pgvector extension is installed in PostgreSQL")
            print("3. Check database connection settings")
        return False


if __name__ == "__main__":
    setup_pgvector()

