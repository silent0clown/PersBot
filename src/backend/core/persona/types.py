from dataclasses import dataclass, field
from typing import Dict, List, Any
from datetime import datetime


@dataclass
class Personality:
    """性格参数"""
    warmth: float = 0.8
    humor: float = 0.6
    verbosity: float = 0.5
    formality: float = 0.3
    curiosity: float = 0.7
    empathy: float = 0.8

    def to_dict(self) -> Dict[str, float]:
        return {
            "warmth": self.warmth,
            "humor": self.humor,
            "verbosity": self.verbosity,
            "formality": self.formality,
            "curiosity": self.curiosity,
            "empathy": self.empathy
        }

    @staticmethod
    def from_dict(data: Dict[str, float]) -> "Personality":
        return Personality(
            warmth=data.get("warmth", 0.8),
            humor=data.get("humor", 0.6),
            verbosity=data.get("verbosity", 0.5),
            formality=data.get("formality", 0.3),
            curiosity=data.get("curiosity", 0.7),
            empathy=data.get("empathy", 0.8)
        )


@dataclass
class Persona:
    """完整的人格配置"""
    name: str = "小P"
    species: str = "数字精灵"
    birthday: str = ""
    user_title: str = "主人"
    personality: Personality = field(default_factory=Personality)
    speech_patterns: List[str] = field(default_factory=lambda: ["~", "呢", "嘛"])
    interests: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "species": self.species,
            "birthday": self.birthday,
            "user_title": self.user_title,
            "personality": self.personality.to_dict(),
            "speech_patterns": self.speech_patterns,
            "interests": self.interests
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Persona":
        p = data.get("personality", {})
        return Persona(
            name=data.get("name", "小P"),
            species=data.get("species", "数字精灵"),
            birthday=data.get("birthday", ""),
            user_title=data.get("user_title", "主人"),
            personality=Personality.from_dict(p) if isinstance(p, dict) else Personality(),
            speech_patterns=data.get("speech_patterns", ["~", "呢", "嘛"]),
            interests=data.get("interests", [])
        )
