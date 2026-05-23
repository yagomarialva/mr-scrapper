"""
Mr. Scrapper — Async Task Manager
Manages background scraping tasks with progress tracking.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Callable, Coroutine, Any

logger = logging.getLogger(__name__)


@dataclass
class TaskState:
    """Shared mutable state for a running scrape task."""
    is_running: bool = False
    query: str | None = None
    target_count: int = 0
    downloaded_count: int = 0
    failed_count: int = 0
    errors: list[str] = field(default_factory=list)
    queue: list[dict] = field(default_factory=list)
    _task: asyncio.Task | None = field(default=None, repr=False)

    @property
    def progress_percent(self) -> float:
        if self.target_count == 0:
            return 0.0
        return round((self.downloaded_count / self.target_count) * 100, 1)

    def reset(self, query: str, target_count: int) -> None:
        self.is_running = True
        self.query = query
        self.target_count = target_count
        self.downloaded_count = 0
        self.failed_count = 0
        self.errors.clear()

    def increment_downloaded(self) -> None:
        self.downloaded_count += 1

    def increment_failed(self, error: str = "") -> None:
        self.failed_count += 1
        if error:
            self.errors.append(error)
            # Keep only last 50 errors
            if len(self.errors) > 50:
                self.errors = self.errors[-50:]

    def finish(self) -> None:
        self.is_running = False

    def enqueue(self, query: str, target_count: int, factory: Callable) -> str:
        job_id = str(uuid.uuid4())
        self.queue.append({
            "id": job_id,
            "query": query,
            "target_count": target_count,
            "factory": factory,
        })
        return job_id

    def remove_from_queue(self, job_id: str) -> bool:
        initial_len = len(self.queue)
        self.queue = [item for item in self.queue if item["id"] != job_id]
        return len(self.queue) < initial_len


# Global singleton — shared across the entire FastAPI process
task_state = TaskState()


async def _process_queue() -> None:
    if task_state.is_running:
        return

    task_state.is_running = True
    while task_state.queue:
        job = task_state.queue.pop(0)
        task_state.reset(job["query"], job["target_count"])
        
        try:
            await job["factory"]()
        except asyncio.CancelledError:
            logger.info("Scrape task cancelled.")
            break
        except Exception as e:
            logger.exception(f"Scrape task crashed: {e}")
            task_state.increment_failed(str(e))
            
    task_state.finish()


async def start_task(
    coro_factory: Callable[[], Coroutine[Any, Any, None]],
    query: str,
    target_count: int,
) -> bool:
    """
    Enqueue a background asyncio task.
    Returns True always.
    """
    task_state.enqueue(query, target_count, coro_factory)
    
    if not task_state.is_running:
        task_state._task = asyncio.create_task(_process_queue())
        
    return True


async def stop_task() -> bool:
    """Cancel the current running task and clear the queue."""
    if not task_state.is_running or task_state._task is None:
        return False

    task_state._task.cancel()
    try:
        await task_state._task
    except asyncio.CancelledError:
        pass

    task_state.finish()
    task_state.queue.clear()
    return True
