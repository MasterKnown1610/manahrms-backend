from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import logging
import bcrypt

from app.core.config import settings

logger = logging.getLogger(__name__)

# Use bcrypt directly instead of passlib to avoid initialization issues
# Passlib's backend detection can cause "password cannot be longer than 72 bytes" errors
# during initialization, so we'll use bcrypt directly for both hashing and verification


def verify_password_against_hash(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    Uses bcrypt directly to avoid passlib initialization issues.
    """
    try:
        # Convert password to bytes
        password_bytes = plain_password.encode('utf-8')
        
        # Bcrypt has a 72-byte limit
        if len(password_bytes) > 72:
            logger.warning(f"Password exceeds 72 bytes, truncating for bcrypt verification")
            password_bytes = password_bytes[:72]
        
        # Convert hash to bytes if it's a string
        if isinstance(hashed_password, str):
            hash_bytes = hashed_password.encode('utf-8')
        else:
            hash_bytes = hashed_password
        
        # Use bcrypt directly to avoid passlib backend detection issues
        return bcrypt.checkpw(password_bytes, hash_bytes)
            
    except (ValueError, TypeError) as e:
        logger.error(f"Password verification error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during password verification: {e}", exc_info=True)
        return False


def hash_password_for_storage(password: str) -> str:
    """
    Hash a password for storage using bcrypt.
    Uses bcrypt directly to avoid passlib initialization issues.
    """
    try:
        # Convert password to bytes
        password_bytes = password.encode('utf-8')
        
        # Bcrypt has a 72-byte limit
        if len(password_bytes) > 72:
            logger.warning(f"Password exceeds 72 bytes, truncating for bcrypt hashing")
            password_bytes = password_bytes[:72]
        
        # Generate salt and hash password
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        
        # Return as string
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing password: {e}", exc_info=True)
        raise


def create_jwt_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def decode_and_verify_jwt_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


