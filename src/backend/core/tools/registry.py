"""
工具注册表 - 管理已安装和可用的工具
"""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    description: str
    server_name: str
    parameters: List[ToolParameter] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)

    def to_openai_format(self) -> Dict[str, Any]:
        """转换为 OpenAI function calling 格式"""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": f"{self.server_name}_{self.name}",
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


@dataclass
class InstalledTool:
    """已安装的工具"""
    tool_info: ToolInfo
    enabled: bool = True


class ToolRegistry:
    """工具注册表 - 管理已安装的工具"""

    def __init__(self, mcp_manager=None):
        self._tools: Dict[str, InstalledTool] = {}
        self._mcp_manager = mcp_manager

    def set_mcp_manager(self, mcp_manager):
        """设置 MCP 管理器"""
        self._mcp_manager = mcp_manager

    async def sync_from_mcp(self):
        """从 MCP 管理器同步已连接的工具"""
        if not self._mcp_manager:
            logger.warning("MCP manager not set, skipping sync")
            return

        self._tools.clear()

        for server_name, client in self._mcp_manager._clients.items():
            if not client.is_connected():
                continue

            tools = client.get_tools()
            for tool_name, mcp_tool in tools.items():
                # 解析参数
                parameters = []
                input_schema = mcp_tool.input_schema or {}

                if "properties" in input_schema:
                    required_fields = input_schema.get("required", [])
                    for param_name, param_info in input_schema["properties"].items():
                        parameters.append(ToolParameter(
                            name=param_name,
                            type=param_info.get("type", "string"),
                            description=param_info.get("description", ""),
                            required=param_name in required_fields
                        ))

                tool_info = ToolInfo(
                    name=tool_name,
                    description=mcp_tool.description or "",
                    server_name=server_name,
                    parameters=parameters,
                    input_schema=input_schema
                )

                tool_key = f"{server_name}_{tool_name}"
                self._tools[tool_key] = InstalledTool(tool_info=tool_info)

        logger.info(f"Synced {len(self._tools)} tools from MCP")

    def get_all_tools(self) -> List[ToolInfo]:
        """获取所有已注册的工具"""
        return [t.tool_info for t in self._tools.values() if t.enabled]

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """获取 OpenAI 格式的工具列表"""
        return [t.tool_info.to_openai_format() for t in self._tools.values() if t.enabled]

    def get_tool(self, tool_key: str) -> Optional[ToolInfo]:
        """获取指定工具"""
        installed = self._tools.get(tool_key)
        return installed.tool_info if installed and installed.enabled else None

    def has_tool(self, tool_key: str) -> bool:
        """检查工具是否存在且启用"""
        installed = self._tools.get(tool_key)
        return installed is not None and installed.enabled

    def list_tool_names(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())

    def find_tools_by_keyword(self, keyword: str) -> List[ToolInfo]:
        """根据关键词查找工具"""
        keyword_lower = keyword.lower()
        results = []

        for installed in self._tools.values():
            if not installed.enabled:
                continue

            tool = installed.tool_info
            if (keyword_lower in tool.name.lower() or
                    keyword_lower in tool.description.lower()):
                results.append(tool)

        return results

    async def call_tool(self, tool_key: str, arguments: Dict[str, Any]) -> Any:
        """调用工具"""
        if not self._mcp_manager:
            raise RuntimeError("MCP manager not set")

        installed = self._tools.get(tool_key)
        if not installed:
            raise ValueError(f"Tool '{tool_key}' not found")

        if not installed.enabled:
            raise ValueError(f"Tool '{tool_key}' is disabled")

        tool = installed.tool_info
        return await self._mcp_manager.call_tool(tool.name, arguments, tool.server_name)

    def parse_tool_key(self, tool_key: str) -> tuple[str, str]:
        """解析工具键为 (server_name, tool_name)"""
        parts = tool_key.split("_", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return tool_key, tool_key


# 全局实例
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表实例"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
