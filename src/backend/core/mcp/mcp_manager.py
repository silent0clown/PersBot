import asyncio
import os
import math
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from mcp import StdioServerParameters
import logging

from .mcp_client import MCPClient, MCPTool, ConnectionState

logger = logging.getLogger(__name__)

# 重连参数 (借鉴 Claude Code 指数退避策略)
MAX_RECONNECT_ATTEMPTS = 5
INITIAL_BACKOFF_MS = 1000
MAX_BACKOFF_MS = 30000


@dataclass
class MCPServerInfo:
    name: str
    enabled: bool
    command: str
    args: List[str]
    env: Dict[str, str] = field(default_factory=dict)
    url: Optional[str] = None


class MCPManager:
    def __init__(self, servers: List[MCPServerInfo] = None):
        self._servers: Dict[str, MCPServerInfo] = {}
        self._clients: Dict[str, MCPClient] = {}
        self._initialized = False
        self._connect_task: Optional[asyncio.Task] = None

        if servers:
            for server in servers:
                self._servers[server.name] = server

    def add_server(self, server: MCPServerInfo):
        self._servers[server.name] = server

    def remove_server(self, name: str):
        if name in self._clients and self._clients[name].is_connected():
            raise RuntimeError(f"Cannot remove server '{name}' while connected. Disconnect first.")
        self._servers.pop(name, None)

    async def initialize(self):
        """非阻塞初始化：后台并发连接所有启用的 MCP 服务器"""
        if self._initialized:
            return

        self._initialized = True
        enabled = [n for n, s in self._servers.items() if s.enabled]

        if not enabled:
            logger.info("No enabled MCP servers")
            return

        self._connect_task = asyncio.create_task(self._connect_all(enabled))
        logger.info(f"MCP Manager: connecting {len(enabled)} server(s) in background")

    async def _connect_all(self, server_names: List[str]):
        """后台并发连接"""
        tasks = [self._safe_connect(name) for name in server_names]
        await asyncio.gather(*tasks)

        connected = [n for n, c in self._clients.items() if c.is_connected()]
        failed = [n for n in server_names if n not in connected]
        logger.info(
            f"MCP init done: {len(connected)} connected"
            + (f", {len(failed)} failed ({', '.join(failed)})" if failed else "")
        )

    async def _safe_connect(self, name: str):
        """带超时的安全连接"""
        try:
            await self.connect_server(name)
        except Exception as e:
            logger.error(f"[{name}] Failed to connect: {e}")

    async def shutdown(self):
        if self._connect_task and not self._connect_task.done():
            self._connect_task.cancel()
        for name in list(self._clients.keys()):
            await self.disconnect_server(name)
        self._initialized = False
        logger.info("MCP Manager shutdown")

    async def connect_server(self, name: str):
        server = self._servers.get(name)
        if not server:
            raise ValueError(f"MCP server '{name}' not configured")
        if not server.enabled:
            raise ValueError(f"MCP server '{name}' is disabled")

        # 如果已存在，先断开
        if name in self._clients:
            await self.disconnect_server(name)

        env = os.environ.copy()
        env.update(server.env)

        params = StdioServerParameters(
            command=server.command,
            args=server.args,
            env=env
        )

        client = MCPClient(name, params)
        self._clients[name] = client
        await client.connect()

    async def disconnect_server(self, name: str):
        client = self._clients.pop(name, None)
        if client:
            await client.disconnect()

    async def reconnect_server(self, name: str):
        """重连服务器（带指数退避）"""
        server = self._servers.get(name)
        if not server or not server.enabled:
            logger.warning(f"[{name}] Server disabled, skipping reconnect")
            return

        for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
            backoff = min(INITIAL_BACKOFF_MS * (2 ** (attempt - 1)), MAX_BACKOFF_MS) / 1000
            logger.info(f"[{name}] Reconnect attempt {attempt}/{MAX_RECONNECT_ATTEMPTS} (backoff {backoff:.1f}s)")

            try:
                await self.connect_server(name)
                if self._clients.get(name, None) and self._clients[name].is_connected():
                    logger.info(f"[{name}] Reconnected on attempt {attempt}")
                    return
            except Exception as e:
                logger.warning(f"[{name}] Reconnect attempt {attempt} failed: {e}")

            if attempt < MAX_RECONNECT_ATTEMPTS:
                await asyncio.sleep(backoff)

        logger.error(f"[{name}] Reconnect failed after {MAX_RECONNECT_ATTEMPTS} attempts")

    def get_client(self, name: str) -> Optional[MCPClient]:
        return self._clients.get(name)

    def is_connected(self, name: str = None) -> bool:
        if name:
            client = self._clients.get(name)
            return client.is_connected() if client else False
        return any(c.is_connected() for c in self._clients.values())

    def get_all_tools(self) -> Dict[str, Dict[str, MCPTool]]:
        return {
            name: client.get_tools()
            for name, client in self._clients.items()
            if client.is_connected()
        }

    def list_tools(self, server_name: str = None) -> List[str]:
        if server_name:
            client = self._clients.get(server_name)
            return client.list_tool_names() if client and client.is_connected() else []
        tools = []
        for client in self._clients.values():
            if client.is_connected():
                tools.extend(client.list_tool_names())
        return tools

    def get_tool_schema(self, tool_name: str, server_name: str = None) -> Optional[Dict[str, Any]]:
        if server_name:
            client = self._clients.get(server_name)
            if client and client.is_connected():
                tool = client.get_tools().get(tool_name)
                if tool:
                    return {
                        "name": f"{server_name}_{tool.name}",
                        "description": tool.description,
                        "input_schema": tool.input_schema
                    }
            return None

        for name, client in self._clients.items():
            if not client.is_connected():
                continue
            tool = client.get_tools().get(tool_name)
            if tool:
                return {
                    "name": f"{name}_{tool.name}",
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                    "server": name
                }
        return None

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], server_name: str = None) -> Any:
        if server_name:
            client = self._clients.get(server_name)
            if not client or not client.is_connected():
                raise ValueError(f"MCP server '{server_name}' not connected")
            return await client.call_tool(tool_name, arguments)

        for name, client in self._clients.items():
            if not client.is_connected():
                continue
            tool = client.get_tools().get(tool_name)
            if tool:
                return await client.call_tool(tool_name, arguments)

        raise ValueError(f"Tool '{tool_name}' not found in any connected MCP server")

    def get_servers(self) -> Dict[str, MCPServerInfo]:
        return self._servers.copy()

    def get_connected_servers(self) -> List[str]:
        return [n for n, c in self._clients.items() if c.is_connected()]

    def get_server_statuses(self) -> List[Dict[str, Any]]:
        """返回所有服务器状态（供 health check 使用）"""
        statuses = []
        for name, server in self._servers.items():
            client = self._clients.get(name)
            statuses.append({
                "name": name,
                "enabled": server.enabled,
                "state": client.state.value if client else ("disabled" if not server.enabled else "not_started"),
                "tools": client.list_tool_names() if client and client.is_connected() else [],
                "error": client.error_message if client else None
            })
        return statuses
