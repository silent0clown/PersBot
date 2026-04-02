import logging
from pathlib import Path
from typing import Optional, Dict, Any

import yaml

from .types import Persona, Personality

logger = logging.getLogger(__name__)

PERSONA_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "persona.yaml"


class PersonaManager:
    """人格管理器"""

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path = config_path or PERSONA_CONFIG_PATH
        self._persona: Optional[Persona] = None
        self._load()

    def _load(self):
        """加载人格配置"""
        try:
            if self._config_path.exists():
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                self._persona = Persona.from_dict(data)
                logger.info(f"Persona loaded: {self._persona.name}")
            else:
                self._persona = Persona()
                logger.warning(f"Persona config not found, using defaults")
        except Exception as e:
            logger.error(f"Failed to load persona: {e}")
            self._persona = Persona()

    def get_persona(self) -> Persona:
        """获取当前人格"""
        return self._persona

    def get_name(self) -> str:
        """获取宠物名称"""
        return self._persona.name if self._persona else "小P"

    def get_user_title(self) -> str:
        """获取对用户的称呼"""
        return self._persona.user_title if self._persona else "主人"

    def adjust_personality(self, feedback_type: str, trait: str, delta: float):
        """
        微调性格参数。

        触发场景:
        - 用户说"你太啰嗦了" → adjust("negative", "verbosity", -0.1)
        - 用户说"哈哈太好笑了" → adjust("positive", "humor", +0.05)
        - 用户说"叫我名字就好" → 修改 user_title
        """
        if not self._persona:
            return

        delta = max(-0.1, min(0.1, delta))
        current = getattr(self._persona.personality, trait, None)
        if current is not None:
            new_value = max(0.1, min(0.9, current + delta))
            setattr(self._persona.personality, trait, new_value)
            logger.info(f"Personality adjusted: {trait} = {new_value}")
            self._save()

    def set_user_title(self, title: str):
        """修改用户称呼"""
        if self._persona:
            self._persona.user_title = title
            self._save()

    def _save(self):
        """保存人格配置"""
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.dump(self._persona.to_dict(), f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            logger.error(f"Failed to save persona: {e}")

    def reload(self):
        """重新加载配置"""
        self._load()


_manager: Optional[PersonaManager] = None


def get_persona_manager() -> PersonaManager:
    """获取全局人格管理器"""
    global _manager
    if _manager is None:
        _manager = PersonaManager()
    return _manager
