import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text

from app import models  # noqa: F401  (registers every ORM table on Base.metadata)
from app.api.v1 import (
    auth,
    credits,
    dossiers,
    dossiers_v2,
    matchmaking,
    network,
    openai_compat,
    pr,
    radar,
    signals,
)
from app.core.config import settings
from app.core.database import Base, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def unhandled_exception_handler(request: Request, exc: Exception):
    """Return a readable 500 that still carries CORS headers.

    Starlette's server-error handler runs outside CORSMiddleware, so an
    unhandled exception would otherwise reach the browser as a 500 with no
    `Access-Control-Allow-Origin` header. That hides the real error behind a
    misleading CORS failure.
    """

    logger.exception("Unhandled error on %s %s", request.method, request.url.path)

    headers: dict[str, str] = {}
    origin = request.headers.get("origin")
    if origin and origin in settings.cors_origin_list:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Vary"] = "Origin"

    detail = str(exc) if not settings.is_production else "Internal server error"
    return JSONResponse(
        status_code=500,
        content={"detail": detail, "path": request.url.path},
        headers=headers,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AI-Powered Student Radar Database Engine...")
    if settings.is_production and "change_in_production" in settings.JWT_SECRET:
        logger.warning("JWT_SECRET is still set to the development default. Rotate it before production traffic.")

    # Extensions live in separate transactions: a failure in one must not abort
    # the other (PostgreSQL aborts the whole transaction after any error).
    for extension in ("uuid-ossp", "vector"):
        try:
            async with engine.begin() as conn:
                if extension == "vector":
                    # Support installs where pgvector's SQL is loaded manually
                    # from a staged DLL and no extension control file exists.
                    type_exists = await conn.scalar(
                        text("SELECT 1 FROM pg_type WHERE typname = 'vector'")
                    )
                    if type_exists:
                        continue
                await conn.execute(text(f'CREATE EXTENSION IF NOT EXISTS "{extension}";'))
        except Exception as exc:
            logger.warning(
                "Could not enable PostgreSQL extension %s (may already exist or "
                "the database is offline): %s",
                extension,
                exc,
            )

    # Force pgvector's shared library to load on a fresh connection. On native
    # Windows installs the SQL functions point at a staged vector.dll; if two
    # copies get loaded in the same backend, PostgreSQL reports
    # `attempt to redefine parameter "hnsw.ef_search"` on every later query
    # that reads or writes a vector column. Catching it here gives an actionable
    # startup warning instead of a mysterious 500 on /api/v1/dossiers.
    try:
        async with engine.begin() as conn:
            dimensions = await conn.scalar(text("SELECT vector_dims('[1,2,3]'::vector)"))
        if dimensions != 3:
            raise RuntimeError(f"pgvector smoke test returned {dimensions!r} dimensions")
        logger.info("pgvector runtime check passed.")
    except Exception as exc:
        logger.warning(
            "pgvector runtime check failed (%s). Vector columns may return 500 "
            "until the shared-library path is consistent and the app is restarted.",
            exc,
        )
        # Never return a possibly poisoned connection to the pool.
        await engine.dispose()

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schemas verified.")
    except Exception as exc:
        logger.warning("Could not connect to database on startup: %s. Will reconnect on demand.", exc)

    # A worker killed mid-run used to leave the row in "running" forever.
    # Reconcile old rows on startup so the UI never shows a stuck dossier.
    try:
        async with engine.begin() as conn:
            stale = await conn.execute(
                text("""
                    update dossier_runs
                       set status = 'failed',
                           error = :error,
                           finished_at = now()
                     where status = 'running'
                       and created_at < now() - interval '10 minutes'
                """),
                {"error": json.dumps({
                    "code": "RUN_INTERRUPTED",
                    "message": "Run did not reach a terminal state before the worker stopped.",
                })},
            )
            if stale.rowcount:
                logger.warning("Marked %s stale dossier run(s) as failed", stale.rowcount)
    except Exception as exc:
        logger.warning("Could not reconcile stale dossier runs: %s", exc)

    yield
    logger.info("Shutting down Student Radar Engine...")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Single-player utility first, multiplayer discovery second. Automated "
        "Proof-of-Work Dossiers, PR Studio, Co-Builder Matchmaking, and Daily "
        "Opportunity Radar."
    ),
    lifespan=lifespan,
    exception_handlers={Exception: unhandled_exception_handler},
)

# CORS: wildcard origins cannot be combined with credentials in browsers.
_allow_credentials = "*" not in settings.cors_origin_list
# Next dev servers can move between 3000-3003 (and Docker uses 3200). In local
# development only, accept any loopback origin so a port change cannot surface
# as `TypeError: Failed to fetch`. Production still uses the explicit list.
_local_origin_regex = (
    None if settings.is_production else r"http://(?:localhost|127\.0\.0\.1):\d+"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=_local_origin_regex,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API v1 Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(dossiers.router, prefix="/api/v1")
app.include_router(dossiers_v2.router, prefix="/api/v1")
app.include_router(pr.router, prefix="/api/v1")
app.include_router(radar.router, prefix="/api/v1")
app.include_router(network.router, prefix="/api/v1")
app.include_router(credits.router, prefix="/api/v1")
app.include_router(matchmaking.router, prefix="/api/v1")
app.include_router(signals.router, prefix="/api/v1")

# OpenAI-compatible surface. Registered without the /api/v1 prefix because
# clients probe /v1/models directly on the server root.
app.include_router(openai_compat.router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "vector_dimensions": settings.GEMINI_EMBEDDING_DIMENSIONS,
        "personas": list(settings.KNOWN_PERSONAS),
    }


@app.get("/api/health", tags=["Health"], include_in_schema=False)
async def proxied_health_check():
    """Alias used by the Caddy /api/* route and the public health monitor."""
    return await health_check()


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Browsers request this from every origin they visit. Answering 204 keeps
    the API access log free of a perpetual 404 when someone opens /docs or /.
    """
    return Response(status_code=204)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "AI-Powered Student Radar API is running.",
        "documentation": "/docs",
        "version": "1.0.0",
    }
