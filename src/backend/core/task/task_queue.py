import asyncio
from typing import Optional, Callable, List, Any
from datetime import datetime, timedelta
from uuid import UUID
import logging

from .task_models import TaskModel, TaskStatus, TaskPriority
from .task_storage import TaskStorage

logger = logging.getLogger(__name__)


class TaskQueue:
    def __init__(self, storage: TaskStorage, max_concurrent: int = 5):
        self._storage = storage
        self._max_concurrent = max_concurrent
        self._running_tasks: asyncio.Set[UUID] = asyncio.Semaphore(max_concurrent)
        self._task_handlers: dict[str, Callable] = {}
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

    def register_handler(self, task_type: str, handler: Callable):
        self._task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")

    async def start(self):
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("Task queue started")

    async def stop(self):
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Task queue stopped")

    async def _worker(self):
        while self._running:
            try:
                ready_tasks = await self._storage.get_ready_tasks()
                if ready_tasks:
                    task = ready_tasks[0]
                    asyncio.create_task(self._execute_task(task))
                    await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)

    async def _execute_task(self, task: TaskModel):
        async with self._running_tasks:
            try:
                task.status = TaskStatus.IN_PROGRESS
                task.updated_at = datetime.now()
                await self._storage.update(task.id, task)
                
                handler = self._task_handlers.get(task.metadata.get('type', 'default'))
                if handler:
                    result = await handler(task)
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now()
                    task.metadata['result'] = result
                else:
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now()
                
                await self._storage.update(task.id, task)
                logger.info(f"Task completed: {task.id}")
                
            except Exception as e:
                logger.error(f"Task execution failed: {e}")
                task.status = TaskStatus.FAILED
                task.metadata['error'] = str(e)
                await self._storage.update(task.id, task)

    async def enqueue(self, task: TaskModel) -> TaskModel:
        if await self._storage.get_dependencies_satisfied(task.id) or not task.dependencies:
            task.status = TaskStatus.PENDING
        else:
            task.status = TaskStatus.PENDING
        return await self._storage.create(task)

    async def get_status(self) -> dict:
        all_tasks = await self._storage.list()
        return {
            'total': len(all_tasks),
            'pending': len([t for t in all_tasks if t.status == TaskStatus.PENDING]),
            'in_progress': len([t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS]),
            'completed': len([t for t in all_tasks if t.status == TaskStatus.COMPLETED]),
            'failed': len([t for t in all_tasks if t.status == TaskStatus.FAILED]),
            'running': self._running
        }


class TaskScheduler:
    def __init__(self, storage: TaskStorage):
        self._storage = storage
        self._scheduled_tasks: dict[str, asyncio.Task] = {}
        self._callbacks: List[Callable] = []

    def schedule_recurring(self, task_id: str, interval: timedelta, callback: Callable):
        async def run():
            while True:
                try:
                    await callback()
                    await asyncio.sleep(interval.total_seconds())
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Scheduled task error: {e}")
        
        self._scheduled_tasks[task_id] = asyncio.create_task(run())
        logger.info(f"Scheduled recurring task: {task_id}")

    def cancel_scheduled(self, task_id: str):
        if task_id in self._scheduled_tasks:
            self._scheduled_tasks[task_id].cancel()
            del self._scheduled_tasks[task_id]

    def register_callback(self, callback: Callable):
        self._callbacks.append(callback)

    async def notify_change(self, task: TaskModel):
        for cb in self._callbacks:
            try:
                await cb(task)
            except Exception as e:
                logger.error(f"Callback error: {e}")