from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from app.core.config import settings


def get_database_url_with_ssl() -> str:
    """
    Ensure DATABASE_URL has SSL parameters for Neon and other cloud databases.
    Adds sslmode=require if not already present for cloud database connections.
    Also cleans the URL to remove any problematic characters.
    """
    db_url = settings.DATABASE_URL
    
    # Clean the URL - remove any trailing whitespace or problematic characters
    db_url = db_url.strip()
    
    # Remove common shell prompt characters that might accidentally be included
    db_url = db_url.rstrip('>').rstrip('<').rstrip('$').rstrip('#')
    
    # Check if it's a cloud database that requires SSL
    is_cloud_db = any(provider in db_url.lower() for provider in [
        "neon", "neon.tech", "render", "supabase", "railway", "heroku", 
        "aws", "amazonaws", "azure", "gcp"
    ])
    
    if is_cloud_db:
        # Parse the URL
        parsed = urlparse(db_url)
        
        # Clean the database name (path) - remove any problematic characters
        db_path = parsed.path.strip().lstrip('/')
        # Remove any trailing special characters
        db_path = db_path.rstrip('>').rstrip('<').rstrip('$').rstrip('#').rstrip(' ')
        
        # Reconstruct path
        parsed = parsed._replace(path=f'/{db_path}')
        
        query_params = parse_qs(parsed.query)
        
        # Add SSL mode if not present
        if 'sslmode' not in query_params:
            query_params['sslmode'] = ['require']
        
        # Reconstruct URL with SSL parameters
        new_query = urlencode(query_params, doseq=True)
        db_url = urlunparse(parsed._replace(query=new_query))
    
    return db_url


# Get database URL with SSL if needed
database_url = get_database_url_with_ssl()

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_database_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
