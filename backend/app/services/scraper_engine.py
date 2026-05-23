"""
Mr. Scrapper — Scraper Engine
Searches for free/AI-generated videos on Pexels and Pixabay
using direct HTTP requests (no API keys).
"""

import asyncio
import logging
import random
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Video
from app.services.downloader import download_video
from app.services.task_manager import task_state

logger = logging.getLogger(__name__)

# ── User-Agent Rotation ─────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:126.0) Gecko/20100101 Firefox/126.0",
]


@dataclass
class VideoCandidate:
    """A scraped video link candidate before download."""
    title: str
    source_url: str
    download_url: str
    platform: str
    description: str = ""
    tags: list[str] | None = None


from playwright.async_api import async_playwright, Page
import yt_dlp

# ─────────────────────────────────────────────────────────────────
# Platform Scrapers
# ─────────────────────────────────────────────────────────────────

async def _scrape_pexels(page: Page, query: str, page_num: int) -> list[VideoCandidate]:
    """Scrape Pexels video search results (Playwright)."""
    candidates = []
    url = f"https://www.pexels.com/search/videos/{query}/?page={page_num}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000) # Wait for JS rendering / Cloudflare
        
        content = await page.content()
        soup = BeautifulSoup(content, "lxml")
        
        articles = soup.select("article")
        for article in articles:
            video_tag = article.find("video")
            link_tag = article.find("a", href=True)

            if video_tag and video_tag.get("src"):
                source_url = link_tag["href"] if link_tag else ""
                if not source_url.startswith("http"):
                    source_url = f"https://www.pexels.com{source_url}"

                title_el = article.find("h2") or article.find("p")
                title = title_el.get_text(strip=True) if title_el else query

                candidates.append(VideoCandidate(
                    title=title or f"Pexels - {query}",
                    source_url=source_url,
                    download_url=video_tag["src"],
                    platform="pexels",
                    tags=[query],
                ))
    except Exception as e:
        logger.warning(f"Pexels scrape failed (page {page_num}): {e}")
    return candidates

async def _scrape_pixabay(page: Page, query: str, page_num: int) -> list[VideoCandidate]:
    """Scrape Pixabay video search results (Playwright)."""
    candidates = []
    url = f"https://pixabay.com/videos/search/?q={query}&pagi={page_num}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)
        
        content = await page.content()
        soup = BeautifulSoup(content, "lxml")
        
        containers = soup.select("div.container--MwyXl")
        if not containers:
            containers = soup.select("[class*='container']")

        for container in containers:
            video_tag = container.find("video")
            link_tag = container.find("a", href=True)

            if video_tag and video_tag.get("src"):
                source_url = link_tag["href"] if link_tag else ""
                if source_url and not source_url.startswith("http"):
                    source_url = f"https://pixabay.com{source_url}"

                candidates.append(VideoCandidate(
                    title=f"Pixabay - {query}",
                    source_url=source_url or video_tag["src"],
                    download_url=video_tag["src"],
                    platform="pixabay",
                    tags=[query],
                ))
    except Exception as e:
        logger.warning(f"Pixabay scrape failed (page {page_num}): {e}")
    return candidates

async def _scrape_youtube_fallback(query: str, count: int = 5) -> list[VideoCandidate]:
    """Fallback using yt-dlp to search YouTube/Google for generic videos."""
    candidates = []
    try:
        def _search():
            ydl_opts = {
                'extract_flat': True,
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(f"ytsearch{count}:{query} free copyright video", download=False)
                
        result = await asyncio.to_thread(_search)
        if result and "entries" in result:
            for entry in result["entries"]:
                candidates.append(VideoCandidate(
                    title=entry.get("title", f"YT - {query}"),
                    source_url=entry.get("url"),
                    download_url=entry.get("url"), # yt-dlp handles source URLs
                    platform="youtube",
                    tags=[query],
                ))
    except Exception as e:
        logger.warning(f"YouTube fallback failed: {e}")
    return candidates

# ─────────────────────────────────────────────────────────────────
# Main Scraping Loop
# ─────────────────────────────────────────────────────────────────

async def run_scraper(query: str, target_count: int) -> None:
    page_num = 1
    max_empty_pages = 5
    empty_streak = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()

        while task_state.downloaded_count < target_count and task_state.is_running:
            all_candidates: list[VideoCandidate] = []

            # Try Playwright scrapers
            for scraper_fn in [_scrape_pexels, _scrape_pixabay]:
                candidates = await scraper_fn(page, query, page_num)
                all_candidates.extend(candidates)
                await asyncio.sleep(random.uniform(1.5, 4.0))

            # If Playwright fails completely, fallback to yt-dlp
            if not all_candidates and page_num == 1:
                logger.info("Primary sources failed or returned empty on page 1. Trying YouTube fallback...")
                fallback_candidates = await _scrape_youtube_fallback(query, count=target_count)
                all_candidates.extend(fallback_candidates)

            if not all_candidates:
                empty_streak += 1
                logger.info(f"No candidates on page {page_num}. Empty streak: {empty_streak}/{max_empty_pages}")
                if empty_streak >= max_empty_pages:
                    logger.warning("Max empty pages reached. Stopping.")
                    break
                page_num += 1
                await asyncio.sleep(random.uniform(2.0, 5.0))
                continue

            empty_streak = 0

            for candidate in all_candidates:
                if task_state.downloaded_count >= target_count or not task_state.is_running:
                    break

                async with AsyncSessionLocal() as db:
                    existing = await db.execute(select(Video).where(Video.source_url == candidate.source_url))
                    if existing.scalar_one_or_none() is not None:
                        logger.debug(f"Skipping duplicate: {candidate.source_url}")
                        continue

                logger.info(f"[{task_state.downloaded_count + 1}/{target_count}] Downloading: {candidate.title}")

                result = await download_video(candidate.download_url)
                if result is None:
                    task_state.increment_failed(f"Download failed: {candidate.download_url}")
                    continue

                async with AsyncSessionLocal() as db:
                    video = Video(
                        title=candidate.title,
                        description=candidate.description,
                        tags=candidate.tags,
                        video_path=result["video_path"],
                        thumb_path=result["thumb_path"],
                        source_url=candidate.source_url,
                        platform=candidate.platform,
                        duration=result["duration"],
                        file_size=result["file_size"],
                        status="completed",
                    )
                    db.add(video)
                    await db.commit()

                task_state.increment_downloaded()
                logger.info(f"✅ Saved [{task_state.downloaded_count}/{target_count}]: {candidate.title}")
                await asyncio.sleep(random.uniform(2.0, 6.0))

            page_num += 1

        await browser.close()

    logger.info(f"Scraping complete. Downloaded: {task_state.downloaded_count}, Failed: {task_state.failed_count}")
