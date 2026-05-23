"""
Mr. Scrapper — Pydantic Schemas
Request / response DTOs for the API layer.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ─────────────────────────────────────────────────────────────────
# Auth Schemas
# ─────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    """Payload for POST /api/auth/register."""
    name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Payload for POST /api/auth/login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token returned after login."""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public user data."""
    id: uuid.UUID
    name: str
    email: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    detail: str | None = None


# ─────────────────────────────────────────────────────────────────
# Video Schemas
# ─────────────────────────────────────────────────────────────────

class VideoUpdate(BaseModel):
    """Payload for PUT /api/videos/{id}."""
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    tags: list[str] | None = None


class VideoResponse(BaseModel):
    """Video data returned by the API."""
    id: uuid.UUID
    title: str
    description: str | None
    tags: list[str] | None

    video_path: str
    thumb_path: str | None

    source_url: str
    platform: str
    duration: float | None
    file_size: int | None
    status: str

    created_at: datetime
    updated_at: datetime

    # Computed URLs (set by the router, not the DB)
    stream_url: str | None = None
    download_url: str | None = None
    thumb_url: str | None = None

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    """Paginated list of videos."""
    items: list[VideoResponse]
    total: int
    page: int
    page_size: int


# ─────────────────────────────────────────────────────────────────
# Scraper Schemas
# ─────────────────────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    """Payload for POST /api/scraper/start."""
    query: str = Field(..., min_length=1, max_length=200)
    target_count: int = Field(..., ge=1, le=500)


class ScrapeQueueItem(BaseModel):
    """An item waiting in the scraper queue."""
    id: str
    query: str
    target_count: int


class ScrapeStatus(BaseModel):
    """Current scraping task status."""
    is_running: bool
    query: str | None = None
    target_count: int = 0
    downloaded_count: int = 0
    failed_count: int = 0
    progress_percent: float = 0.0
    errors: list[str] = []
    queue: list[ScrapeQueueItem] = []
