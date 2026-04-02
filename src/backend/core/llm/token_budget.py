import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class TokenBudgetConfig:
    """Token 预算配置"""
    simple: int = 500
    medium: int = 2000
    complex: int = 4000
    tool_intensive: int = 6000

    @property
    def default(self) -> int:
        return self.medium


class TokenBudgetManager:
    """Token 预算管理器"""

    def __init__(self, config: Optional[TokenBudgetConfig] = None):
        self.config = config or TokenBudgetConfig()
        self.current_budget: int = self.config.default
        self.total_used: int = 0

    def assess_task_type(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """评估任务类型"""
        last_msg = messages[-1].get("content", "") if messages else ""

        # 工具密集: 连续调用超过3次工具
        if tools and len(tools) > 3:
            return "tool_intensive"

        # 复杂: 有工具调用
        if tools:
            return "complex"

        # 中等: 消息长度 >= 50 字
        if len(last_msg) >= 50:
            return "medium"

        # 简单: 其他
        return "simple"

    def get_budget_for_task(self, task_type: str) -> int:
        """获取任务对应的预算"""
        budget_map = {
            "simple": self.config.simple,
            "medium": self.config.medium,
            "complex": self.config.complex,
            "tool_intensive": self.config.tool_intensive,
        }
        return budget_map.get(task_type, self.config.default)

    def check_within_budget(self, estimated_tokens: int) -> bool:
        """检查是否在预算内"""
        return (self.total_used + estimated_tokens) <= self.current_budget

    def consume(self, tokens: int):
        """消耗 token"""
        self.total_used += tokens

    def reset(self):
        """重置预算（新会话）"""
        self.total_used = 0
        self.current_budget = self.config.default

    def set_budget(self, budget: int):
        """手动设置预算（用于特定任务）"""
        self.current_budget = budget