"""
Mr. Scrapper — Application Settings
Loads configuration from environment variables / .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    """Application-wide settings loaded from environment."""

    # ── PostgreSQL ───────────────────────────────────────────────
    POSTGRES_USER: str = "mrscrap"
    POSTGRES_PASSWORD: str = "mrscrap_secret_2024"
    POSTGRES_DB: str = "mrscrap_db"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql+asyncpg://mrscrap:mrscrap_secret_2024@db:5432/mrscrap_db"

    # ── JWT ──────────────────────────────────────────────────────
    JWT_SECRET: str = "super-secret-change-me-in-production-abc123xyz"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours
    JWT_EMAIL_CONFIRM_EXPIRATION_HOURS: int = 24

    # ── SMTP (Email Confirmation) ────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_FROM_NAME: str = "Mr. Scrapper"

    # ── Frontend ─────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:4200"

    # ── Telegram Bot ─────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # ── Media Paths ──────────────────────────────────────────────
    MEDIA_PATH: str = "/app/media"

    @property
    def videos_path(self) -> Path:
        p = Path(self.MEDIA_PATH) / "videos"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def thumbs_path(self) -> Path:
        p = Path(self.MEDIA_PATH) / "thumbs"
        p.mkdir(parents=True, exist_ok=True)
        return p

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
