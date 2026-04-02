import os
import logging
import subprocess
from typing import Dict, Any

from .base import BaseTool
from .types import ToolResult, ValidationResult, ToolErrorCode

logger = logging.getLogger(__name__)


class ReadFileTool(BaseTool):
    """读取文件工具"""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "读取指定路径的文件内容。适用于查看代码、配置文件、文本文件等。"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要读取的文件路径"
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码，默认 utf-8",
                    "default": "utf-8"
                },
                "max_lines": {
                    "type": "integer",
                    "description": "最大读取行数，默认读取全部",
                    "default": -1
                }
            },
            "required": ["path"]
        }

    @property
    def is_read_only(self) -> bool:
        return True

    @property
    def is_concurrency_safe(self) -> bool:
        return True

    def validate_input(self, **kwargs) -> ValidationResult:
        path = kwargs.get("path", "")
        if not path:
            return ValidationResult.fail("path 参数不能为空")
        return ValidationResult.ok()

    def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", "")
        encoding = kwargs.get("encoding", "utf-8")
        max_lines = kwargs.get("max_lines", -1)

        try:
            # 安全检查：展开路径
            expanded_path = os.path.expanduser(path)
            
            # 检查文件是否存在
            if not os.path.exists(expanded_path):
                return ToolResult.error(
                    f"文件不存在: {path}",
                    ToolErrorCode.EXECUTION_ERROR
                )
            
            # 检查是否为文件
            if not os.path.isfile(expanded_path):
                return ToolResult.error(
                    f"路径不是文件: {path}",
                    ToolErrorCode.EXECUTION_ERROR
                )

            # 读取文件
            with open(expanded_path, "r", encoding=encoding) as f:
                if max_lines > 0:
                    lines = [f.readline() for _ in range(max_lines)]
                    content = "".join(lines)
                else:
                    content = f.read()

            # 检查结果大小
            if len(content.encode("utf-8")) > self.max_result_size:
                content = content[: self.max_result_size] + f"\n... (内容过长，已截断)"

            return ToolResult.success(
                content,
                path=expanded_path,
                size=len(content)
            )

        except UnicodeDecodeError:
            return ToolResult.error(
                f"文件编码错误，请尝试其他编码",
                ToolErrorCode.EXECUTION_ERROR
            )
        except PermissionError:
            return ToolResult.error(
                f"无权限读取: {path}",
                ToolErrorCode.EXECUTION_ERROR
            )
        except Exception as e:
            logger.error(f"Read file error: {e}")
            return ToolResult.error(
                f"读取文件失败: {str(e)}",
                ToolErrorCode.EXECUTION_ERROR
            )


class WriteFileTool(BaseTool):
    """写入文件工具"""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "将内容写入指定路径的文件。如果文件不存在则创建，如果已存在则覆盖。"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要写入的文件路径"
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容"
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码，默认 utf-8",
                    "default": "utf-8"
                },
                "append": {
                    "type": "boolean",
                    "description": "是否追加模式，默认 false (覆盖)",
                    "default": False
                }
            },
            "required": ["path", "content"]
        }

    def validate_input(self, **kwargs) -> ValidationResult:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        
        if not path:
            return ValidationResult.fail("path 参数不能为空")
        if content is None:
            return ValidationResult.fail("content 参数不能为空")
        
        # 检查写入敏感路径
        sensitive = [".ssh", ".gnupg", ".aws", "credentials", ".env"]
        expanded_path = os.path.expanduser(path)
        if any(s in expanded_path for s in sensitive):
            return ValidationResult.fail("禁止写入敏感路径")
        
        return ValidationResult.ok()

    def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        encoding = kwargs.get("encoding", "utf-8")
        append = kwargs.get("append", False)

        try:
            expanded_path = os.path.expanduser(path)
            
            # 确保目录存在
            dir_path = os.path.dirname(expanded_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            # 写入文件
            mode = "a" if append else "w"
            with open(expanded_path, mode, encoding=encoding) as f:
                f.write(content)

            return ToolResult.success(
                f"成功写入文件: {path} ({len(content)} 字符)",
                path=expanded_path,
                size=len(content)
            )

        except PermissionError:
            return ToolResult.error(
                f"无权限写入: {path}",
                ToolErrorCode.EXECUTION_ERROR
            )
        except Exception as e:
            logger.error(f"Write file error: {e}")
            return ToolResult.error(
                f"写入文件失败: {str(e)}",
                ToolErrorCode.EXECUTION_ERROR
            )


class ListDirectoryTool(BaseTool):
    """列出目录工具"""

    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "列出指定目录下的文件和文件夹。可以查看目录结构。"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要列出的目录路径",
                    "default": "."
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "是否显示隐藏文件",
                    "default": False
                }
            },
            "required": []
        }

    @property
    def is_read_only(self) -> bool:
        return True

    @property
    def is_concurrency_safe(self) -> bool:
        return True

    def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", ".")
        show_hidden = kwargs.get("show_hidden", False)

        try:
            expanded_path = os.path.expanduser(path)
            
            if not os.path.exists(expanded_path):
                return ToolResult.error(
                    f"目录不存在: {path}",
                    ToolErrorCode.EXECUTION_ERROR
                )
            
            if not os.path.isdir(expanded_path):
                return ToolResult.error(
                    f"路径不是目录: {path}",
                    ToolErrorCode.EXECUTION_ERROR
                )

            entries = os.listdir(expanded_path)
            
            if not show_hidden:
                entries = [e for e in entries if not e.startswith(".")]
            
            # 分类
            dirs = []
            files = []
            for entry in sorted(entries):
                full_path = os.path.join(expanded_path, entry)
                if os.path.isdir(full_path):
                    dirs.append(entry + "/")
                else:
                    files.append(entry)

            result = "📁 目录: " + expanded_path + "\n\n"
            if dirs:
                result += "文件夹:\n" + "\n".join(f"  📁 {d}") + "\n\n"
            if files:
                result += "文件:\n" + "\n".join(f"  📄 {f}") + "\n\n"
            
            if not dirs and not files:
                result = "目录为空"

            return ToolResult.success(result, path=expanded_path)

        except PermissionError:
            return ToolResult.error(
                f"无权限访问: {path}",
                ToolErrorCode.EXECUTION_ERROR
            )
        except Exception as e:
            logger.error(f"List directory error: {e}")
            return ToolResult.error(
                f"列出目录失败: {str(e)}",
                ToolErrorCode.EXECUTION_ERROR
            )