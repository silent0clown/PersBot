from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


class ToolErrorCode(str, Enum):
    """工具错误分类码"""
    VALIDATION_ERROR = "validation_error"
    PERMISSION_DENIED = "permission_denied"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT = "timeout"
    LOOP_DETECTED = "loop_detected"
    RESULT_TOO_LARGE = "result_too_large"
    NOT_FOUND = "not_found"


@dataclass
class ToolResult:
    """统一工具执行结果，替代纯字符串返回"""
    content: str = ""
    is_error: bool = False
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_tool_message(self) -> str:
        """转换为注入 LLM 上下文的工具结果文本"""
        if self.is_error:
            return f"[工具错误:{self.error_code}] {self.content}"
        return self.content

    @staticmethod
    def success(content: str, **metadata) -> "ToolResult":
        return ToolResult(content=content, metadata=metadata)

    @staticmethod
    def error(content: str, error_code: ToolErrorCode, error_message: str = None, **metadata) -> "ToolResult":
        return ToolResult(
            content=content,
            is_error=True,
            error_code=error_code.value,
            error_message=error_message,
            metadata=metadata
        )


class ValidationResult:
    """输入验证结果"""
    
    def __init__(self, valid: bool, error: str = ""):
        self.valid = valid
        self.error = error

    @staticmethod
    def ok() -> "ValidationResult":
        return ValidationResult(True)

    @staticmethod
    def fail(error: str) -> "ValidationResult":
        return ValidationResult(False, error)


@dataclass
class ToolDefinition:
    """工具定义 (给 LLM 看的元数据)"""
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    is_read_only: bool = False
    is_concurrency_safe: bool = False
    max_result_size: int = 100_000
    
    def to_schema(self) -> Dict[str, Any]:
        """转换为 LLM 工具调用格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
            }
        }


@dataclass
class ToolCall:
    """工具调用请求"""
    id: str
    name: str
    arguments: Dict[str, Any]
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ToolCall":
        func = data.get("function", {})
        return ToolCall(
            id=data.get("id", ""),
            name=func.get("name", ""),
            arguments=func.get("arguments", {})
        )