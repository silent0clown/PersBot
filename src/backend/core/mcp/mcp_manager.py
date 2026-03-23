import asyncio
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from mcp import StdioServerParameters
import logging

from .mcp_client import MCPClient, MCPTool

logger = logging.getLogger(__name__)


@dataclass
class MCPServerInfo:
    name: str
    enabled: bool
    command: str
    args: List[str]
    env: Dict[str, str]
    url: Optional[str]


class MCPManager:
    def __init__(self, servers: List[MCPServerInfo] = None):
        self._servers: Dict[str, MCPServerInfo] = {}
        self._clients: Dict[str, MCPClient] = {}
        self._initialized = False

        if servers:
            for server in servers:
                self._servers[server.name] = server

    def add_server(self, server: MCPServerInfo):
        self._servers[server.name] = server

    def remove_server(self, name: str):
        if name in self._clients:
            raise RuntimeError(f"Cannot remove server '{name}' while connected. Disconnect first.")
        self._servers.pop(name, None)

    async def initialize(self):
        if self._initialized:
            return

        for name, server in self._servers.items():
            if not server.enabled:
                logger.info(f"Skipping disabled MCP server: {name}")
                continue

            try:
                await self.connect_server(name)
            except Exception as e:
                logger.error(f"Failed to connect MCP server '{name}': {e}")

        self._initialized = True
        logger.info(f"MCP Manager initialized with {len(self._clients)} servers")

    async def shutdown(self):
        for name in list(self._clients.keys()):
            await self.disconnect_server(name)
        self._initialized = False
        logger.info("MCP Manager shutdown")

    async def connect_server(self, name: str):
        if name in self._clients:
            logger.warning(f"MCP server '{name}' already connected")
            return

        server = self._servers.get(name)
        if not server:
            raise ValueError(f"MCP server '{name}' not configured")

        if not server.enabled:
            raise ValueError(f"MCP server '{name}' is disabled")

        env = os.environ.copy()
        env.update(server.env)

        params = StdioServerParameters(
            command=server.command,
            args=server.args,
            env=env,
            url=server.url
        )

        client = MCPClient(name, params)
        await client.connect()
        self._clients[name] = client

        logger.info(f"Connected to MCP server: {name}")

    async def disconnect_server(self, name: str):
        client = self._clients.get(name)
        if not client:
            return

        await client.disconnect()
        self._clients.pop(name)
        logger.info(f"Disconnected from MCP server: {name}")

    async def reconnect_server(self, name: str):
        await self.disconnect_server(name)
        await self.connect_server(name)

    def get_client(self, name: str) -> Optional[MCPClient]:
        return self._clients.get(name)

    def is_connected(self, name: str = None) -> bool:
        if name:
            client = self._clients.get(name)
            return client.is_connected() if client else False
        return len(self._clients) > 0

    def get_all_tools(self) -> Dict[str, Dict[str, MCPTool]]:
        result = {}
        for name, client in self._clients.items():
            result[name] = client.get_tools()
        return result

    def list_tools(self, server_name: str = None) -> List[str]:
        if server_name:
            client = self._clients.get(server_name)
            return client.list_tool_names() if client else []
        
        tools = []
        for client in self._clients.values():
            tools.extend(client.list_tool_names())
        return tools

    def get_tool_schema(self, tool_name: str, server_name: str = None) -> Optional[Dict[str, Any]]:
        if server_name:
            client = self._clients.get(server_name)
            if client:
                tool = client.get_tools().get(tool_name)
                return {
                    "name": f"{server_name}_{tool.name}",
                    "description": tool.description,
                    "input_schema": tool.input_schema
                } if tool else None
            return None

        for name, client in self._clients.items():
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
            if not client:
                raise ValueError(f"MCP server '{server_name}' not connected")
            return await client.call_tool(tool_name, arguments)

        for name, client in self._clients.items():
            tool = client.get_tools().get(tool_name)
            if tool:
                return await client.call_tool(tool_name, arguments)

        raise ValueError(f"Tool '{tool_name}' not found in any connected MCP server")

    def get_servers(self) -> Dict[str, MCPServerInfo]:
        return self._servers.copy()

    def get_connected_servers(self) -> List[str]:
        return list(self._clients.keys())
