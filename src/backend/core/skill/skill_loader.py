import asyncio
from typing import Optional, Dict, Any, List, Callable, Union
from pydantic import BaseModel, Field
from enum import Enum
import json
import importlib.util
import importlib
import sys
import re
from pathlib import Path
import logging
import yaml

logger = logging.getLogger(__name__)


class SkillStatus(str, Enum):
    UNLOADED = "unloaded"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"


class SkillCommand(BaseModel):
    description: str
    usage: str
    params: Dict[str, Any] = Field(default_factory=dict)


class SkillModel(BaseModel):
    name: str
    description: str
    version: str = "1.0.0"
    author: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    main: str = "main.py"
    commands: Dict[str, SkillCommand] = Field(default_factory=dict)
    exclude_patterns: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    readme: Optional[str] = None


def parse_skill_md(skill_dir: Path, name: str) -> Optional[SkillModel]:
    skill_path = skill_dir / name
    md_file = skill_path / "SKILL.md"
    
    if not md_file.exists():
        return None
    
    try:
        content = md_file.read_text(encoding='utf-8')
        
        frontmatter_pattern = r'^---\s*\n(.*?)\n---'
        match = re.match(frontmatter_pattern, content, re.DOTALL)
        
        if not match:
            logger.warning(f"SKILL.md in '{name}' has no valid frontmatter")
            return None
        
        frontmatter_yaml = match.group(1)
        data = yaml.safe_load(frontmatter_yaml)
        
        if not data:
            return None
        
        readme_match = re.match(r'^---\s*\n.*?\n---\s*\n(.*)', content, re.DOTALL)
        readme_content = readme_match.group(1).strip() if readme_match else None
        
        model = SkillModel(
            name=data.get('name', name),
            description=data.get('description', ''),
            version=data.get('version', '1.0.0'),
            author=data.get('author'),
            keywords=data.get('keywords', []),
            main=data.get('main', 'main.py'),
            commands={},
            exclude_patterns=data.get('exclude_patterns', []),
            dependencies=data.get('dependencies', []),
            metadata=data.get('metadata', {}),
            readme=readme_content
        )
        
        commands_data = data.get('commands', {})
        for cmd_name, cmd_data in commands_data.items():
            model.commands[cmd_name] = SkillCommand(
                description=cmd_data.get('description', ''),
                usage=cmd_data.get('usage', f'persbot skill {name} {cmd_name}'),
                params=cmd_data.get('params', {})
            )
        
        logger.info(f"Parsed SKILL.md for skill: {name}")
        return model
        
    except yaml.YAMLError as e:
        logger.error(f"YAML parse error in SKILL.md for '{name}': {e}")
    except Exception as e:
        logger.error(f"Error parsing SKILL.md for '{name}': {e}")
    
    return None


class SkillInstance:
    def __init__(self, model: SkillModel, module: Any, path: Path):
        self.model = model
        self.module = module
        self.path = path
        self.status = SkillStatus.LOADED
        self._handlers: Dict[str, Callable] = {}
        
    def register_handler(self, command: str, handler: Callable):
        self._handlers[command] = handler
        
    async def execute(self, command: str, params: Dict[str, Any] = None) -> Any:
        if command not in self._handlers:
            raise ValueError(f"Command '{command}' not found in skill '{self.model.name}'")
        
        handler = self._handlers[command]
        if asyncio.iscoroutinefunction(handler):
            return await handler(params or {})
        return handler(params or {})
    
    def has_command(self, command: str) -> bool:
        return command in self._handlers


class SkillLoader:
    def __init__(self, skill_dir: str = "skill"):
        self.skill_dir = Path(skill_dir)
        self._skills: Dict[str, SkillInstance] = {}
        self._loaders: Dict[str, Callable] = {}
        
    def register_loader(self, extension: str, loader: Callable):
        self._loaders[extension] = loader
        
    async def load_skill(self, name: str) -> SkillInstance:
        skill_path = self.skill_dir / name
        
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill '{name}' not found at {skill_path}")
        
        model = parse_skill_md(self.skill_dir, name)
        
        if model is None:
            json_file = skill_path / f"{name}_skill.json"
            if not json_file.exists():
                json_file = skill_path / "skill.json"
            
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    model = SkillModel(**json.load(f))
            else:
                raise FileNotFoundError(f"No SKILL.md or skill.json found for '{name}'")
        
        main_file = skill_path / model.main
        if not main_file.exists():
            raise FileNotFoundError(f"Main file '{model.main}' not found")
        
        spec = importlib.util.spec_from_file_location(f"skill_{name}", main_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"skill_{name}"] = module
        spec.loader.exec_module(module)
        
        instance = SkillInstance(model, module, skill_path)
        
        if hasattr(module, 'register'):
            await module.register(instance)
            
        self._skills[name] = instance
        logger.info(f"Loaded skill: {name}")
        return instance
    
    async def unload_skill(self, name: str) -> bool:
        if name not in self._skills:
            return False
            
        skill = self._skills[name]
        if hasattr(skill.module, 'unload'):
            await skill.module.unload(skill)
            
        del self._skills[name]
        logger.info(f"Unloaded skill: {name}")
        return True
    
    async def reload_skill(self, name: str) -> SkillInstance:
        await self.unload_skill(name)
        return await self.load_skill(name)
    
    def get_skill(self, name: str) -> Optional[SkillInstance]:
        return self._skills.get(name)
    
    def list_skills(self) -> List[SkillModel]:
        return [s.model for s in self._skills.values()]
    
    async def discover_skills(self) -> List[str]:
        discovered = []
        for item in self.skill_dir.iterdir():
            if item.is_dir():
                discovered.append(item.name)
        return discovered
    
    def get_command_suggestions(self) -> Dict[str, List[str]]:
        suggestions = {}
        for name, skill in self._skills.items():
            suggestions[name] = list(skill.model.commands.keys())
        return suggestions