"""
Mr. Scrapper — Scraper Router
Start, stop, and monitor scraping tasks.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import User
from app.schemas import MessageResponse, ScrapeRequest, ScrapeStatus
from app.services.auth_service import get_current_user
from app.services.scraper_engine import run_scraper
from app.services.task_manager import start_task, stop_task, task_state

router = APIRouter(prefix="/api/scraper", tags=["Scraper"])


# ─────────────────────────────────────────────────────────────────
# POST /api/scraper/start
# ─────────────────────────────────────────────────────────────────

@router.post("/start", response_model=MessageResponse)
async def start_scraping(
    payload: ScrapeRequest,
    _current_user: User = Depends(get_current_user),
):
    """
    Start a background scraping task or enqueue it.
    """
    async def _factory():
        await run_scraper(payload.query, payload.target_count)

    await start_task(_factory, payload.query, payload.target_count)

    return MessageResponse(
        message=f"Busca enfileirada: '{payload.query}' — meta: {payload.target_count} vídeos.",
    )


# ─────────────────────────────────────────────────────────────────
# GET /api/scraper/status
# ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=ScrapeStatus)
async def get_scrape_status(
    _current_user: User = Depends(get_current_user),
):
    """Return the current scraping task status and queue."""
    return ScrapeStatus(
        is_running=task_state.is_running,
        query=task_state.query,
        target_count=task_state.target_count,
        downloaded_count=task_state.downloaded_count,
        failed_count=task_state.failed_count,
        progress_percent=task_state.progress_percent,
        errors=task_state.errors[-10:],  # Last 10 errors
        queue=task_state.queue,
    )


# ─────────────────────────────────────────────────────────────────
# POST /api/scraper/stop
# ─────────────────────────────────────────────────────────────────

@router.post("/stop", response_model=MessageResponse)
async def stop_scraping(
    _current_user: User = Depends(get_current_user),
):
    """Stop the currently running scraping task and clear the queue."""
    stopped = await stop_task()

    if not stopped:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma tarefa de scraping está em execução.",
        )

    return MessageResponse(message="Scraping interrompido e fila esvaziada.")


# ─────────────────────────────────────────────────────────────────
# DELETE /api/scraper/queue/{job_id}
# ─────────────────────────────────────────────────────────────────

@router.delete("/queue/{job_id}", response_model=MessageResponse)
async def remove_from_queue(
    job_id: str,
    _current_user: User = Depends(get_current_user),
):
    """Remove a pending scrape job from the queue."""
    removed = task_state.remove_from_queue(job_id)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Busca não encontrada na fila.",
        )

    return MessageResponse(message="Busca removida da fila.")
