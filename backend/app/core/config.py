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
    # The 2.5 model names below are retained only for legacy services. Live
    # probes (2026-11-24) returned 404 "no longer available to new users" for
    # gemini-2.5-flash / 2.5-pro; Dossier v2 therefore pins a working model and
    # an explicit fallback chain. Do not change these to a model that has not
    # been probed with the configured key.
    GEMINI_API_KEY: Optional[str] = None
    # Live probes on 2026-11-24: 3.5/3.6 flash returned 429 quota exhaustion,
    # 3.8 flash returned 503 high demand. These models returned real JSON with
    # stable token counts: 3-flash-preview (reasoning), 3.5-flash-lite (fast),
    # 3.1-flash-lite and flash-lite-latest. The critic uses the reasoning model;
    # bulk extraction/synthesis uses the fast model, with a reasoning fallback.
    GEMINI_TEXT_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_CRITIC_MODEL: str = "gemini-3-flash-preview"
    GEMINI_SMALL_MODEL: str = "gemini-3.5-flash-lite"
    # Exclude models that returned 429 quota exhaustion or 503 high demand
    # during the real-run probe. Each remaining id returned real JSON.
    GEMINI_MODEL_FALLBACKS: tuple[str, ...] = (
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3-flash-preview",
    )
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_EMBEDDING_DIMENSIONS: int = 768
    # Groq is the primary fast/cheap JSON planner for Concept Normalization and
    # the Radar relevance gatekeeper. The model ids below were probed with a
    # live key on 2026-11-24 and support OpenAI-compatible JSON mode.
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_MODEL_FALLBACKS: tuple[str, ...] = ("openai/gpt-oss-20b", "allam-2-7b")
    TAVILY_API_KEY: Optional[str] = None
    EXA_API_KEY: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None  # optional: raises GitHub API rate limit

    # Dossier v2 research pipeline
    DOSSIER_V2_ENABLED: bool = True
    DOSSIER_V2_RETRIEVAL_TIMEOUT_SECONDS: float = 20.0
    DOSSIER_V2_SECTION_TIMEOUT_SECONDS: float = 45.0
    DOSSIER_V2_LLM_TIMEOUT_SECONDS: float = 25.0
    DOSSIER_V2_MAX_REPAIRS: int = 1
    DOSSIER_V2_MAX_SECTION_WORKERS: int = 5
    DOSSIER_V2_MAX_QUESTION_WORKERS: int = 6
    # Free-tier providers cannot serve 18 independent section calls in a burst.
    # Sections are written in small batches with a hard overall deadline.
    DOSSIER_V2_SECTION_BATCH_SIZE: int = 3
    DOSSIER_V2_RUN_TIMEOUT_SECONDS: float = 220.0
    # Dossier-specific model order. Live probes on 2026-11-25 showed 3-flash-preview
    # quota-limited; 3.1-flash-lite became healthy again after the earlier 503
    # burst, so it is retained as the third Gemini option. The generic legacy
    # fallback list is deliberately not used here.
    DOSSIER_V2_MODEL_CHAIN: tuple[str, ...] = (
        "gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.1-flash-lite",
    )
    DOSSIER_V2_CRITIC_MODEL_CHAIN: tuple[str, ...] = (
        "gemini-flash-lite-latest", "gemini-3.1-flash-lite", "gemini-3.5-flash-lite",
    )
    # USD per 1M tokens; used for per-run cost estimates shown to reviewers.
    DOSSIER_V2_PRICE_PER_M_INPUT_USD: float = 0.30
    DOSSIER_V2_PRICE_PER_M_OUTPUT_USD: float = 2.50
    # Groq public pricing for openai/gpt-oss-20b (console.groq.com/docs/models).
    DOSSIER_V2_GROQ_PRICE_PER_M_INPUT_USD: float = 0.075
    DOSSIER_V2_GROQ_PRICE_PER_M_OUTPUT_USD: float = 0.30
    DOSSIER_V2_GROQ_MODEL: str = "openai/gpt-oss-20b"

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
    RADAR_ON_DEMAND_MAX_INTENTS: int = 5
    RADAR_ENABLE_DIRECT_SOURCES: bool = True
    RADAR_DIRECT_SOURCE_TIMEOUT_SECONDS: float = 10.0
    RADAR_DIRECT_SOURCE_LIMIT: int = 20

    # Concept-normalized Radar search (Tavily 4-bucket blueprint).
    RADAR_EVENT_DOMAINS: tuple[str, ...] = (
        "devpost.com",
        "devfolio.co",
        "unstop.com",
        "dorahacks.io",
        "lu.ma",
        "mlh.io",
        "hackerearth.com",
    )
    RADAR_OPPORTUNITY_DOMAINS: tuple[str, ...] = (
        "ycombinator.com",
        "techstars.com",
        "grants.gov",
        "f6s.com",
        "startupindia.gov.in",
        "birac.nic.in",
        "producthunt.com",
    )
    RADAR_TREND_DAYS: int = 180
    RADAR_NEWS_DAYS: int = 30
    RADAR_OPPORTUNITY_DAYS: int = 60
    RADAR_TAVILY_MIN_SCORE: float = 0.60
    # Open-web trend/news scores sit on a lower scale than the general gate.
    # Keep enough candidates alive for the strict LLM relevance gate to judge.
    RADAR_TAVILY_SIGNAL_MIN_SCORE: float = 0.45
    # Tavily scores domain-locked (events / grants) results on a different
    # scale than open-web results. A lower provider gate keeps genuine portal
    # hits alive; the LLM gatekeeper below is the strict relevance filter.
    RADAR_TAVILY_DOMAIN_MIN_SCORE: float = 0.30
    RADAR_LLM_MIN_SCORE: int = 60
    RADAR_INTEL_MAX_RESULTS: int = 8

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
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001,"
        "http://localhost:3002,http://127.0.0.1:3002,"
        "http://localhost:3003,http://127.0.0.1:3003,"
        "http://localhost:3200,http://127.0.0.1:3200"
    )

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

    @property
    def gemini_configured(self) -> bool:
        key = (self.GEMINI_API_KEY or "").strip()
        return bool(key) and key not in {
            "your_gemini_api_key_here", "changeme", "xxx", "placeholder",
        }

    @property
    def groq_configured(self) -> bool:
        key = (self.GROQ_API_KEY or "").strip()
        return bool(key) and key not in {
            "your_groq_api_key_here", "changeme", "xxx", "placeholder",
        }

    @property
    def llm_configured(self) -> bool:
        """True only when at least one real provider key is present."""
        return self.gemini_configured or self.groq_configured


settings = Settings()
