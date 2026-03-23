from typing import Optional, Dict, Any, List, Callable
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class AgentCapability(BaseModel):
    name: str
    description: str
    params: Dict[str, Any] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    name: str
    description: str = ""
    model: str = "default"
    max_steps: int = 100
    timeout: int = 300
    capabilities: List[AgentCapability] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    system_prompt: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentTask(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    description: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    status: AgentStatus = AgentStatus.IDLE
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    steps: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


@dataclass
class AgentState:
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[AgentTask] = None
    task_history: List[AgentTask] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    last_error: Optional[str] = None


class BaseAgent:
    def __init__(self, config: AgentConfig, parent: Optional['BaseAgent'] = None):
        self.config = config
        self.id = uuid4()
        self.parent = parent
        self.children: List[BaseAgent] = []
        self.state = AgentState()
        self._handlers: Dict[str, Callable] = {}
        self._running = False
        self._task_queue: asyncio.Queue = asyncio.Queue()
        
    def register_handler(self, event: str, handler: Callable):
        self._handlers[event] = handler
        
    async def _emit(self, event: str, *args, **kwargs):
        if event in self._handlers:
            handler = self._handlers[event]
            if asyncio.iscoroutinefunction(handler):
                await handler(*args, **kwargs)
            else:
                handler(*args, **kwargs)
                
    async def spawn_child(self, config: AgentConfig) -> 'BaseAgent':
        child = SubAgent(config, parent=self)
        self.children.append(child)
        await self._emit('child_spawned', child)
        return child
        
    async def terminate_child(self, child_id: UUID) -> bool:
        for child in self.children:
            if child.id == child_id:
                await child.terminate()
                self.children.remove(child)
                return True
        return False
        
    async def assign_task(self, task: AgentTask):
        await self._task_queue.put(task)
        await self._emit('task_assigned', task)
        
    async def execute_task(self, task: AgentTask) -> Any:
        task.status = AgentStatus.RUNNING
        task.started_at = datetime.now()
        self.state.current_task = task
        self.state.status = AgentStatus.RUNNING
        
        try:
            await self._emit('task_started', task)
            
            result = await self._run_task(task)
            
            task.status = AgentStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()
            self.state.status = AgentStatus.IDLE
            
            await self._emit('task_completed', task, result)
            return result
            
        except Exception as e:
            task.status = AgentStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            self.state.last_error = str(e)
            self.state.status = AgentStatus.IDLE
            
            await self._emit('task_failed', task, e)
            raise
            
        finally:
            self.state.task_history.append(task)
            self.state.current_task = None
            
    async def _run_task(self, task: AgentTask) -> Any:
        raise NotImplementedError("Subclass must implement _run_task")
        
    async def run(self):
        self._running = True
        while self._running:
            try:
                task = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)
                await self.execute_task(task)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Agent error: {e}")
                await asyncio.sleep(1)
                
    async def stop(self):
        self._running = False
        
    async def terminate(self):
        for child in self.children:
            await child.terminate()
        self._running = False
        self.state.status = AgentStatus.TERMINATED
        
    def get_info(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.config.name,
            "status": self.state.status.value,
            "children": [str(c.id) for c in self.children],
            "parent": str(self.parent.id) if self.parent else None,
            "task_count": len(self.state.task_history),
            "current_task": self.state.current_task.id if self.state.current_task else None
        }


class SubAgent(BaseAgent):
    def __init__(self, config: AgentConfig, parent: BaseAgent):
        super().__init__(config, parent)
        
    async def _run_task(self, task: AgentTask) -> Any:
        logger.info(f"SubAgent {self.config.name} executing task: {task.description}")
        
        for step in range(self.config.max_steps):
            task.steps = step + 1
            
            action = await self._think(task)
            if action.get('type') == 'finish':
                return action.get('result')
                
            result = await self._act(action)
            task.result = result
            
            await asyncio.sleep(0.01)
            
        return {"status": "max_steps_reached", "steps": task.steps}
        
    async def _think(self, task: AgentTask) -> Dict[str, Any]:
        return {"type": "finish", "result": f"Task completed: {task.description}"}
        
    async def _act(self, action: Dict[str, Any]) -> Any:
        return action


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[UUID, BaseAgent] = {}
        self._templates: Dict[str, AgentConfig] = {}
        
    def register_template(self, name: str, config: AgentConfig):
        self._templates[name] = config
        logger.info(f"Registered agent template: {name}")
        
    def create_from_template(self, name: str, **overrides) -> Optional[BaseAgent]:
        if name not in self._templates:
            return None
            
        config = self._templates[name].model_copy(update=overrides)
        return SubAgent(config, parent=None)
        
    def register(self, agent: BaseAgent):
        self._agents[agent.id] = agent
        
    def unregister(self, agent_id: UUID) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False
        
    def get(self, agent_id: UUID) -> Optional[BaseAgent]:
        return self._agents.get(agent_id)
        
    def list_agents(self) -> List[Dict[str, Any]]:
        return [a.get_info() for a in self._agents.values()]