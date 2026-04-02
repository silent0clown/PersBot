import time
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class CallRecord:
    tool_name: str
    timestamp: float
    arguments: str


class LoopDetector:
    """工具循环调用检测器"""

    def __init__(self, max_calls: int = 5, time_window: float = 60.0):
        self.max_calls = max_calls
        self.time_window = time_window
        self._calls: Dict[str, list] = {}

    def check(self, tool_name: str, arguments: Dict = None) -> bool:
        """检查是否触发循环"""
        self._cleanup()

        args_str = str(arguments) if arguments else ""
        current_time = time.time()

        if tool_name not in self._calls:
            self._calls[tool_name] = []

        recent_calls = self._calls[tool_name]
        recent_calls.append(CallRecord(tool_name, current_time, args_str))

        if len(recent_calls) > self.max_calls:
            return False

        return True

    def _cleanup(self):
        """清理超时的调用记录"""
        current_time = time.time()
        for tool_name in list(self._calls.keys()):
            self._calls[tool_name] = [
                c for c in self._calls[tool_name]
                if current_time - c.timestamp < self.time_window
            ]
            if not self._calls[tool_name]:
                del self._calls[tool_name]

    def reset(self, tool_name: str = None):
        """重置记录"""
        if tool_name:
            self._calls.pop(tool_name, None)
        else:
            self._calls.clear()
