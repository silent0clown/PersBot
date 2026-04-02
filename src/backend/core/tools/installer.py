"""
MCP 服务器安装服务
"""
import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .discovery import get_tool_discovery, MCPServerOption

logger = logging.getLogger(__name__)


@dataclass
class InstallResult:
    """安装结果"""
    success: bool
    message: str
    server_name: str
    config: Optional[Dict[str, Any]] = None


class MCPInstaller:
    """MCP 服务器安装器"""

    def __init__(self, project_root: str = None):
        if project_root is None:
            project_root = str(Path(__file__).parent.parent.parent)

        self.project_root = Path(project_root)
        self.mcp_servers_dir = self.project_root / "mcp-servers"
        self.package_json_path = self.project_root / "package.json"
        self.mcp_config_path = self.project_root / "config" / "mcp_servers.yaml"

    async def install_server(self, tool_id: str) -> InstallResult:
        """
        安装 MCP 服务器

        Args:
            tool_id: 工具 ID（如 "weather"）

        Returns:
            InstallResult: 安装结果
        """
        discovery = get_tool_discovery()

        tool = discovery.get_tool_by_id(tool_id)
        if not tool:
            return InstallResult(
                success=False,
                message=f"未找到工具: {tool_id}",
                server_name=tool_id
            )

        if tool.is_installed:
            return InstallResult(
                success=True,
                message=f"工具 {tool.name} 已安装",
                server_name=tool_id
            )

        if not tool.mcp_servers:
            return InstallResult(
                success=False,
                message=f"工具 {tool.name} 没有可用的 MCP 服务器",
                server_name=tool_id
            )

        server = tool.mcp_servers[0]
        return await self._execute_install(tool_id, server)

    async def _execute_install(
            self,
            tool_id: str,
            server: MCPServerOption
    ) -> InstallResult:
        """执行安装命令"""
        try:
            await self._ensure_package_json()

            logger.info(f"Installing MCP server: {server.package}")

            if server.package and server.package != "custom":
                cmd = ["npm", "install", server.package]
            else:
                cmd = server.install_command.split()

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                return InstallResult(
                    success=False,
                    message=f"安装失败: {error_msg}",
                    server_name=tool_id
                )

            config = await self._update_mcp_config(tool_id, server)

            logger.info(f"Successfully installed MCP server: {server.package}")

            return InstallResult(
                success=True,
                message=f"成功安装 {server.name}",
                server_name=tool_id,
                config=config
            )

        except Exception as e:
            logger.error(f"Failed to install MCP server: {e}")
            return InstallResult(
                success=False,
                message=f"安装出错: {str(e)}",
                server_name=tool_id
            )

    async def _ensure_package_json(self):
        """确保 package.json 存在"""
        if not self.package_json_path.exists():
            package_data = {
                "name": "persbot-mcp-servers",
                "version": "1.0.0",
                "description": "PersBot MCP Server Dependencies",
                "private": True,
                "dependencies": {}
            }

            with open(self.package_json_path, 'w', encoding='utf-8') as f:
                json.dump(package_data, f, indent=2)

            logger.info("Created package.json")

    async def _update_mcp_config(
            self,
            tool_id: str,
            server: MCPServerOption
    ) -> Dict[str, Any]:
        """更新 mcp_servers.yaml 配置"""
        import yaml

        config = {}

        if self.mcp_config_path.exists():
            with open(self.mcp_config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}

        if 'servers' not in config:
            config['servers'] = {}

        server_config = server.config.copy()

        if server.package and server.package != "custom":
            server_config['command'] = 'npx'
            server_config['args'] = ['-y', server.package]

        config['servers'][tool_id] = {
            'name': server.name,
            **server_config,
            'enabled': True
        }

        with open(self.mcp_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

        logger.info(f"Updated mcp_servers.yaml with {tool_id}")

        return config['servers'][tool_id]

    async def check_requirements(self, tool_id: str) -> Dict[str, Any]:
        """
        检查安装所需的环境变量是否已配置
        """
        discovery = get_tool_discovery()
        tool = discovery.get_tool_by_id(tool_id)

        if not tool or not tool.mcp_servers:
            return {"valid": False, "message": "工具不存在"}

        server = tool.mcp_servers[0]
        missing_env = []

        for env in server.required_env:
            if env.get('required', True):
                env_name = env['name']
                if not os.environ.get(env_name):
                    missing_env.append({
                        'name': env_name,
                        'description': env.get('description', ''),
                        'obtain_url': env.get('obtain_url', '')
                    })

        return {
            "valid": len(missing_env) == 0,
            "missing_env": missing_env,
            "message": "所有环境变量已配置" if not missing_env else f"缺少 {len(missing_env)} 个环境变量"
        }

    def list_installed_servers(self) -> List[str]:
        """列出已安装的 MCP 服务器"""
        import yaml

        if not self.mcp_config_path.exists():
            return []

        try:
            with open(self.mcp_config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}

            servers = config.get('servers', {})
            return [
                name for name, cfg in servers.items()
                if cfg.get('enabled', True)
            ]
        except Exception as e:
            logger.error(f"Failed to read mcp_servers.yaml: {e}")
            return []


# 全局实例
_installer: Optional[MCPInstaller] = None


def get_mcp_installer() -> MCPInstaller:
    global _installer
    if _installer is None:
        _installer = MCPInstaller()
    return _installer
