import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    APP_NAME: str = "AI-Powered Student Radar"
    APP_ENV: str = "development"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://radar_admin:radar_secret_pass@localhost:5432/student_radar_db",
        description="Async SQLAlchemy database connection string"
    )
    SYNC_DATABASE_URL: str = Field(
        default="postgresql://radar_admin:radar_secret_pass@localhost:5432/student_radar_db",
        description="Synchronous database connection string for Alembic and Celery"
    )
    
    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AI & Search
    GEMINI_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    EXA_API_KEY: Optional[str] = None
    
    # Security & Auth
    JWT_SECRET: str = "super_secret_jwt_key_for_development_purposes_only_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    GUEST_SESSION_EXPIRE_HOURS: int = 24
    
    # Cloudflare R2 / S3
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: str = "student-radar-assets"
    R2_PUBLIC_DOMAIN: str = "https://assets.studentradar.dev"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()

