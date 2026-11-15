import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import (
    auth,
    dossiers,
    pr,
    radar,
    network,
    credits
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AI-Powered Student Radar Database Engine...")
    try:
        async with engine.begin() as conn:
            # Enable uuid and pgvector extensions in PostgreSQL
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
                await conn.execute("CREATE EXTENSION IF NOT EXISTS \"vector\";")
            except Exception as e:
                logger.warning(f"Vector extension notice (may already exist or running in test mode): {e}")
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schemas verified.")
    except Exception as e:
        logger.warning(f"Could not connect to database on startup: {e}. Will reconnect when DB is online.")
    yield
    logger.info("Shutting down Student Radar Engine...")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Single-player utility first, multiplayer discovery second. Automated Proof-of-Work Dossiers, PR Studio, and Daily Opportunity Radar.",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(dossiers.router, prefix="/api/v1")
app.include_router(pr.router, prefix="/api/v1")
app.include_router(radar.router, prefix="/api/v1")
app.include_router(network.router, prefix="/api/v1")
app.include_router(credits.router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "vector_dimensions": 768
    }

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "AI-Powered Student Radar API is running.",
        "documentation": "/docs",
        "version": "1.0.0"
    }

