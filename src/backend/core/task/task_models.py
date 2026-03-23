from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TaskPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskModel(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    tags: List[str] = Field(default_factory=list)
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    dependencies: List[UUID] = Field(default_factory=list)
    parent_id: Optional[UUID] = None
    subtasks: List[UUID] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class TaskFilter(BaseModel):
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    tags: Optional[List[str]] = None
    parent_id: Optional[UUID] = None
    due_before: Optional[datetime] = None
    due_after: Optional[datetime] = None


class TaskUpdate(BaseModel):
    content: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    tags: Optional[List[str]] = None
    due_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskCreate(BaseModel):
    content: str
    priority: TaskPriority = TaskPriority.MEDIUM
    tags: List[str] = Field(default_factory=list)
    due_date: Optional[datetime] = None
    dependencies: List[UUID] = Field(default_factory=list)
    parent_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)