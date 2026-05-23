"""
Mr. Scrapper — Downloader Service
Downloads video files via httpx and generates thumbnails via FFmpeg.
"""

import logging
import uuid
from pathlib import Path

import httpx

from app.config import settings
from app.utils.ffmpeg import extract_thumbnail, get_video_duration

logger = logging.getLogger(__name__)

# Timeout for large video downloads (5 min)
DOWNLOAD_TIMEOUT = httpx.Timeout(300.0, connect=30.0)


import asyncio
import yt_dlp

def _sync_yt_dlp_download(url: str, output_path: str):
    ydl_opts = {
        'outtmpl': output_path,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

async def download_video(
    url: str,
    filename: str | None = None,
) -> dict | None:
    """
    Download a video file from *url* and extract a thumbnail.

    Returns a dict with keys:
        video_path, thumb_path, file_size, duration
    or None on failure.
    """
    if not filename:
        ext = _guess_extension(url)
        filename = f"{uuid.uuid4().hex}{ext}"

    video_file = settings.videos_path / filename
    thumb_file = settings.thumbs_path / f"{Path(filename).stem}.jpg"

    try:
        if "youtube.com" in url or "youtu.be" in url or "tiktok.com" in url or not url.split("?")[0].endswith(".mp4"):
            logger.info(f"Using yt-dlp for {url}")
            await asyncio.to_thread(_sync_yt_dlp_download, url, str(video_file))
            file_size = video_file.stat().st_size
        else:
            logger.info(f"Using httpx for {url}")
            async with httpx.AsyncClient(
                timeout=DOWNLOAD_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            ) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    file_size = 0
                    with open(video_file, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=65536):
                            f.write(chunk)
                            file_size += len(chunk)

        logger.info(f"Downloaded {file_size} bytes → {video_file}")

        # Extract thumbnail
        thumb_ok = await extract_thumbnail(video_file, thumb_file)
        if not thumb_ok:
            thumb_file = None

        # Probe duration
        duration = await get_video_duration(video_file)

        return {
            "video_path": str(video_file.relative_to(Path(settings.MEDIA_PATH))),
            "thumb_path": str(thumb_file.relative_to(Path(settings.MEDIA_PATH))) if thumb_file else None,
            "file_size": file_size,
            "duration": duration,
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP {e.response.status_code} downloading {url}")
        _cleanup(video_file)
        return None
    except Exception as e:
        logger.error(f"Download failed for {url}: {e}")
        _cleanup(video_file)
        return None


def _guess_extension(url: str) -> str:
    """Best-effort file extension from URL."""
    path = url.split("?")[0].split("#")[0]
    if "." in path.split("/")[-1]:
        ext = "." + path.split("/")[-1].rsplit(".", 1)[-1]
        if len(ext) <= 5:
            return ext
    return ".mp4"


def _cleanup(path: Path) -> None:
    """Remove partial file silently."""
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
