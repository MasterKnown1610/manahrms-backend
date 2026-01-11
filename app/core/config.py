from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field
from typing import Optional


class Settings(BaseSettings):
    """Database configuration settings"""
    
    # Database Configuration
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "123456"
    DATABASE_NAME: str = "HRMS"
    # Optional full connection URL from environment (takes precedence if provided)
    DATABASE_URL_ENV: Optional[str] = Field(default=None, alias="DATABASE_URL")
    
    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """Construct PostgreSQL database URL"""
        if self.DATABASE_URL_ENV:
            return self.DATABASE_URL_ENV
        return (
            f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )
    
    # JWT Authentication Settings
    SECRET_KEY: str = "your-secret-key-change-in-production-09876543210"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720  # 1 day (12 hours * 60 minutes)
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "HRMS Backend"
    
    # OpenAI Settings
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key for AI chatbot")
    OPENAI_MODEL: str = "gpt-3.5-turbo"  # Use cheaper model for token efficiency
    
    # File Upload Settings
    UPLOAD_DIR: str = Field(default="uploads", description="Directory for storing uploaded files (fallback if S3 not configured)")
    MAX_FILE_SIZE: int = Field(default=10485760, description="Maximum file size in bytes (default: 10MB)")
    ALLOWED_IMAGE_TYPES: list[str] = Field(default=["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"], description="Allowed image MIME types")
    ALLOWED_DOCUMENT_TYPES: list[str] = Field(default=["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"], description="Allowed document MIME types")
    
    # AWS S3 Settings
    USE_S3: bool = Field(default=False, description="Whether to use S3 for file storage (if False, uses local storage)")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, description="AWS Access Key ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, description="AWS Secret Access Key")
    AWS_REGION: str = Field(default="us-east-1", description="AWS Region for S3 bucket")
    S3_BUCKET_NAME: Optional[str] = Field(default=None, description="S3 bucket name for file storage")
    S3_ENDPOINT_URL: Optional[str] = Field(default=None, description="Custom S3 endpoint URL (for S3-compatible services like DigitalOcean Spaces)")
    
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra environment variables
    )


# Global settings instance
settings = Settings()
