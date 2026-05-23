"""
Mr. Scrapper — ORM Models
User (authentication) and Video (media catalog).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Registered user with email-verified access."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Video(Base):
    """Scraped / downloaded video entry with metadata."""

    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True, default=list
    )

    # File paths (relative to MEDIA_PATH)
    video_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    thumb_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Source info
    source_url: Mapped[str] = mapped_column(
        String(2000), unique=True, nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")

    # Media metadata
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Status: pending | downloading | completed | failed
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self) -> str:
        return f"<Video {self.title[:40]}>"
