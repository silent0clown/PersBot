from typing import Optional, Dict, Any, List, Callable
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


class TeamRole(str, Enum):
    LEADER = "leader"
    WORKER = "worker"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"


class TeamStatus(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class CollaborationMode(str, Enum):
    LEADER_FOLLOWER = "leader_follower"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    SWARM = "swarm"


class TeamMember(BaseModel):
    agent_id: UUID
    role: TeamRole = TeamRole.WORKER
    capabilities: List[str] = Field(default_factory=list)
    status: str = "active"
    assigned_tasks: List[UUID] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TeamTask(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    description: str
    required_roles: List[TeamRole] = Field(default_factory=list)
    required_capabilities: List[str] = Field(default_factory=list)
    assigned_to: Optional[UUID] = None
    status: str = "pending"
    result: Optional[Any] = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class TeamMessage(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    from_agent: UUID
    to_agent: Optional[UUID] = None
    team_id: UUID
    content: str
    message_type: str = "info"
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TeamConfig(BaseModel):
    name: str
    description: str = ""
    collaboration_mode: CollaborationMode = CollaborationMode.LEADER_FOLLOWER
    max_concurrent_tasks: int = 5
    task_timeout: int = 300
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentTeam:
    def __init__(self, config: TeamConfig):
        self.id = uuid4()
        self.config = config
        self.members: Dict[UUID, TeamMember] = {}
        self.tasks: Dict[UUID, TeamTask] = {}
        self.messages: List[TeamMessage] = []
        self.status = TeamStatus.IDLE
        self._message_handlers: List[Callable] = []
        self._task_queue: asyncio.Queue = asyncio.Queue()
        
    def add_member(self, agent_id: UUID, role: TeamRole = TeamRole.WORKER, capabilities: List[str] = None) -> TeamMember:
        member = TeamMember(
            agent_id=agent_id,
            role=role,
            capabilities=capabilities or []
        )
        self.members[agent_id] = member
        logger.info(f"Added member {agent_id} to team {self.config.name}")
        return member
        
    def remove_member(self, agent_id: UUID) -> bool:
        if agent_id in self.members:
            del self.members[agent_id]
            return True
        return False
        
    def get_member(self, agent_id: UUID) -> Optional[TeamMember]:
        return self.members.get(agent_id)
        
    def get_leader(self) -> Optional[TeamMember]:
        for member in self.members.values():
            if member.role == TeamRole.LEADER:
                return member
        return None
        
    def get_available_members(self, capabilities: List[str] = None) -> List[TeamMember]:
        available = []
        for member in self.members.values():
            if member.status != "active":
                continue
            if capabilities:
                if any(c in member.capabilities for c in capabilities):
                    available.append(member)
            else:
                available.append(member)
        return available
        
    async def assign_task(self, task: TeamTask) -> bool:
        available = self.get_available_members(task.required_capabilities)
        
        if not available:
            logger.warning(f"No available members for task {task.id}")
            return False
            
        if self.config.collaboration_mode == CollaborationMode.LEADER_FOLLOWER:
            member = available[0]
        elif self.config.collaboration_mode == CollaborationMode.PARALLEL:
            for m in available[:self.config.max_concurrent_tasks]:
                task_copy = TeamTask(
                    description=task.description,
                    required_roles=task.required_roles,
                    required_capabilities=task.required_capabilities,
                    assigned_to=m.agent_id
                )
                self.tasks[task_copy.id] = task_copy
                m.assigned_tasks.append(task_copy.id)
            return True
        else:
            member = available[0]
            
        task.assigned_to = member.agent_id
        member.assigned_tasks.append(task.id)
        self.tasks[task.id] = task
        self.status = TeamStatus.ACTIVE
        
        logger.info(f"Assigned task {task.id} to member {member.agent_id}")
        return True
        
    async def complete_task(self, task_id: UUID, result: Any) -> bool:
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        task.status = "completed"
        task.result = result
        task.completed_at = datetime.now()
        
        if task.assigned_to and task.assigned_to in self.members:
            member = self.members[task.assigned_to]
            if task.id in member.assigned_tasks:
                member.assigned_tasks.remove(task.id)
                
        active_tasks = [t for t in self.tasks.values() if t.status == "pending"]
        if not active_tasks:
            self.status = TeamStatus.COMPLETED
            
        return True
        
    async def send_message(self, from_agent: UUID, content: str, to_agent: UUID = None, msg_type: str = "info"):
        msg = TeamMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            team_id=self.id,
            content=content,
            message_type=msg_type
        )
        self.messages.append(msg)
        
        for handler in self._message_handlers:
            await handler(msg)
            
    def register_message_handler(self, handler: Callable):
        self._message_handlers.append(handler)
        
    def get_info(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.config.name,
            "status": self.status.value,
            "mode": self.config.collaboration_mode.value,
            "member_count": len(self.members),
            "task_count": len(self.tasks),
            "message_count": len(self.messages),
            "members": [
                {
                    "agent_id": str(m.agent_id),
                    "role": m.role.value,
                    "status": m.status,
                    "capabilities": m.capabilities
                }
                for m in self.members.values()
            ]
        }


class TeamManager:
    def __init__(self):
        self._teams: Dict[UUID, AgentTeam] = {}
        self._team_by_agent: Dict[UUID, UUID] = {}
        
    def create_team(self, config: TeamConfig) -> AgentTeam:
        team = AgentTeam(config)
        self._teams[team.id] = team
        logger.info(f"Created team: {config.name}")
        return team
        
    def get_team(self, team_id: UUID) -> Optional[AgentTeam]:
        return self._teams.get(team_id)
        
    def delete_team(self, team_id: UUID) -> bool:
        if team_id in self._teams:
            del self._teams[team_id]
            return True
        return False
        
    def list_teams(self) -> List[Dict[str, Any]]:
        return [t.get_info() for t in self._teams.values()]
        
    def get_team_by_agent(self, agent_id: UUID) -> Optional[AgentTeam]:
        team_id = self._team_by_agent.get(agent_id)
        if team_id:
            return self._teams.get(team_id)
        return None
        
    async def add_agent_to_team(self, team_id: UUID, agent_id: UUID, role: TeamRole = TeamRole.WORKER, capabilities: List[str] = None) -> bool:
        team = self._teams.get(team_id)
        if not team:
            return False
            
        team.add_member(agent_id, role, capabilities)
        self._team_by_agent[agent_id] = team_id
        return True
        
    async def remove_agent_from_team(self, team_id: UUID, agent_id: UUID) -> bool:
        team = self._teams.get(team_id)
        if not team:
            return False
            
        if team.remove_member(agent_id):
            if agent_id in self._team_by_agent:
                del self._team_by_agent[agent_id]
            return True
        return False