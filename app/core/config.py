from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field, field_validator
from typing import Optional, Any


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
    # Voice (STT/TTS) — same OPENAI_API_KEY; optional overrides
    OPENAI_WHISPER_MODEL: str = Field(default="whisper-1", description="OpenAI Whisper model for speech-to-text")
    OPENAI_TTS_MODEL: str = Field(default="tts-1", description="OpenAI TTS model (tts-1 or tts-1-hd)")
    OPENAI_TTS_VOICE: str = Field(default="alloy", description="OpenAI TTS voice name")
    OPENAI_TTS_FORMAT: str = Field(default="mp3", description="TTS audio format: mp3, opus, aac, flac")
    MAX_VOICE_AUDIO_SIZE: int = Field(
        default=25 * 1024 * 1024,
        description="Max uploaded voice audio size in bytes (OpenAI Whisper limit is 25MB)",
    )
    
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
    
    # Redis Settings (for WebSocket Pub/Sub)
    REDIS_URL: Optional[str] = Field(default=None, description="Redis connection URL (e.g., redis://localhost:6379)")
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    
    # Razorpay Settings
    RAZORPAY_KEY_ID: Optional[str] = Field(default=None, description="Razorpay Key ID")
    RAZORPAY_KEY_SECRET: Optional[str] = Field(default=None, description="Razorpay Key Secret")
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = Field(default=None, description="Razorpay Webhook Secret for signature verification")

    # SMTP (transactional email, e.g. Hostinger)
    EMAIL_HOST: Optional[str] = Field(default=None, description="SMTP host (e.g. smtp.hostinger.com)")
    EMAIL_PORT: int = Field(default=465, description="SMTP port (465 SSL, 587 TLS)")
    EMAIL_USER: Optional[str] = Field(default=None, description="SMTP username (usually full email)")
    EMAIL_PASS: Optional[str] = Field(default=None, description="SMTP password")
    EMAIL_SECURE: str = Field(default="SSL", description="SSL (port 465), TLS (STARTTLS, often 587), or NONE")
    EMAIL_FROM_NAME: str = Field(default="ManaHRMS", description="Display name for From header")
    APP_PUBLIC_URL: Optional[str] = Field(
        default=None,
        description="Public app URL for email links (no trailing slash), e.g. https://app.manahrms.com",
    )

    # Exotel voice agent (inbound calls → leads)
    EXOTEL_API_KEY: Optional[str] = Field(default=None, description="Exotel API key")
    EXOTEL_API_TOKEN: Optional[str] = Field(default=None, description="Exotel API token")
    EXOTEL_ACCOUNT_SID: Optional[str] = Field(default=None, description="Exotel account SID")
    EXOTEL_SUBDOMAIN: str = Field(default="api.in.exotel.com", description="Exotel API subdomain")
    EXOTEL_INBOUND_NUMBER: str = Field(default="08047361154", description="Exotel ExoPhone for Dhiora inbound calls")
    EXOTEL_WEBHOOK_TOKEN: Optional[str] = Field(default=None, description="Shared secret for Exotel webhook URLs")
    EXOTEL_DEFAULT_COMPANY_ID: Optional[int] = Field(default=None, description="Company ID for leads created from Exotel calls")
    EXOTEL_OPENAI_REALTIME_MODEL: str = Field(
        default="gpt-realtime",
        description="OpenAI Realtime GA model for Exotel voice agent (e.g. gpt-realtime)",
    )
    DHIORA_KNOWLEDGE: Optional[str] = Field(
        default=None,
        description="Optional override for Dhiora product knowledge used by the voice agent",
    )

    @field_validator(
        "EMAIL_HOST",
        "EMAIL_USER",
        "EMAIL_PASS",
        "EMAIL_FROM_NAME",
        "EMAIL_SECURE",
        "APP_PUBLIC_URL",
        mode="before",
    )
    @classmethod
    def strip_email_env_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra environment variables
    )


# Global settings instance
settings = Settings()
