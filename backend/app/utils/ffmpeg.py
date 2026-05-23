"""
Mr. Scrapper — FFmpeg Utilities
Extract thumbnails and probe video metadata.
"""

import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def extract_thumbnail(
    video_path: str | Path,
    output_path: str | Path,
    timestamp: float = 1.0,
) -> bool:
    """
    Extract a single frame from *video_path* at the given timestamp
    and save it as a JPEG to *output_path*.
    Returns True on success.
    """
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_path),
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.error(f"FFmpeg thumbnail extraction failed: {stderr.decode()}")
        return False

    logger.info(f"Thumbnail extracted: {output_path}")
    return True


async def get_video_duration(video_path: str | Path) -> float | None:
    """
    Use ffprobe to get video duration in seconds.
    Returns None if the probe fails.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(video_path),
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()

    if proc.returncode != 0:
        return None

    try:
        data = json.loads(stdout.decode())
        return float(data["format"]["duration"])
    except (json.JSONDecodeError, KeyError, ValueError):
        return None
