import asyncio
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
import logging

from .skill_loader import SkillLoader, SkillInstance, SkillModel, SkillStatus

logger = logging.getLogger(__name__)


class SkillManager:
    def __init__(self, skill_dir: str = "skill"):
        self._loader = SkillLoader(skill_dir)
        self._skill_dir = Path(skill_dir)
        self._hooks: Dict[str, List[Callable]] = {
            'on_load': [],
            'on_unload': [],
            'on_execute': [],
            'on_error': []
        }
        self._initialized = False
        
    async def initialize(self):
        if self._initialized:
            return
            
        discovered = await self._loader.discover_skills()
        for name in discovered:
            try:
                await self._loader.load_skill(name)
            except Exception as e:
                logger.error(f"Failed to load skill '{name}': {e}")
                
        self._initialized = True
        logger.info(f"SkillManager initialized with {len(discovered)} skills")
        
    async def shutdown(self):
        for name in list(self._loader._skills.keys()):
            await self._loader.unload_skill(name)
        logger.info("SkillManager shutdown")
        
    def register_hook(self, event: str, callback: Callable):
        if event in self._hooks:
            self._hooks[event].append(callback)
            
    async def _trigger_hook(self, event: str, *args, **kwargs):
        for callback in self._hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Hook error: {e}")
                
    async def load_skill(self, name: str) -> SkillInstance:
        await self._trigger_hook('on_load', name)
        return await self._loader.load_skill(name)
    
    async def unload_skill(self, name: str) -> bool:
        result = await self._loader.unload_skill(name)
        if result:
            await self._trigger_hook('on_unload', name)
        return result
    
    async def reload_skill(self, name: str) -> SkillInstance:
        await self._trigger_hook('on_unload', name)
        instance = await self._loader.reload_skill(name)
        await self._trigger_hook('on_load', name)
        return instance
    
    async def execute_skill(self, skill_name: str, command: str, params: Dict[str, Any] = None) -> Any:
        skill = self._loader.get_skill(skill_name)
        if not skill:
            raise ValueError(f"Skill '{skill_name}' not loaded")
            
        try:
            result = await skill.execute(command, params)
            await self._trigger_hook('on_execute', skill_name, command, result)
            return result
        except Exception as e:
            await self._trigger_hook('on_error', skill_name, command, e)
            raise
            
    def get_skill(self, name: str) -> Optional[SkillInstance]:
        return self._loader.get_skill(name)
    
    def list_skills(self) -> List[SkillModel]:
        return self._loader.list_skills()
    
    def get_skill_status(self) -> Dict[str, str]:
        result = {}
        for name, skill in self._loader._skills.items():
            result[name] = skill.status.value
        return result
    
    def get_commands(self) -> Dict[str, Dict[str, str]]:
        result = {}
        for name, skill in self._loader._skills.items():
            result[name] = {
                cmd: cmd_model.description 
                for cmd, cmd_model in skill.model.commands.items()
            }
        return result
    
    async def get_available_commands(self, query: str = None) -> List[Dict[str, str]]:
        commands = []
        for name, skill in self._loader._skills.items():
            for cmd in skill.model.commands.keys():
                if query is None or query.lower() in cmd.lower():
                    commands.append({
                        'skill': name,
                        'command': cmd,
                        'description': skill.model.commands[cmd].description
                    })
        return commands
    
    def has_command(self, skill_name: str, command: str) -> bool:
        skill = self._loader.get_skill(skill_name)
        if not skill:
            return False
        return skill.has_command(command)
    
    async def install_skill(self, source: str) -> str:
        logger.info(f"Installing skill from: {source}")
        # Placeholder for remote skill installation
        # Could support git clone, pip install, etc.
        return "not implemented"
    
    async def uninstall_skill(self, name: str) -> bool:
        return await self.unload_skill(name)