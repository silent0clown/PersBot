import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """MCP 连接状态机 (借鉴 Claude Code)"""
    PENDING = "pending"
    CONNECTED = "connected"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPClient:
    CONNECT_TIMEOUT = 30  # 秒
    TOOL_CALL_TIMEOUT = 120  # 秒

    def __init__(self, name: str, server_params: StdioServerParameters):
        self.name = name
        self.server_params = server_params
        self.state = ConnectionState.PENDING
        self.error_message: Optional[str] = None
        self._session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self._tools: Dict[str, MCPTool] = {}

    async def connect(self):
        if self.state == ConnectionState.CONNECTED:
            return

        self.state = ConnectionState.PENDING
        self.error_message = None

        try:
            logger.info(f"[{self.name}] Connecting...")
            self._exit_stack = AsyncExitStack()

            url = getattr(self.server_params, 'url', None)
            if url:
                logger.info(f"[{self.name}] Using HTTP transport")
                from mcp.client.streamable_http import streamablehttp_client
                client = streamablehttp_client(url)
                read, write = await self._exit_stack.enter_async_context(client)
            else:
                logger.info(f"[{self.name}] Using stdio transport")
                read, write = await self._exit_stack.enter_async_context(
                    stdio_client(self.server_params)
                )

            session = ClientSession(read, write)
            self._session = await self._exit_stack.enter_async_context(session)
            await asyncio.wait_for(
                self._session.initialize(),
                timeout=self.CONNECT_TIMEOUT
            )

            await self._load_tools()
            self.state = ConnectionState.CONNECTED
            logger.info(f"[{self.name}] Connected, {len(self._tools)} tools available")

        except asyncio.TimeoutError:
            self.state = ConnectionState.FAILED
            self.error_message = f"Connection timed out ({self.CONNECT_TIMEOUT}s)"
            logger.error(f"[{self.name}] {self.error_message}")
            await self._cleanup()
            raise
        except Exception as e:
            self.state = ConnectionState.FAILED
            self.error_message = str(e)
            logger.error(f"[{self.name}] Connection failed: {e}")
            await self._cleanup()
            raise

    async def _load_tools(self):
        if not self._session:
            return
        response = await self._session.list_tools()
        self._tools = {
            tool.name: MCPTool(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema
            )
            for tool in response.tools
        }

    async def disconnect(self):
        self._session = None
        old_state = self.state
        self.state = ConnectionState.DISABLED
        await self._cleanup()
        if old_state == ConnectionState.CONNECTED:
            logger.info(f"[{self.name}] Disconnected")

    async def _cleanup(self):
        """安全清理资源"""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception as e:
                logger.debug(f"[{self.name}] Cleanup error (ignored): {e}")
            self._exit_stack = None

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if self.state != ConnectionState.CONNECTED or not self._session:
            raise RuntimeError(f"MCP server '{self.name}' not connected (state: {self.state})")

        try:
            return await asyncio.wait_for(
                self._session.call_tool(tool_name, arguments),
                timeout=self.TOOL_CALL_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise RuntimeError(f"Tool call '{tool_name}' timed out ({self.TOOL_CALL_TIMEOUT}s)")

    def get_tools(self) -> Dict[str, MCPTool]:
        return self._tools

    def list_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def is_connected(self) -> bool:
        return self.state == ConnectionState.CONNECTED

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "tools": len(self._tools),
            "error": self.error_message
        }
