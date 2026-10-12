import os
import logging
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

logger = logging.getLogger("synapselm.config")
load_dotenv()

def _normalize_database_url(url: str) -> str:
    """Ensure database URL is compatible with SQLAlchemy (convert postgres:// to postgresql://)."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

_raw_db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/synapselm")
_normalized_db_url = _normalize_database_url(_raw_db_url)

class Settings(BaseSettings):
    PROJECT_NAME: str = "SynapseLM"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-for-jwt")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    DATABASE_URL: str = _normalized_db_url
    
    # LLM Provider Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-3.6-flash")
    
    # Realtime & Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # CORS
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")

    # Credential Encryption
    CREDENTIAL_ENCRYPTION_KEY: str | None = os.getenv("CREDENTIAL_ENCRYPTION_KEY", None)

    # Frontend URL (for password reset links, etc.)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://frontend-blond-omega-jv7qlrlh2x.vercel.app")

    # Transactional Email Provider (SMTP / Resend)
    SMTP_HOST: str | None = os.getenv("SMTP_HOST", None)
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str | None = os.getenv("SMTP_USER", None)
    SMTP_PASSWORD: str | None = os.getenv("SMTP_PASSWORD", None)
    SMTP_FROM: str = os.getenv("SMTP_FROM", "SynapseLM <noreply@synapselm.com>")
    RESEND_API_KEY: str | None = os.getenv("RESEND_API_KEY", None)

    class Config:
        case_sensitive = True

settings = Settings()

# Production configuration validation
if settings.ENVIRONMENT.lower() == "production":
    if settings.SECRET_KEY == "super-secret-key-for-jwt":
        logger.critical("SECURITY ALERT: Using default dev SECRET_KEY in production! Set SECRET_KEY in environment.")
    if not settings.CREDENTIAL_ENCRYPTION_KEY:
        logger.critical("SECURITY ALERT: CREDENTIAL_ENCRYPTION_KEY is unset in production! Stored API keys will fail.")
