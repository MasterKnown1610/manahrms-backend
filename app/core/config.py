from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Database configuration settings"""
    
    # Database Configuration
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "123456"
    DATABASE_NAME: str = "HRMS"
    # Optional full connection URL (takes precedence if provided)
    DATABASE_URL_OVERRIDE: Optional[str] = Field(default=None, alias="DATABASE_URL")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct PostgreSQL database URL"""
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        return (
            f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )
    
    # JWT Authentication Settings
    SECRET_KEY: str = "your-secret-key-change-in-production-09876543210"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "HRMS Backend"
    
    class Config:
        case_sensitive = True
        env_file = ".env"


# Global settings instance
settings = Settings()
