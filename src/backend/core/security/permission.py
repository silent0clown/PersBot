import os
import re
import logging
import fnmatch
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from .types import (
    PermissionLevel,
    PermissionMode,
    PermissionRequest,
    PermissionResult,
    AutoApprovedRule
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent


@dataclass
class PermissionConfig:
    """权限配置"""
    safe_paths_read: List[str] = field(default_factory=list)
    safe_paths_write: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    command_whitelist: List[str] = field(default_factory=list)
    command_blacklist_patterns: List[str] = field(default_factory=list)
    auto_approved_rules: List[Dict] = field(default_factory=list)
    timeout_seconds: int = 120
    auto_approve_timeout: int = 300
    
    @classmethod
    def load(cls, config_path: str = None) -> "PermissionConfig":
        """从 YAML 文件加载配置"""
        import yaml
        
        if config_path is None:
            config_path = BASE_DIR / "config" / "permissions.yaml"
        
        if not Path(config_path).exists():
            logger.warning(f"Permission config not found: {config_path}, using defaults")
            return cls()
        
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        safe_paths = data.get("safe_paths", {})
        blocked = data.get("blocked_paths", [])
        perm_cfg = data.get("permission", {})
        
        return cls(
            safe_paths_read=safe_paths.get("read", []),
            safe_paths_write=safe_paths.get("write", []),
            blocked_paths=blocked,
            command_whitelist=data.get("command_whitelist", []),
            command_blacklist_patterns=data.get("command_blacklist_patterns", []),
            auto_approved_rules=data.get("auto_approved_rules", []),
            timeout_seconds=perm_cfg.get("timeout_seconds", 120),
            auto_approve_timeout=perm_cfg.get("auto_approve_timeout", 300)
        )


class PermissionManager:
    """权限管理器"""
    
    def __init__(self, config_path: str = None):
        self.config = PermissionConfig.load(config_path)
        self.mode = PermissionMode.DEFAULT
        self.auto_rules: List[AutoApprovedRule] = []
        
        # 加载已保存的自动授权规则
        for rule_data in self.config.auto_approved_rules:
            if isinstance(rule_data, dict):
                self.auto_rules.append(AutoApprovedRule(
                    pattern=rule_data.get("pattern", ""),
                    level=PermissionLevel.YELLOW  # 只有黄色权限可以"记住"
                ))
        
        logger.info(f"PermissionManager initialized, mode={self.mode.value}")
    
    def set_mode(self, mode: PermissionMode):
        """切换权限模式"""
        self.mode = mode
        logger.info(f"Permission mode changed to: {mode.value}")
    
    def check(self, tool_name: str, action: str, target: str) -> PermissionResult:
        """
        检查操作权限，返回 PermissionResult
        
        流程:
        1. 黑名单检查 (任何模式都拦截黑色)
        2. plan 模式: 所有非绿色操作拒绝
        3. bypass 模式: 非黑色操作自动放行
        4. default 模式: 正常分级处理
        """
        # 1. 黑名单检查 - 永久拦截
        if self._is_blocked(tool_name, target):
            logger.warning(f"Blocked by blacklist: {tool_name} {target}")
            return PermissionResult.deny("此操作被永久禁止")
        
        # 获取基础权限级别
        level = self._assess_level(tool_name, action, target)
        
        # 2. 检查自动授权规则 (用户"记住"的规则)
        if self._is_auto_approved(target):
            logger.info(f"Auto-approved by rule: {target}")
            return PermissionResult.allow(PermissionLevel.GREEN)
        
        # 3. 根据模式处理
        if self.mode == PermissionMode.PLAN:
            # Plan 模式: 只读模式，非绿色操作全部拒绝
            if level == PermissionLevel.GREEN:
                return PermissionResult.allow(level)
            else:
                logger.info(f"Plan mode: denied {level} operation")
                return PermissionResult.deny("Plan 模式下只允许读取操作")
        
        elif self.mode == PermissionMode.BYPASS:
            # Bypass 模式: 跳过确认，但黑色仍拦截
            if level == PermissionLevel.BLACK:
                return PermissionResult.deny("Bypass 模式下仍禁止此操作")
            logger.info(f"Bypass mode: allowed {level} operation")
            return PermissionResult.allow(level)
        
        else:
            # Default 模式: 正常分级处理
            if level == PermissionLevel.GREEN:
                return PermissionResult.allow(level)
            elif level == PermissionLevel.YELLOW:
                return PermissionResult.confirm(level)
            elif level == PermissionLevel.RED:
                return PermissionResult.double_confirm(level)
            else:
                return PermissionResult.deny("此操作被禁止")
    
    def check_and_create_request(
        self,
        tool_name: str,
        action: str,
        target: str
    ) -> tuple[PermissionResult, Optional[PermissionRequest]]:
        """检查权限并创建请求对象（如果需要确认）"""
        result = self.check(tool_name, action, target)
        
        if result.need_confirmation:
            request = PermissionRequest(
                tool_name=tool_name,
                action=action,
                target=target,
                level=result.level,
                detail=result.message,
                timeout_seconds=self.config.timeout_seconds
            )
            return result, request
        
        return result, None
    
    def add_auto_rule(self, pattern: str):
        """添加自动授权规则 (仅黄色权限可"记住")"""
        rule = AutoApprovedRule(pattern=pattern, level=PermissionLevel.YELLOW)
        self.auto_rules.append(rule)
        logger.info(f"Added auto-approved rule: {pattern}")
    
    def remove_auto_rule(self, pattern: str):
        """移除自动授权规则"""
        self.auto_rules = [r for r in self.auto_rules if r.pattern != pattern]
        logger.info(f"Removed auto-approved rule: {pattern}")
    
    def _is_blocked(self, tool_name: str, target: str) -> bool:
        """检查是否在黑名单中"""
        # 检查命令黑名单
        for pattern in self.config.command_blacklist_patterns:
            if tool_name == "run_command" and re.search(pattern, target, re.IGNORECASE):
                return True
        
        # 检查路径黑名单
        target_expanded = os.path.expanduser(target)
        for blocked in self.config.blocked_paths:
            blocked_expanded = os.path.expanduser(blocked)
            if fnmatch.fnmatch(target_expanded, blocked_expanded) or blocked in target_expanded:
                return True
        
        return False
    
    def _assess_level(
        self,
        tool_name: str,
        action: str,
        target: str
    ) -> PermissionLevel:
        """评估操作的危险级别"""
        action_lower = action.lower()
        
        # 1. 检查命令白名单 (绿色)
        if tool_name == "run_command":
            for cmd in self.config.command_whitelist:
                if target.strip().startswith(cmd.strip()) or cmd in target:
                    return PermissionLevel.GREEN
        
        # 2. 检查安全路径
        target_expanded = os.path.expanduser(target)
        
        # 检查写入操作的安全路径 (支持中英文关键词)
        write_keywords = ["write", "create", "edit", "delete", "写入", "创建", "编辑", "删除"]
        if any(word in action_lower for word in write_keywords):
            for safe_path in self.config.safe_paths_write:
                safe_expanded = os.path.expanduser(safe_path)
                if target_expanded.startswith(safe_expanded):
                    return PermissionLevel.YELLOW  # 编辑操作至少是黄色
            
            # 检查敏感路径 (红色)
            sensitive_patterns = ["~/.ssh", "~/.gnupg", "~/.aws", "credentials", ".env"]
            if any(p in target_expanded for p in sensitive_patterns):
                return PermissionLevel.RED
        
        # 3. 检查读取操作的安全路径 (支持中英文关键词)
        read_keywords = ["read", "list", "view", "读取", "列出", "查看", "浏览"]
        if any(word in action_lower for word in read_keywords):
            for safe_path in self.config.safe_paths_read:
                safe_expanded = os.path.expanduser(safe_path)
                if target_expanded.startswith(safe_expanded):
                    return PermissionLevel.GREEN
        
        # 4. 默认级别: 黄色 (需要确认)
        return PermissionLevel.YELLOW
    
    def _is_auto_approved(self, target: str) -> bool:
        """检查是否匹配用户已授权的"记住"规则"""
        for rule in self.auto_rules:
            if rule.matches(target):
                return True
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取权限系统状态"""
        return {
            "mode": self.mode.value,
            "auto_rules_count": len(self.auto_rules),
            "auto_rules": [r.pattern for r in self.auto_rules]
        }