import re
import logging
import subprocess
import os
from typing import Dict, Any

from .base import BaseTool
from .types import ToolResult, ValidationResult, ToolErrorCode

logger = logging.getLogger(__name__)


class ShellTool(BaseTool):
    """Shell 命令执行工具"""

    # 危险命令模式黑名单
    DANGEROUS_PATTERNS = [
        r">\s*/dev/sd",
        r"\bmkfs\b",
        r"dd\s+.*of=/dev/",
        r":\(\)\{",  # fork bomb
        r"rm\s+-rf\s+/(?:\s|$)",
        r"rm\s+-rf\s+\*",
        r"chmod\s+-R\s+777\s+/",
        r"chown\s+-R",
        r"curl.*\|\s*bash",
        r"wget.*\|\s*sh",
    ]

    # 安全命令白名单 (如果启用白名单模式)
    SAFE_COMMANDS = [
        "ls", "pwd", "cd", "cat", "head", "tail", "grep", "find",
        "date", "whoami", "uname", "df", "du", "echo", "wc",
        "git status", "git log", "git diff", "git branch",
        "python", "pip", "npm", "node",
    ]

    def __init__(self, timeout: int = 30, enable_whitelist: bool = False):
        self.timeout = timeout
        self.enable_whitelist = enable_whitelist

    @property
    def name(self) -> str:
        return "run_command"

    @property
    def description(self) -> str:
        return "在系统终端中执行命令并返回输出。用于运行程序、执行脚本、查询信息等。"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的命令"
                },
                "cwd": {
                    "type": "string",
                    "description": "执行命令的工作目录",
                    "default": None
                },
                "timeout": {
                    "type": "integer",
                    "description": "命令超时时间(秒)",
                    "default": 30
                }
            },
            "required": ["command"]
        }

    @property
    def is_read_only(self) -> bool:
        return False

    @property
    def is_concurrency_safe(self) -> bool:
        return False

    def validate_input(self, **kwargs) -> ValidationResult:
        command = kwargs.get("command", "")
        
        if not command or not command.strip():
            return ValidationResult.fail("command 参数不能为空")

        # 检查危险命令模式
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return ValidationResult.fail(f"检测到危险命令模式: {pattern}")

        # 白名单模式检查
        if self.enable_whitelist:
            cmd_start = command.strip().split()[0] if command.strip() else ""
            if cmd_start not in self.SAFE_COMMANDS:
                # 允许带有安全参数的命令
                allowed = False
                for safe_cmd in self.SAFE_COMMANDS:
                    if command.strip().startswith(safe_cmd):
                        allowed = True
                        break
                if not allowed:
                    return ValidationResult.fail(f"命令不在白名单中: {cmd_start}")

        return ValidationResult.ok()

    def execute(self, **kwargs) -> ToolResult:
        command = kwargs.get("command", "")
        cwd = kwargs.get("cwd", None)
        timeout = kwargs.get("timeout", self.timeout)

        try:
            # 执行命令
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )

            output = result.stdout
            if result.stderr:
                output += f"\n[stderr] {result.stderr}"

            # 限制输出长度
            if len(output.encode("utf-8")) > self.max_result_size:
                output = output[: self.max_result_size] + f"\n... (输出过长，已截断)"

            return ToolResult.success(
                output if output else "(命令执行完成，无输出)",
                return_code=result.returncode,
                command=command
            )

        except subprocess.TimeoutExpired:
            return ToolResult.error(
                f"命令执行超时({timeout}秒)",
                ToolErrorCode.TIMEOUT
            )
        except PermissionError:
            return ToolResult.error(
                "无权限执行此命令",
                ToolErrorCode.EXECUTION_ERROR
            )
        except Exception as e:
            logger.error(f"Shell command error: {e}")
            return ToolResult.error(
                f"命令执行失败: {str(e)}",
                ToolErrorCode.EXECUTION_ERROR
            )


class GetSystemInfoTool(BaseTool):
    """获取系统信息工具"""

    @property
    def name(self) -> str:
        return "get_system_info"

    @property
    def description(self) -> str:
        return "获取系统基本信息，包括操作系统版本、CPU、内存、磁盘等。"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "info_type": {
                    "type": "string",
                    "description": "信息类型: all, os, cpu, memory, disk",
                    "default": "all"
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
        import platform
        import psutil

        info_type = kwargs.get("info_type", "all")

        try:
            result = []

            if info_type in ("all", "os"):
                result.append(f"操作系统: {platform.system()} {platform.release()}")
                result.append(f"版本: {platform.version()}")
                result.append(f"机器: {platform.machine()}")
                result.append(f"处理器: {platform.processor()}")

            if info_type in ("all", "cpu"):
                cpu_count = psutil.cpu_count()
                cpu_percent = psutil.cpu_percent(interval=0.5)
                result.append(f"CPU: {cpu_count} 核, 使用率 {cpu_percent}%")

            if info_type in ("all", "memory"):
                mem = psutil.virtual_memory()
                result.append(f"内存: {mem.total // (1024**3)}GB, 使用 {mem.percent}%")
                swap = psutil.swap_memory()
                result.append(f"Swap: {swap.total // (1024**3)}GB, 使用 {swap.percent}%")

            if info_type in ("all", "disk"):
                for part in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        result.append(f"磁盘 {part.mountpoint}: {usage.total // (1024**3)}GB, 使用 {usage.percent}%")
                    except:
                        pass

            return ToolResult.success("\n".join(result))

        except Exception as e:
            return ToolResult.error(
                f"获取系统信息失败: {str(e)}",
                ToolErrorCode.EXECUTION_ERROR
            )