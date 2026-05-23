"""
Mr. Scrapper — FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from sqlalchemy import select
from app.database import init_db, AsyncSessionLocal
from app.models import User
from app.services.auth_service import hash_password
from app.routers import auth, scraper, videos

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)
logger = logging.getLogger("mr_scrapper")


# ── Lifespan (startup / shutdown) ────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB tables on startup."""
    logger.info("🚀 Mr. Scrapper starting up...")
    await init_db()

    # Ensure media directories exist
    settings.videos_path
    settings.thumbs_path

    # Create default test user
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.email == "teste@email.com")
        result = await session.execute(stmt)
        test_user = result.scalar_one_or_none()

        if not test_user:
            hashed_password = hash_password("admin")
            new_user = User(
                name="Usuário de Teste",
                email="teste@email.com",
                hashed_password=hashed_password,
                is_verified=True,  # Bypass email verification
            )
            session.add(new_user)
            await session.commit()
            logger.info("✨ Default test user (teste@email.com / admin) created.")

    logger.info("✅ Database initialized, media dirs ready.")
    yield
    logger.info("👋 Mr. Scrapper shutting down.")


# ── FastAPI App ──────────────────────────────────────────────────

app = FastAPI(
    title="Mr. Scrapper API",
    description="Automated video database builder — API for scraping, streaming, and managing videos.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://localhost",
        settings.FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(videos.router)
app.include_router(scraper.router)


# ── Health Check ─────────────────────────────────────────────────

@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "Mr. Scrapper API",
        "version": "1.0.0",
    }
