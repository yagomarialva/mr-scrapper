"""
Mr. Scrapper — Videos Router
CRUD, streaming (HTTP 206), download, and thumbnail endpoints.
"""

import os
import stat
from pathlib import Path
from uuid import UUID

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User, Video
from app.schemas import VideoListResponse, VideoResponse, VideoUpdate
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/videos", tags=["Videos"])

CHUNK_SIZE = 1024 * 1024  # 1 MB chunks for streaming


def _build_video_response(video: Video, request: Request) -> VideoResponse:
    """Attach computed stream/download/thumb URLs to a VideoResponse."""
    base = str(request.base_url).rstrip("/")
    resp = VideoResponse.model_validate(video)
    resp.stream_url = f"{base}/api/videos/{video.id}/stream"
    resp.download_url = f"{base}/api/videos/{video.id}/download"
    if video.thumb_path:
        resp.thumb_url = f"{base}/api/videos/{video.id}/thumb"
    return resp


# ─────────────────────────────────────────────────────────────────
# GET /api/videos — List all videos (paginated)
# ─────────────────────────────────────────────────────────────────

@router.get("", response_model=VideoListResponse)
async def list_videos(
    request: Request,
    page: int = 1,
    page_size: int = 24,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """List all videos with pagination and optional search."""
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    offset = (page - 1) * page_size

    query = select(Video).where(Video.status == "completed")
    count_query = select(func.count(Video.id)).where(Video.status == "completed")

    if search:
        like_pattern = f"%{search}%"
        query = query.where(Video.title.ilike(like_pattern))
        count_query = count_query.where(Video.title.ilike(like_pattern))

    query = query.order_by(Video.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    videos = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return VideoListResponse(
        items=[_build_video_response(v, request) for v in videos],
        total=total,
        page=page,
        page_size=page_size,
    )


# ─────────────────────────────────────────────────────────────────
# GET /api/videos/{id} — Video details
# ─────────────────────────────────────────────────────────────────

@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get a single video's details."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado.")

    return _build_video_response(video, request)

# ─────────────────────────────────────────────────────────────────
# GET /api/videos/{id}/next — Get next video
# ─────────────────────────────────────────────────────────────────

@router.get("/{video_id}/next", response_model=VideoResponse)
async def get_next_video(
    video_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get the next video in chronological order."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    current_video = result.scalar_one_or_none()

    if not current_video:
        raise HTTPException(status_code=404, detail="Vídeo atual não encontrado.")

    # Find the next video (older than current, since list is ordered DESC)
    next_result = await db.execute(
        select(Video)
        .where(Video.status == "completed")
        .where(Video.created_at < current_video.created_at)
        .order_by(Video.created_at.desc())
        .limit(1)
    )
    next_video = next_result.scalar_one_or_none()

    if not next_video:
        # If no older video, loop back to the newest video
        newest_result = await db.execute(
            select(Video)
            .where(Video.status == "completed")
            .where(Video.id != video_id)
            .order_by(Video.created_at.desc())
            .limit(1)
        )
        next_video = newest_result.scalar_one_or_none()

    if not next_video:
         raise HTTPException(status_code=404, detail="Não há próximo vídeo.")

    return _build_video_response(next_video, request)


# ─────────────────────────────────────────────────────────────────
# GET /api/videos/{id}/stream — HTTP 206 Range Streaming
# ─────────────────────────────────────────────────────────────────

@router.get("/{video_id}/stream")
async def stream_video(
    video_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Stream a video file with HTTP 206 Partial Content support.
    Enables seeking in the browser <video> player.
    NOTE: Streaming is public (no auth) so <video src="..."> works directly.
    """
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado.")

    file_path = Path(settings.MEDIA_PATH) / video.video_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de vídeo não encontrado no disco.")

    file_size = file_path.stat().st_size
    content_type = "video/mp4"

    range_header = request.headers.get("range")

    if range_header:
        # Parse Range: bytes=START-END
        range_spec = range_header.replace("bytes=", "")
        parts = range_spec.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else file_size - 1
        end = min(end, file_size - 1)

        content_length = end - start + 1

        async def _range_generator():
            async with aiofiles.open(file_path, "rb") as f:
                await f.seek(start)
                remaining = content_length
                while remaining > 0:
                    read_size = min(CHUNK_SIZE, remaining)
                    chunk = await f.read(read_size)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return StreamingResponse(
            _range_generator(),
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Cache-Control": "no-cache",
            },
        )
    else:
        # Full file response
        async def _full_generator():
            async with aiofiles.open(file_path, "rb") as f:
                while chunk := await f.read(CHUNK_SIZE):
                    yield chunk

        return StreamingResponse(
            _full_generator(),
            media_type=content_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            },
        )


# ─────────────────────────────────────────────────────────────────
# GET /api/videos/{id}/download — Download with Content-Disposition
# ─────────────────────────────────────────────────────────────────

@router.get("/{video_id}/download")
async def download_video(
    video_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Download a video file with Content-Disposition: attachment."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado.")

    file_path = Path(settings.MEDIA_PATH) / video.video_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de vídeo não encontrado no disco.")

    # Sanitize filename for download
    safe_name = "".join(
        c if c.isalnum() or c in "._- " else "_"
        for c in video.title
    )[:100]
    ext = file_path.suffix or ".mp4"
    download_name = f"{safe_name}{ext}"

    return FileResponse(
        path=str(file_path),
        filename=download_name,
        media_type="application/octet-stream",
    )


# ─────────────────────────────────────────────────────────────────
# GET /api/videos/{id}/thumb — Serve thumbnail
# ─────────────────────────────────────────────────────────────────

@router.get("/{video_id}/thumb")
async def get_thumbnail(
    video_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Serve the video's thumbnail image."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()

    if not video or not video.thumb_path:
        raise HTTPException(status_code=404, detail="Thumbnail não encontrada.")

    thumb_path = Path(settings.MEDIA_PATH) / video.thumb_path

    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de thumbnail não encontrado no disco.")

    return FileResponse(
        path=str(thumb_path),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ─────────────────────────────────────────────────────────────────
# PUT /api/videos/{id} — Update metadata
# ─────────────────────────────────────────────────────────────────

@router.put("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: UUID,
    payload: VideoUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Update a video's title, description, and/or tags."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado.")

    if payload.title is not None:
        video.title = payload.title
    if payload.description is not None:
        video.description = payload.description
    if payload.tags is not None:
        video.tags = payload.tags

    await db.commit()
    await db.refresh(video)

    return _build_video_response(video, request)


# ─────────────────────────────────────────────────────────────────
# DELETE /api/videos/{id} — Delete video (DB + disk)
# ─────────────────────────────────────────────────────────────────

@router.delete("/{video_id}", response_model=dict)
async def delete_video(
    video_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Delete a video from the database AND remove files from disk."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado.")

    # Delete files from disk
    video_file = Path(settings.MEDIA_PATH) / video.video_path
    if video_file.exists():
        video_file.unlink()

    if video.thumb_path:
        thumb_file = Path(settings.MEDIA_PATH) / video.thumb_path
        if thumb_file.exists():
            thumb_file.unlink()

    # Delete from database
    await db.delete(video)
    await db.commit()

    return {"message": "Vídeo excluído com sucesso.", "id": str(video_id)}
