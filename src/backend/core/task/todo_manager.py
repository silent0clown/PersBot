import asyncio
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from uuid import UUID
import logging

from .task_models import (
    TaskModel, TaskStatus, TaskPriority, 
    TaskFilter, TaskUpdate, TaskCreate
)
from .task_storage import TaskStorage
from .task_queue import TaskQueue, TaskScheduler

logger = logging.getLogger(__name__)


class TodoManager:
    def __init__(self, storage_path: Optional[str] = None, max_concurrent: int = 5):
        self._storage = TaskStorage(storage_path)
        self._queue = TaskQueue(self._storage, max_concurrent)
        self._scheduler = TaskScheduler(self._storage)
        self._change_listeners: List[Callable] = []

    async def initialize(self):
        await self._queue.start()
        logger.info("TodoManager initialized")

    async def shutdown(self):
        await self._queue.stop()
        logger.info("TodoManager shutdown")

    def add_change_listener(self, listener: Callable):
        self._change_listeners.append(listener)

    async def _notify_change(self, task: TaskModel, action: str):
        for listener in self._change_listeners:
            try:
                await listener(task, action)
            except Exception as e:
                logger.error(f"Listener error: {e}")

    async def create_task(self, task_data: TaskCreate) -> TaskModel:
        task = TaskModel(
            content=task_data.content,
            priority=task_data.priority,
            tags=task_data.tags,
            due_date=task_data.due_date,
            dependencies=task_data.dependencies,
            parent_id=task_data.parent_id,
            metadata=task_data.metadata
        )
        created = await self._storage.create(task)
        await self._notify_change(created, 'created')
        return created

    async def get_task(self, task_id: UUID) -> Optional[TaskModel]:
        return await self._storage.get(task_id)

    async def update_task(self, task_id: UUID, update: TaskUpdate) -> Optional[TaskModel]:
        existing = await self._storage.get(task_id)
        if not existing:
            return None
        
        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(existing, field, value)
        existing.updated_at = datetime.now()
        
        if update.status == TaskStatus.COMPLETED:
            existing.completed_at = datetime.now()
        
        updated = await self._storage.update(task_id, existing)
        await self._notify_change(updated, 'updated')
        return updated

    async def delete_task(self, task_id: UUID) -> bool:
        task = await self._storage.get(task_id)
        if not task:
            return False
        result = await self._storage.delete(task_id)
        if result:
            await self._notify_change(task, 'deleted')
        return result

    async def list_tasks(self, filter_obj: Optional[TaskFilter] = None) -> List[TaskModel]:
        return await self._storage.list(filter_obj)

    async def get_subtasks(self, parent_id: UUID) -> List[TaskModel]:
        return await self._storage.get_subtasks(parent_id)

    async def complete_task(self, task_id: UUID) -> Optional[TaskModel]:
        return await self.update_task(task_id, TaskUpdate(status=TaskStatus.COMPLETED))

    async def cancel_task(self, task_id: UUID) -> Optional[TaskModel]:
        return await self.update_task(task_id, TaskUpdate(status=TaskStatus.CANCELLED))

    async def reopen_task(self, task_id: UUID) -> Optional[TaskModel]:
        return await self.update_task(task_id, TaskUpdate(status=TaskStatus.PENDING))

    async def add_subtask(self, parent_id: UUID, task_data: TaskCreate) -> Optional[TaskModel]:
        task_data.parent_id = parent_id
        return await self.create_task(task_data)

    async def add_dependency(self, task_id: UUID, depends_on: UUID) -> bool:
        task = await self._storage.get(task_id)
        if not task:
            return False
        if depends_on not in task.dependencies:
            task.dependencies.append(depends_on)
            await self._storage.update(task_id, task)
        return True

    async def remove_dependency(self, task_id: UUID, depends_on: UUID) -> bool:
        task = await self._storage.get(task_id)
        if not task:
            return False
        if depends_on in task.dependencies:
            task.dependencies.remove(depends_on)
            await self._storage.update(task_id, task)
        return True

    async def get_ready_tasks(self) -> List[TaskModel]:
        return await self._storage.get_ready_tasks()

    async def enqueue_task(self, task_id: UUID) -> Optional[TaskModel]:
        task = await self._storage.get(task_id)
        if not task:
            return None
        return await self._queue.enqueue(task)

    async def get_queue_status(self) -> dict:
        return await self._queue.get_status()

    async def get_task_tree(self, root_id: Optional[UUID] = None) -> Dict[str, Any]:
        if root_id:
            tasks = await self._storage.get_subtasks(root_id)
        else:
            tasks = await self._storage.list(TaskFilter(parent_id=None))
        
        tree = []
        for task in tasks:
            subtree = await self._build_tree(task)
            tree.append(subtree)
        return {'tasks': tree, 'total': len(tree)}

    async def _build_tree(self, task: TaskModel) -> Dict[str, Any]:
        subtasks = await self._storage.get_subtasks(task.id)
        return {
            'task': task.model_dump(mode='json'),
            'subtasks': [await self._build_tree(st) for st in subtasks]
        }

    async def get_statistics(self) -> Dict[str, Any]:
        all_tasks = await self._storage.list()
        
        by_priority = {p.value: 0 for p in TaskPriority}
        by_status = {s.value: 0 for s in TaskStatus}
        by_tags: Dict[str, int] = {}
        
        for task in all_tasks:
            by_priority[task.priority] += 1
            by_status[task.status] += 1
            for tag in task.tags:
                by_tags[tag] = by_tags.get(tag, 0) + 1
        
        overdue = len([t for t in all_tasks if t.due_date and t.due_date < datetime.now() and t.status != TaskStatus.COMPLETED])
        
        return {
            'total': len(all_tasks),
            'by_priority': by_priority,
            'by_status': by_status,
            'by_tags': by_tags,
            'overdue': overdue
        }