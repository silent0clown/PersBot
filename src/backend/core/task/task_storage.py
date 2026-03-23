import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import logging

from .task_models import TaskModel, TaskFilter, TaskStatus

logger = logging.getLogger(__name__)


class TaskStorage:
    def __init__(self, storage_path: Optional[str] = None):
        self._tasks: Dict[UUID, TaskModel] = {}
        self._storage_path = storage_path
        self._lock = asyncio.Lock()
        
        if storage_path:
            self._load_from_disk()

    def _load_from_disk(self):
        try:
            path = Path(self._storage_path)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_dict in data.get('tasks', []):
                        task = TaskModel(**task_dict)
                        self._tasks[task.id] = task
                logger.info(f"Loaded {len(self._tasks)} tasks from {self._storage_path}")
        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")

    def _save_to_disk(self):
        if not self._storage_path:
            return
        try:
            path = Path(self._storage_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'version': 1,
                'updated_at': datetime.now().isoformat(),
                'tasks': [task.model_dump(mode='json') for task in self._tasks.values()]
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")

    async def create(self, task: TaskModel) -> TaskModel:
        async with self._lock:
            self._tasks[task.id] = task
            if task.parent_id and task.parent_id in self._tasks:
                parent = self._tasks[task.parent_id]
                parent.subtasks.append(task.id)
            self._save_to_disk()
            logger.info(f"Created task: {task.id}")
            return task

    async def get(self, task_id: UUID) -> Optional[TaskModel]:
        return self._tasks.get(task_id)

    async def update(self, task_id: UUID, task_update: TaskModel) -> Optional[TaskModel]:
        async with self._lock:
            if task_id not in self._tasks:
                return None
            task = self._tasks[task_id]
            for field, value in task_update.model_dump(exclude={'id', 'created_at'}).items():
                if value is not None:
                    setattr(task, field, value)
            task.updated_at = datetime.now()
            self._save_to_disk()
            logger.info(f"Updated task: {task_id}")
            return task

    async def delete(self, task_id: UUID) -> bool:
        async with self._lock:
            if task_id not in self._tasks:
                return False
            task = self._tasks[task_id]
            
            for subtask_id in task.subtasks:
                await self.delete(subtask_id)
            
            if task.parent_id and task.parent_id in self._tasks:
                parent = self._tasks[task.parent_id]
                if task_id in parent.subtasks:
                    parent.subtasks.remove(task_id)
            
            del self._tasks[task_id]
            self._save_to_disk()
            logger.info(f"Deleted task: {task_id}")
            return True

    async def list(self, filter_obj: Optional[TaskFilter] = None) -> List[TaskModel]:
        tasks = list(self._tasks.values())
        
        if not filter_obj:
            return sorted(tasks, key=lambda t: (t.priority != 'high', t.created_at), reverse=True)
        
        if filter_obj.status:
            tasks = [t for t in tasks if t.status == filter_obj.status]
        if filter_obj.priority:
            tasks = [t for t in tasks if t.priority == filter_obj.priority]
        if filter_obj.tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in filter_obj.tags)]
        if filter_obj.parent_id:
            tasks = [t for t in tasks if t.parent_id == filter_obj.parent_id]
        if filter_obj.due_before:
            tasks = [t for t in tasks if t.due_date and t.due_date < filter_obj.due_before]
        if filter_obj.due_after:
            tasks = [t for t in tasks if t.due_date and t.due_date > filter_obj.due_after]
            
        return sorted(tasks, key=lambda t: (t.priority != 'high', t.created_at), reverse=True)

    async def get_subtasks(self, parent_id: UUID) -> List[TaskModel]:
        parent = self._tasks.get(parent_id)
        if not parent:
            return []
        return [self._tasks[sid] for sid in parent.subtasks if sid in self._tasks]

    async def get_dependencies_satisfied(self, task_id: UUID) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        for dep_id in task.dependencies:
            dep = self._tasks.get(dep_id)
            if not dep or dep.status != TaskStatus.COMPLETED:
                return False
        return True

    async def get_ready_tasks(self) -> List[TaskModel]:
        tasks = []
        for task in self._tasks.values():
            if task.status == TaskStatus.PENDING and await self.get_dependencies_satisfied(task.id):
                tasks.append(task)
        return sorted(tasks, key=lambda t: (t.priority != 'high', t.created_at))