from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


class PermissionLevel(Enum):
    """权限级别"""
    GREEN = "green"    # 安全, 静默放行
    YELLOW = "yellow"  # 敏感, 需确认
    RED = "red"        # 危险, 需双重确认
    BLACK = "black"    # 禁止, 永久拦截


class PermissionMode(Enum):
    """权限模式"""
    DEFAULT = "default"   # 正常权限流程
    PLAN = "plan"         # 只读模式，写入自动拒绝
    BYPASS = "bypass"     # 跳过确认，自动放行 (黑色仍拦截)


@dataclass
class PermissionRequest:
    """权限请求对象"""
    tool_name: str
    action: str
    target: str
    level: PermissionLevel
    detail: str
    created_at: datetime = field(default_factory=datetime.now)
    timeout_seconds: int = 120
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def is_expired(self) -> bool:
        """检查请求是否已超时"""
        return (datetime.now() - self.created_at).total_seconds() > self.timeout_seconds
    
    def to_user_message(self) -> str:
        """生成展示给用户的确认消息"""
        level_desc = {
            PermissionLevel.YELLOW: "需要确认",
            PermissionLevel.RED: "危险操作，需要二次确认"
        }
        return f"{level_desc.get(self.level, '')}\n\n操作: {self.action}\n目标: {self.target}\n\n{self.detail}"


@dataclass
class AutoApprovedRule:
    """用户"记住"的自动授权规则"""
    pattern: str  # 匹配模式 (路径/命令前缀)
    level: PermissionLevel
    created_at: datetime = field(default_factory=datetime.now)
    
    def matches(self, target: str) -> bool:
        """检查目标是否匹配此规则"""
        return target.startswith(self.pattern) or self.pattern in target


class PermissionResult:
    """权限检查结果"""
    
    def __init__(
        self,
        allowed: bool,
        level: PermissionLevel,
        need_confirmation: bool = False,
        need_double_confirm: bool = False,
        message: str = ""
    ):
        self.allowed = allowed
        self.level = level
        self.need_confirmation = need_confirmation
        self.need_double_confirm = need_double_confirm
        self.message = message
    
    @staticmethod
    def allow(level: PermissionLevel = PermissionLevel.GREEN) -> "PermissionResult":
        return PermissionResult(
            allowed=True,
            level=level,
            message="允许执行"
        )
    
    @staticmethod
    def confirm(level: PermissionLevel = PermissionLevel.YELLOW) -> "PermissionResult":
        return PermissionResult(
            allowed=False,  # 暂时不允许，需要用户确认
            level=level,
            need_confirmation=True,
            message=f"需要用户确认 ({level.value} 级别)"
        )
    
    @staticmethod
    def double_confirm(level: PermissionLevel = PermissionLevel.RED) -> "PermissionResult":
        return PermissionResult(
            allowed=False,
            level=level,
            need_confirmation=True,
            need_double_confirm=True,
            message=f"危险操作，需要二次确认 ({level.value} 级别)"
        )
    
    @staticmethod
    def deny(message: str = "操作被拒绝") -> "PermissionResult":
        return PermissionResult(
            allowed=False,
            level=PermissionLevel.BLACK,
            message=message
        )