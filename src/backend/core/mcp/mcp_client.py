import asyncio
import json
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from contextlib import AsyncExitStack
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPClient:
    def __init__(self, name: str, server_params: StdioServerParameters):
        self.name = name
        self.server_params = server_params
        self._session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self._tools: Dict[str, MCPTool] = {}
        self._connected = False

    async def connect(self):
        if self._connected:
            return

        self._exit_stack = AsyncExitStack()

        if self.server_params.url:
            # 使用 streamable_http_client 连接 HTTP MCP 服务器
            from mcp.client.streamable_http import streamablehttp_client
            client = streamablehttp_client(self.server_params.url)
            read, write = await self._exit_stack.enter_async_context(client)
        else:
            read, write = await self._exit_stack.enter_async_context(
                stdio_client(self.server_params)
            )

        self._session = ClientSession(read, write)
        await self._session.initialize()

        await self._load_tools()
        self._connected = True
        logger.info(f"MCP client '{self.name}' connected")

    async def _load_tools(self):
        if not self._session:
            return

        response = await self._session.list_tools()
        self._tools = {}
        for tool in response.tools:
            self._tools[tool.name] = MCPTool(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema
            )

        logger.info(f"Loaded {len(self._tools)} tools from '{self.name}'")

    async def disconnect(self):
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._session = None
            self._connected = False
            logger.info(f"MCP client '{self.name}' disconnected")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if not self._session or not self._connected:
            raise RuntimeError(f"MCP client '{self.name}' not connected")

        result = await self._session.call_tool(tool_name, arguments)
        return result

    def get_tools(self) -> Dict[str, MCPTool]:
        return self._tools

    def list_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def is_connected(self) -> bool:
        return self._connected
