"""
权限管理器 - 管理 Agent 操作权限
"""
import asyncio
import logging
import uuid
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PermissionType(Enum):
    """权限类型"""
    INSTALL_MCP = "install_mcp"           # 安装 MCP 服务器
    EXECUTE_COMMAND = "execute_command"    # 执行系统命令
    ACCESS_FILE = "access_file"            # 访问文件
    NETWORK_REQUEST = "network_request"    # 网络请求
    SEND_MESSAGE = "send_message"          # 发送消息


class PermissionLevel(Enum):
    """权限级别"""
    DENIED = "denied"         # 拒绝
    ASK = "ask"              # 每次询问
    ALLOWED = "allowed"       # 允许
    TRUSTED = "trusted"       # 信任（不再询问）


@dataclass
class PermissionRequest:
    """权限请求"""
    id: str
    permission_type: PermissionType
    description: str
    details: Dict[str, Any]
    requester: str  # 请求来源
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    response: Optional[bool] = None
    responded_at: Optional[datetime] = None


@dataclass
class PermissionRule:
    """权限规则"""
    permission_type: PermissionType
    level: PermissionLevel
    pattern: Optional[str] = None  # 匹配模式（如特定命令）


class PermissionManager:
    """权限管理器"""

    def __init__(self, default_level: PermissionLevel = PermissionLevel.ASK):
        self._default_level = default_level
        self._rules: Dict[PermissionType, PermissionRule] = {}
        self._pending_requests: Dict[str, PermissionRequest] = {}
        self._response_callbacks: Dict[str, asyncio.Event] = {}
        self._message_sender: Optional[Callable] = None
        self._timeout_seconds = 60  # 默认超时时间

        # 初始化默认规则
        self._init_default_rules()

    def _init_default_rules(self):
        """初始化默认规则"""
        # 默认所有敏感操作都需要询问
        for ptype in PermissionType:
            self._rules[ptype] = PermissionRule(
                permission_type=ptype,
                level=self._default_level
            )

    def set_message_sender(self, sender: Callable):
        """设置消息发送器（用于发送确认请求）"""
        self._message_sender = sender

    def set_timeout(self, seconds: int):
        """设置超时时间"""
        self._timeout_seconds = seconds

    def set_permission_level(self, permission_type: PermissionType, level: PermissionLevel):
        """设置权限级别"""
        self._rules[permission_type] = PermissionRule(
            permission_type=permission_type,
            level=level
        )
        logger.info(f"Set {permission_type.value} permission to {level.value}")

    def get_permission_level(self, permission_type: PermissionType) -> PermissionLevel:
        """获取权限级别"""
        rule = self._rules.get(permission_type)
        return rule.level if rule else self._default_level

    async def request_permission(
            self,
            permission_type: PermissionType,
            description: str,
            details: Dict[str, Any] = None,
            requester: str = "agent"
    ) -> bool:
        """
        请求权限
        
        Args:
            permission_type: 权限类型
            description: 操作描述
            details: 详细信息
            requester: 请求来源
            
        Returns:
            bool: 是否获得权限
        """
        level = self.get_permission_level(permission_type)

        # 如果是信任级别，直接允许
        if level == PermissionLevel.TRUSTED:
            logger.info(f"Permission auto-granted (trusted): {permission_type.value}")
            return True

        # 如果是拒绝级别，直接拒绝
        if level == PermissionLevel.DENIED:
            logger.info(f"Permission denied: {permission_type.value}")
            return False

        # 需要询问用户
        return await self._ask_user_permission(
            permission_type, description, details or {}, requester
        )

    async def _ask_user_permission(
            self,
            permission_type: PermissionType,
            description: str,
            details: Dict[str, Any],
            requester: str
    ) -> bool:
        """向用户请求权限"""
        # 创建请求
        request_id = str(uuid.uuid4())[:8]
        request = PermissionRequest(
            id=request_id,
            permission_type=permission_type,
            description=description,
            details=details,
            requester=requester,
            expires_at=datetime.now() + timedelta(seconds=self._timeout_seconds)
        )

        self._pending_requests[request_id] = request
        self._response_callbacks[request_id] = asyncio.Event()

        # 发送确认消息
        if self._message_sender:
            message = self._format_permission_request(request)
            await self._message_sender(message)

        # 等待响应
        try:
            await asyncio.wait_for(
                self._response_callbacks[request_id].wait(),
                timeout=self._timeout_seconds
            )
            return request.response or False
        except asyncio.TimeoutError:
            logger.warning(f"Permission request {request_id} timed out")
            return False
        finally:
            # 清理
            self._pending_requests.pop(request_id, None)
            self._response_callbacks.pop(request_id, None)

    def _format_permission_request(self, request: PermissionRequest) -> Dict[str, Any]:
        """格式化权限请求消息"""
        type_names = {
            PermissionType.INSTALL_MCP: "🔧 安装 MCP 工具",
            PermissionType.EXECUTE_COMMAND: "⚡ 执行命令",
            PermissionType.ACCESS_FILE: "📁 访问文件",
            PermissionType.NETWORK_REQUEST: "🌐 网络请求",
            PermissionType.SEND_MESSAGE: "💬 发送消息"
        }

        type_name = type_names.get(request.permission_type, request.permission_type.value)

        details_text = ""
        if request.details:
            details_lines = []
            for key, value in request.details.items():
                details_lines.append(f"  • {key}: {value}")
            details_text = "\n".join(details_lines)

        return {
            "type": "permission_request",
            "request_id": request.id,
            "permission_type": request.permission_type.value,
            "title": f"🔐 需要你的授权",
            "message": f"""我想执行以下操作，需要你的许可：

📌 **{type_name}**
📝 {request.description}
{f"📋 详情:\n{details_text}" if details_text else ""}

请回复:
• **确认** 或 **允许** - 批准本次操作
• **拒绝** 或 **取消** - 拒绝本次操作
• **始终允许** - 以后不再询问（仅限本次会话）""",
            "timeout": self._timeout_seconds,
            "options": ["确认", "拒绝", "始终允许"]
        }

    def handle_response(self, request_id: str, approved: bool, remember: bool = False):
        """处理用户响应"""
        request = self._pending_requests.get(request_id)
        if not request:
            logger.warning(f"Unknown permission request: {request_id}")
            return

        request.response = approved
        request.responded_at = datetime.now()

        # 如果用户选择"始终允许"
        if remember and approved:
            self.set_permission_level(
                request.permission_type,
                PermissionLevel.TRUSTED
            )

        # 通知等待的协程
        event = self._response_callbacks.get(request_id)
        if event:
            event.set()

        logger.info(f"Permission {request_id}: {'approved' if approved else 'denied'}")

    def parse_user_response(self, message: str, request_id: str = None) -> Optional[bool]:
        """
        解析用户响应
        
        Returns:
            True: 允许
            False: 拒绝
            None: 无法解析
        """
        message_lower = message.lower().strip()

        # 确认关键词
        confirm_keywords = ["确认", "允许", "是", "yes", "ok", "好的", "同意", "approve"]
        deny_keywords = ["拒绝", "取消", "否", "no", "不行", "不同意", "deny", "cancel"]
        always_keywords = ["始终允许", "总是允许", "一直允许", "trust", "always"]

        if any(kw in message_lower for kw in confirm_keywords):
            return True
        elif any(kw in message_lower for kw in deny_keywords):
            return False
        elif any(kw in message_lower for kw in always_keywords):
            # 检查是否有待处理的请求
            if request_id:
                self.handle_response(request_id, True, remember=True)
            return True

        return None

    def get_pending_requests(self) -> Dict[str, PermissionRequest]:
        """获取待处理的请求"""
        return self._pending_requests.copy()

    def has_pending_request(self) -> bool:
        """是否有待处理的请求"""
        return len(self._pending_requests) > 0


# 全局实例
_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """获取全局权限管理器实例"""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager


def set_permission_manager(manager: PermissionManager):
    """设置全局权限管理器实例"""
    global _permission_manager
    _permission_manager = manager
