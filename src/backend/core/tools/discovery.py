"""
工具发现服务 - 搜索和推荐可用的工具
"""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import yaml
import re

from .registry import get_tool_registry

logger = logging.getLogger(__name__)


@dataclass
class MCPServerOption:
    """MCP 服务器选项"""
    name: str
    package: str
    description: str
    install_command: str
    config: Dict[str, Any]
    required_env: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class CatalogTool:
    """目录中的工具定义"""
    name: str
    description: str
    category: str
    keywords: List[str]
    example_queries: List[str]
    mcp_servers: List[MCPServerOption]
    is_installed: bool = False


@dataclass
class ToolSuggestion:
    """工具建议"""
    tool: CatalogTool
    match_score: float  # 匹配分数 0-1
    reason: str  # 匹配原因


class ToolDiscovery:
    """工具发现服务 - 搜索可用工具并提供建议"""

    def __init__(self, catalog_path: str = None):
        self._catalog: Dict[str, CatalogTool] = {}
        self._categories: Dict[str, Dict[str, str]] = {}

        if catalog_path is None:
            catalog_path = Path(__file__).parent / "catalog.yaml"

        self._load_catalog(catalog_path)

    def _load_catalog(self, catalog_path: str):
        """加载工具目录"""
        path = Path(catalog_path)
        if not path.exists():
            logger.warning(f"Catalog file not found: {catalog_path}")
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}

            # 加载分类
            self._categories = data.get('categories', {})

            # 加载工具
            tools_data = data.get('tools', {})
            for tool_id, tool_data in tools_data.items():
                mcp_servers = []
                for server_data in tool_data.get('mcp_servers', []):
                    required_env = []
                    for env in server_data.get('required_env', []):
                        required_env.append({
                            'name': env.get('name', ''),
                            'description': env.get('description', ''),
                            'obtain_url': env.get('obtain_url', ''),
                            'required': env.get('required', True)
                        })

                    mcp_servers.append(MCPServerOption(
                        name=server_data.get('name', ''),
                        package=server_data.get('package', ''),
                        description=server_data.get('description', ''),
                        install_command=server_data.get('install_command', ''),
                        config=server_data.get('config', {}),
                        required_env=required_env
                    ))

                self._catalog[tool_id] = CatalogTool(
                    name=tool_data.get('name', tool_id),
                    description=tool_data.get('description', ''),
                    category=tool_data.get('category', 'other'),
                    keywords=tool_data.get('keywords', []),
                    example_queries=tool_data.get('example_queries', []),
                    mcp_servers=mcp_servers
                )

            logger.info(f"Loaded {len(self._catalog)} tools from catalog")

        except Exception as e:
            logger.error(f"Failed to load catalog: {e}")

    def search_by_intent(self, user_query: str) -> List[ToolSuggestion]:
        """
        根据用户意图搜索相关工具
        
        Args:
            user_query: 用户的原始查询
            
        Returns:
            按匹配度排序的工具建议列表
        """
        suggestions = []
        query_lower = user_query.lower()
        query_words = set(re.findall(r'[\w\u4e00-\u9fff]+', query_lower))

        self._refresh_install_status()

        for tool_id, tool in self._catalog.items():

            # 计算匹配分数
            score, reason = self._calculate_match_score(
                query_lower, query_words, tool
            )

            if score > 0:
                suggestions.append(ToolSuggestion(
                    tool=tool,
                    match_score=score,
                    reason=reason
                ))

        # 按分数排序
        suggestions.sort(key=lambda x: x.match_score, reverse=True)
        return suggestions

    def _calculate_match_score(
            self,
            query: str,
            query_words: set,
            tool: CatalogTool
    ) -> tuple[float, str]:
        """计算匹配分数"""
        score = 0.0
        reasons = []

        # 1. 关键词完全匹配 (高权重)
        for keyword in tool.keywords:
            if keyword in query:
                score += 0.5
                reasons.append(f"关键词匹配: {keyword}")

        # 2. 工具名称匹配
        if tool.name.lower() in query:
            score += 0.4
            reasons.append(f"工具名称匹配: {tool.name}")

        # 3. 描述中的词匹配
        desc_words = set(re.findall(r'[\w\u4e00-\u9fff]+', tool.description.lower()))
        common_words = query_words & desc_words
        if common_words:
            score += 0.1 * len(common_words)
            reasons.append(f"描述匹配: {', '.join(list(common_words)[:3])}")

        # 4. 示例查询相似度
        for example in tool.example_queries:
            example_lower = example.lower()
            if any(word in example_lower for word in query_words):
                score += 0.2
                reasons.append(f"示例查询相似")
                break

        reason = "; ".join(reasons) if reasons else "无匹配"
        return min(score, 1.0), reason

    def _refresh_install_status(self):
        """刷新所有 catalog 工具的安装状态"""
        registry = get_tool_registry()
        # 收集所有已注册工具的 server_name
        installed_servers = set()
        for tool_info in registry.get_all_tools():
            installed_servers.add(tool_info.server_name)

        for tool_id, tool in self._catalog.items():
            tool.is_installed = any(
                server.name in installed_servers
                for server in tool.mcp_servers
            )

    def get_tool_by_id(self, tool_id: str) -> Optional[CatalogTool]:
        """根据 ID 获取工具"""
        return self._catalog.get(tool_id)

    def get_all_tools(self) -> List[CatalogTool]:
        """获取所有目录中的工具（动态刷新 is_installed 状态）"""
        self._refresh_install_status()
        return list(self._catalog.values())

    def get_tools_by_category(self, category: str) -> List[CatalogTool]:
        """根据分类获取工具"""
        return [t for t in self._catalog.values() if t.category == category]

    def get_categories(self) -> Dict[str, Dict[str, str]]:
        """获取所有分类"""
        return self._categories

    def format_suggestion(self, suggestion: ToolSuggestion) -> str:
        """格式化工具建议为用户友好的文本"""
        tool = suggestion.tool

        if tool.is_installed:
            return f"✅ **{tool.name}** - {tool.description}\n   (已安装，可以直接使用)"

        lines = []
        lines.append(f"🔧 **{tool.name}** - {tool.description}")
        lines.append(f"   匹配原因: {suggestion.reason}")
        lines.append("")

        if tool.mcp_servers:
            server = tool.mcp_servers[0]  # 推荐第一个
            lines.append(f"   📦 安装方式:")
            lines.append(f"   ```bash")
            lines.append(f"   {server.install_command}")
            lines.append(f"   ```")

            if server.required_env:
                lines.append(f"")
                lines.append(f"   🔑 需要配置:")
                for env in server.required_env:
                    lines.append(f"   - {env['name']}: {env['description']}")
                    if env.get('obtain_url'):
                        lines.append(f"     获取地址: {env['obtain_url']}")

        return "\n".join(lines)

    def generate_advice(self, user_query: str) -> str:
        """
        生成完整的建议文本
        
        当没有找到合适的工具时，为用户提供如何获得该能力的建议
        """
        suggestions = self.search_by_intent(user_query)

        if not suggestions:
            return self._generate_no_suggestion_advice(user_query)

        # 只取前3个最相关的建议
        top_suggestions = suggestions[:3]

        installed = [s for s in top_suggestions if s.tool.is_installed]
        not_installed = [s for s in top_suggestions if not s.tool.is_installed]

        lines = []

        if installed:
            lines.append("你已有以下相关工具:")
            for s in installed:
                lines.append(f"  • {s.tool.name}: {s.tool.description}")
            lines.append("")

        if not_installed:
            lines.append("要解决这个问题，你可以安装以下工具:")
            lines.append("")
            for s in not_installed:
                lines.append(self.format_suggestion(s))
                lines.append("")

        lines.append("💡 安装后重启 PersBot 即可使用。")

        return "\n".join(lines)

    def _generate_no_suggestion_advice(self, user_query: str) -> str:
        """当没有找到匹配工具时的建议"""
        return f"""抱歉，我暂时没有找到能直接处理这个问题的工具 😅

不过别担心，你可以:

1️⃣ **查看可用工具列表**
   告诉我"你有什么能力"，我可以展示所有可用的工具

2️⃣ **手动添加 MCP 服务器**
   编辑 `mcp_servers.yaml` 文件，添加你需要的服务

3️⃣ **搜索社区工具**
   访问 https://github.com/modelcontextprotocol 查看更多 MCP 服务器

有什么我能帮你的吗？"""


# 全局实例
_discovery: Optional[ToolDiscovery] = None


def get_tool_discovery() -> ToolDiscovery:
    """获取全局工具发现服务实例"""
    global _discovery
    if _discovery is None:
        _discovery = ToolDiscovery()
    return _discovery
