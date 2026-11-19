from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ``backend/app/core/config.py`` -> repository ``backend`` directory.
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    APP_NAME: str = "AI-Powered Student Radar"
    APP_ENV: str = "development"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://radar_admin:radar_secret_pass@localhost:5432/student_radar_db",
        description="Async SQLAlchemy database connection string",
    )
    SYNC_DATABASE_URL: str = Field(
        default="postgresql://radar_admin:radar_secret_pass@localhost:5432/student_radar_db",
        description="Synchronous database connection string for Alembic and Celery",
    )

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    ENABLE_CELERY_DISPATCH: bool = False

    # AI & Search
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_TEXT_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    GEMINI_EMBEDDING_DIMENSIONS: int = 768
    TAVILY_API_KEY: Optional[str] = None
    EXA_API_KEY: Optional[str] = None

    # External market intelligence (cross-platform signal collection)
    ENABLE_EXTERNAL_INTELLIGENCE: bool = True
    EXTERNAL_SIGNAL_TIMEOUT_SECONDS: float = 5.0
    EXTERNAL_SIGNAL_MAX_PER_SOURCE: int = 3
    SIGNAL_CACHE_TTL_MINUTES: int = 180

    # Intent + recency Radar pipeline
    RADAR_HACKATHON_DOMAINS: tuple[str, ...] = (
        "devfolio.co",
        "unstop.com",
        "dorahacks.io",
        "devpost.com",
        "mlh.io",
        "hackerearth.com",
    )
    RADAR_BUILDER_DOMAINS: tuple[str, ...] = (
        "reddit.com",
        "x.com",
        "news.ycombinator.com",
        "indiehackers.com",
    )
    RADAR_TAVILY_SEARCH_DEPTH: str = "advanced"
    RADAR_TAVILY_NEWS_TIME_RANGE: str = "week"
    RADAR_TAVILY_TIME_RANGE: str = "month"
    RADAR_TAVILY_MAX_RESULTS: int = 10
    RADAR_TAVILY_FILTER_BY_PUBLISHED_DATE: bool = True
    RADAR_TAVILY_INCLUDE_PUBLISHED_DATE: bool = True
    RADAR_RERANK_THRESHOLD: int = 65
    RADAR_SCAN_LANGUAGE: str = "en"
    RADAR_ON_DEMAND_MAX_INTENTS: int = 3
    RADAR_ENABLE_DIRECT_SOURCES: bool = True
    RADAR_DIRECT_SOURCE_TIMEOUT_SECONDS: float = 10.0
    RADAR_DIRECT_SOURCE_LIMIT: int = 20

    # Security & Auth
    JWT_SECRET: str = "super_secret_jwt_key_for_development_purposes_only_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    GUEST_SESSION_EXPIRE_HOURS: int = 24
    SIMULATED_OAUTH_EMAIL: str = "student.builder@university.edu"

    # Domain personas (mirrors backend/configs/personas/*.json)
    KNOWN_PERSONAS: tuple[str, ...] = (
        "tech_builder",
        "policy_law",
        "business_finance",
        "design_biotech",
    )
    DEFAULT_PERSONA: str = "tech_builder"
    DEFAULT_CITY: str = "Pune"

    # Credits / growth limits (Visibility Credits economy)
    SIGNUP_CREDITS: int = 30
    REFERRAL_SIGNUP_CREDITS: int = 15
    PEER_REVIEW_CREDITS: int = 10
    BOOST_COST_CREDITS: int = 20
    BOOST_DURATION_HOURS: int = 48
    # Kept for backwards compatibility with older callers/docs.
    BOOST_DURATION_DAYS: int = 2
    INVITE_DAILY_LIMIT: int = 10
    MAX_CONTACT_HASHES: int = 500
    URGENT_WINDOW_HOURS: int = 72  # Urgent deadlines: closing in < 72 hours
    MATCHMAKING_LIMIT: int = 5
    MATCHMAKING_CANDIDATE_LIMIT: int = 300
    MAX_VERIFIED_SKILLS: int = 40

    # Scheduled radar workers (IST)
    CRAWL_HOUR_IST: int = 5
    CRAWL_MINUTE_IST: int = 30
    DAILY_BRIEFING_HOUR_IST: int = 7
    WEEKLY_BRIEFING_DAY: str = "sunday"
    WEEKLY_BRIEFING_HOUR_IST: int = 18
    SIGNAL_REFRESH_HOUR_IST: int = 6
    SIGNAL_REFRESH_MINUTE_IST: int = 0

    # Outbound link verification
    VERIFY_REQUEST_TIMEOUT_SECONDS: float = 5.0
    VERIFY_MAX_REDIRECTS: int = 3

    # Cloudflare R2 / S3
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: str = "student-radar-assets"
    R2_PUBLIC_DOMAIN: str = "https://assets.studentradar.dev"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(
        # Support both ``backend/.env`` and a repository-root ``.env`` while
        # still working when the process is launched from any directory.
        env_file=(_BACKEND_DIR / ".env", _REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.strip().lower() in {"production", "prod"}


settings = Settings()
