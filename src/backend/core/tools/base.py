from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .types import ToolResult, ValidationResult, ToolDefinition


class BaseTool(ABC):
    """所有工具的基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述 (给LLM看, 用于判断何时调用)"""

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """参数的JSON Schema定义"""

    @property
    def is_read_only(self) -> bool:
        """是否为只读操作。只读工具可并行执行"""
        return False

    @property
    def is_concurrency_safe(self) -> bool:
        """是否可与其他工具并发执行"""
        return False

    @property
    def max_result_size(self) -> int:
        """结果最大字节数，超出则写入磁盘返回摘要"""
        return 100_000

    def validate_input(self, **kwargs) -> ValidationResult:
        """校验输入参数的合法性 (类型、范围、格式)。
        默认实现: 无校验，子类按需覆盖。
        在 check_permissions 之前调用。"""
        return ValidationResult.ok()

    def get_definition(self) -> ToolDefinition:
        """获取工具定义"""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters_schema=self.parameters_schema,
            is_read_only=self.is_read_only,
            is_concurrency_safe=self.is_concurrency_safe,
            max_result_size=self.max_result_size
        )

    def to_schema(self) -> Dict[str, Any]:
        """转换为LLM工具调用格式 (兼容旧接口)"""
        return self.get_definition().to_schema()

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """执行工具, 返回 ToolResult"""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"