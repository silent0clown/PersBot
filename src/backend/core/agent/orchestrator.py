"""
Agent 协调器 - ReAct 风格的智能 Agent

核心流程:
1. 用户消息 → LLM (带工具列表)
2. LLM 决定: 调用工具 / 直接回答
3. 如果调用工具 → 执行 → 结果喂回 LLM → 继续
4. 如果工具不存在 → 搜索目录 → 引导安装
5. 安装流程: 检查依赖 → 收集 API Key → 安装 → 热连接 → 重试
"""
import json
import logging
import os
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from ..llm.llm_client import LLMClient, ToolCall, AgentTurn
from ..tools.registry import get_tool_registry, ToolInfo
from ..tools.discovery import get_tool_discovery
from .conversation import (
    get_conversation_manager,
    ConversationManager,
    ConversationSession,
    SessionState,
    PendingInstall
)
from ..config import persona_manager

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Agent 响应"""
    content: str
    tool_calls: List[Dict[str, Any]] = None
    tool_results: List[Dict[str, Any]] = None
    pending_install: Optional[str] = None


class AgentOrchestrator:
    """
    ReAct 风格的 Agent 协调器
    """

    def __init__(self, llm_client: LLMClient, mcp_manager=None):
        self.llm_client = llm_client
        self.mcp_manager = mcp_manager

        self.registry = get_tool_registry()
        self.discovery = get_tool_discovery()
        self.conversation = get_conversation_manager()
        self._installer = None
        self._tools_synced = False

        if mcp_manager:
            self.registry.set_mcp_manager(mcp_manager)

    @property
    def installer(self):
        if self._installer is None:
            from ..tools.installer import get_mcp_installer
            self._installer = get_mcp_installer()
        return self._installer

    async def initialize(self):
        """初始化协调器"""
        await self.registry.sync_from_mcp()
        self._tools_synced = True
        logger.info(f"AgentOrchestrator initialized with {len(self.registry.get_all_tools())} tools")

    async def process(self, user_message: str, session_id: str = "default") -> AgentResponse:
        """
        处理用户消息（主入口）

        Args:
            user_message: 用户输入
            session_id: 会话 ID（web 用 default，飞书用 user_id）

        Returns:
            AgentResponse: 处理结果
        """
        logger.info(f"Processing message [{session_id}]: {user_message[:80]}...")

        # 惰性同步：如果 MCP 已连接但工具尚未同步，立即同步
        if not self._tools_synced and self.mcp_manager:
            await self.registry.sync_from_mcp()
            self._tools_synced = True
            logger.info(f"Lazy-synced {len(self.registry.get_all_tools())} tools from MCP")

        session = self.conversation.get_or_create_session(session_id)
        session.add_message("user", user_message)

        # 1. 检查是否有待处理的 API Key 输入
        if session.state == SessionState.AWAITING_API_KEY:
            return await self._handle_api_key_input(session, user_message)

        # 2. 检查是否有待处理的安装确认
        if session.state == SessionState.AWAITING_INSTALL:
            result = await self._handle_install_response(session, user_message)
            if result:
                return result

        # 3. 检查是否是能力询问
        if self._is_capability_inquiry(user_message):
            response = self._handle_capability_inquiry()
            session.add_message("assistant", response.content)
            return response

        # 4. 检查是否是显式的安装/取消命令
        if self._is_install_command(user_message):
            return await self._handle_install_command(session, user_message)

        if self._is_cancel_command(user_message):
            return self._handle_cancel_command(session)

        # 5. 正常对话 - ReAct loop
        return await self._react_loop(session)

    async def _react_loop(self, session: ConversationSession) -> AgentResponse:
        """
        ReAct 循环: LLM → 工具调用 → 结果 → LLM → ...
        """
        # 获取可用工具
        available_tools = self.registry.get_all_tools()
        openai_tools = self.registry.get_openai_tools()

        # 添加 catalog 中的"虚拟工具"让 LLM 知道还有哪些能力可以安装
        install_hint_tools = self._build_install_hint_tools()
        all_tools = openai_tools + install_hint_tools

        if not all_tools:
            # 没有任何工具，直接对话
            return await self._handle_direct_chat(session)

        # 构建系统提示词
        system_prompt = self._build_agent_system_prompt(session)

        # 获取对话历史
        history = session.get_history(max_messages=20)

        # ReAct 循环（最多 5 轮）
        max_iterations = 5
        all_tool_calls = []
        all_tool_results = []
        messages = list(history)

        for iteration in range(max_iterations):
            try:
                turn = await self.llm_client.chat_with_tools(
                    messages=messages,
                    tools=all_tools,
                    system_prompt=system_prompt
                )

                logger.debug(f"ReAct iter {iteration}: finish={turn.finish_reason}, tool_calls={[tc.name for tc in turn.tool_calls] if turn.tool_calls else []}")

                if turn.finish_reason == "stop" or not turn.tool_calls:
                    # LLM 给出了最终回答
                    session.add_message("assistant", turn.content)
                    return AgentResponse(
                        content=turn.content,
                        tool_calls=all_tool_calls or None,
                        tool_results=all_tool_results or None
                    )

                # 处理工具调用
                for tc in turn.tool_calls:
                    all_tool_calls.append({
                        "tool": tc.name,
                        "arguments": tc.arguments
                    })

                    # 检查是否是安装请求的虚拟工具
                    if tc.name.startswith("_install_"):
                        tool_id = tc.name.replace("_install_", "")
                        install_response = await self._handle_tool_missing(
                            session, tool_id, messages
                        )
                        session.add_message("assistant", install_response.content)
                        return install_response

                    # 执行实际工具调用
                    logger.info(f"Calling tool: {tc.name}")
                    result = await self._execute_tool_call(tc)
                    all_tool_results.append({
                        "tool": tc.name,
                        "result": result
                    })

                    # 添加 assistant 消息和 tool 结果到消息列表
                    messages.append({
                        "role": "assistant",
                        "content": turn.content or "",
                        "tool_calls": [{
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments, ensure_ascii=False)
                            }
                        }]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False)
                    })

            except Exception as e:
                logger.error(f"ReAct loop error (iteration {iteration}): {e}")
                if iteration == 0:
                    return await self._handle_direct_chat(session)
                break

        # 超过最大迭代次数
        fallback = "我已经处理了你的请求，但似乎遇到了一些限制。你可以再试一次或者换个方式问哦~"
        session.add_message("assistant", fallback)
        return AgentResponse(content=fallback)

    async def _execute_tool_call(self, tool_call: ToolCall) -> Any:
        """执行工具调用"""
        tool_name = tool_call.name
        arguments = tool_call.arguments or {}

        # 从注册表中查找工具
        tools = self.registry.get_all_tools()
        matched_tool = None
        for t in tools:
            full_name = f"{t.server_name}_{t.name}"
            if full_name == tool_name or t.name == tool_name:
                matched_tool = t
                break

        if not matched_tool:
            return {"error": f"工具 '{tool_name}' 未找到"}

        try:
            result = await self.registry.call_tool(
                f"{matched_tool.server_name}_{matched_tool.name}",
                arguments
            )
            # 把 MCP CallToolResult 转为可序列化的格式
            if hasattr(result, 'content'):
                # MCP CallToolResult 对象
                contents = []
                for item in result.content:
                    if hasattr(item, 'text'):
                        contents.append(item.text)
                    else:
                        contents.append(str(item))
                text = "\n".join(contents)
                if hasattr(result, 'isError') and result.isError:
                    return {"error": text}
                return {"result": text}
            return {"result": str(result)}
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e)}

    async def _handle_tool_missing(
        self,
        session: ConversationSession,
        tool_id: str,
        messages: List[Dict]
    ) -> AgentResponse:
        """处理工具缺失 - 引导安装"""
        # 从 catalog 中查找工具
        tool = self.discovery.get_tool_by_id(tool_id)
        if not tool:
            # 尝试模糊搜索
            suggestions = self.discovery.search_by_intent(tool_id)
            if suggestions:
                tool = suggestions[0].tool
                tool_id = self._find_tool_id(tool)

        if not tool:
            response = "抱歉，我暂时没有找到能处理这个请求的工具呢 😅\n你可以告诉我'你有什么能力'来查看可用的工具~"
            return AgentResponse(content=response)

        # 设置待安装
        if not tool.mcp_servers:
            response = f"找到了 **{tool.name}** 工具，但目前没有可用的安装方式 😢"
            return AgentResponse(content=response)

        server = tool.mcp_servers[0]

        # 检查是否已安装
        if tool.is_installed:
            return AgentResponse(content=f"**{tool.name}** 已经安装了，可以直接使用哦~")

        # 检查环境变量
        missing_env = []
        for env in server.required_env:
            if env.get('required', True):
                env_name = env['name']
                if not os.environ.get(env_name):
                    missing_env.append(env)

        pending = PendingInstall(
            tool_id=tool_id,
            tool_name=tool.name,
            missing_env=missing_env,
            original_message=messages[-1].get("content", "") if messages else ""
        )

        if missing_env:
            # 需要 API Key
            pending.waiting_for_key = missing_env[0]['name']
            self.conversation.set_pending_install(session.session_id, pending)

            env_info = missing_env[0]
            key_text = f"""我找到了一个可以帮你查询天气的工具呢~ 🌤️

不过安装它需要一个 API Key:
  🔑 **{env_info['name']}**: {env_info.get('description', '')}"""
            if env_info.get('obtain_url'):
                key_text += f"\n  🔗 获取地址: {env_info['obtain_url']}"
            key_text += "\n\n把 Key 发给我就行，我帮你配置好~"

            return AgentResponse(content=key_text)

        # 无需 API Key，直接询问是否安装
        self.conversation.set_pending_install(session.session_id, pending)

        install_text = f"""我找到了一个可以帮助你的工具呢~ 🔧

  📦 **{tool.name}**: {tool.description}

要不要安装？回复 **"安装"** 即可~"""

        return AgentResponse(
            content=install_text,
            pending_install=tool_id
        )

    async def _handle_api_key_input(
        self,
        session: ConversationSession,
        user_message: str
    ) -> AgentResponse:
        """处理用户输入的 API Key"""
        pending = session.pending_install
        if not pending:
            session.state = SessionState.IDLE
            return AgentResponse(content="抱歉出了点问题，我们重新来吧~")

        # 验证 Key 格式（简单验证：非空且长度合理）
        key_value = user_message.strip()
        if len(key_value) < 8:
            return AgentResponse(content="这个 Key 看起来不太对哦，再检查一下？ 🤔")

        # 保存到 .env
        env_name = pending.waiting_for_key
        saved = self._save_env_variable(env_name, key_value)

        if not saved:
            return AgentResponse(content="保存配置时出了点问题 😢 你可以手动编辑 .env 文件添加这个配置。")

        logger.info(f"Saved API key: {env_name}")

        # 移除已处理的 env
        pending.missing_env = [
            e for e in pending.missing_env if e['name'] != env_name
        ]

        # 检查是否还有其他缺少的 env
        if pending.missing_env:
            next_env = pending.missing_env[0]
            pending.waiting_for_key = next_env['name']
            self.conversation.set_pending_install(session.session_id, pending)

            env_text = f"✅ {env_name} 已保存！\n\n"
            env_text += f"还需要一个配置:\n"
            env_text += f"  🔑 **{next_env['name']}**: {next_env.get('description', '')}"
            if next_env.get('obtain_url'):
                env_text += f"\n  🔗 获取地址: {next_env['obtain_url']}"
            env_text += "\n\n发给我就行~"

            return AgentResponse(content=env_text)

        # 所有 Key 都有了，自动安装
        pending.waiting_for_key = None
        return await self._execute_install(session, pending)

    async def _handle_install_response(
        self,
        session: ConversationSession,
        user_message: str
    ) -> Optional[AgentResponse]:
        """处理安装确认"""
        pending = session.pending_install
        if not pending:
            return None

        msg_lower = user_message.lower().strip()

        # 确认关键词
        confirm_kw = ["安装", "install", "好的", "ok", "yes", "是", "确认", "装"]
        deny_kw = ["不用了", "取消", "算了", "no", "不装", "cancel", "否", "不要"]

        if any(kw in msg_lower for kw in deny_kw):
            self.conversation.clear_pending_install(session.session_id)
            return AgentResponse(content="好的，那就不安装啦~ 以后需要的话随时告诉我哦 😊")

        if any(kw in msg_lower for kw in confirm_kw):
            return await self._execute_install(session, pending)

        return None

    async def _execute_install(
        self,
        session: ConversationSession,
        pending: PendingInstall
    ) -> AgentResponse:
        """执行安装"""
        tool_id = pending.tool_id

        # 检查环境变量
        requirements = await self.installer.check_requirements(tool_id)
        if not requirements["valid"]:
            missing = requirements.get("missing_env", [])
            if missing:
                pending.missing_env = missing
                pending.waiting_for_key = missing[0]['name']
                self.conversation.set_pending_install(session.session_id, pending)

                env = missing[0]
                text = f"还需要配置一个 Key:\n  🔑 **{env['name']}**: {env.get('description', '')}"
                if env.get('obtain_url'):
                    text += f"\n  🔗 获取地址: {env['obtain_url']}"
                text += "\n\n发给我就行~"
                return AgentResponse(content=text)

        # 执行安装
        logger.info(f"Installing tool: {tool_id}")
        result = await self.installer.install_server(tool_id)

        if result.success:
            # 热连接新安装的 MCP 服务器
            try:
                if self.mcp_manager:
                    from ..mcp.mcp_manager import MCPServerInfo
                    import yaml

                    # 从 mcp_servers.yaml 读取配置
                    mcp_config_path = self.installer.mcp_config_path
                    if mcp_config_path.exists():
                        with open(mcp_config_path, 'r', encoding='utf-8') as f:
                            config = yaml.safe_load(f) or {}

                        server_cfg = config.get('servers', {}).get(tool_id, {})
                        if server_cfg:
                            server_info = MCPServerInfo(
                                name=tool_id,
                                enabled=True,
                                command=server_cfg.get('command', ''),
                                args=server_cfg.get('args', []),
                                env=server_cfg.get('env', {}),
                                url=server_cfg.get('url')
                            )
                            self.mcp_manager.add_server(server_info)
                            await self.mcp_manager.connect_server(tool_id)

                            # 同步工具注册表
                            await self.registry.sync_from_mcp()
                            logger.info(f"Hot-connected MCP server: {tool_id}")
            except Exception as e:
                logger.warning(f"Hot-connect failed (restart may be needed): {e}")

            # 清除待安装状态
            self.conversation.clear_pending_install(session.session_id)

            # 重新执行用户原始请求
            if pending.original_message:
                # 创建新会话消息，重新走 ReAct loop
                retry_session = self.conversation.get_or_create_session(
                    f"{session.session_id}_retry"
                )
                retry_session.add_message("user", pending.original_message)

                try:
                    retry_response = await self._react_loop(retry_session)
                    install_msg = f"✅ **{pending.tool_name}** 安装成功！🎉\n\n"
                    # 清理重试会话
                    self.conversation.remove_session(f"{session.session_id}_retry")
                    return AgentResponse(content=install_msg + retry_response.content)
                except Exception as e:
                    logger.error(f"Retry after install failed: {e}")

            return AgentResponse(
                content=f"✅ **{pending.tool_name}** 安装成功！🎉\n\n现在可以使用了，你再试试看~"
            )
        else:
            self.conversation.clear_pending_install(session.session_id)
            return AgentResponse(
                content=f"安装遇到了一些问题 😢\n\n{result.message}\n\n你可以稍后再试，或者手动安装。"
            )

    async def _handle_direct_chat(self, session: ConversationSession) -> AgentResponse:
        """无工具时的直接对话"""
        history = session.get_history()
        system_prompt = persona_manager.system_prompt

        response_text = await self.llm_client.chat(
            message=history[-1]["content"] if history else "",
            system_prompt=system_prompt,
            history=history[:-1] if len(history) > 1 else None
        )

        session.add_message("assistant", response_text)
        return AgentResponse(content=response_text)

    def _build_agent_system_prompt(self, session: ConversationSession) -> str:
        """构建 Agent 系统提示词"""
        base_prompt = persona_manager.system_prompt

        agent_prompt = f"""{base_prompt}

你是一个智能助手，可以使用工具来帮助用户。

重要规则:
1. 优先使用工具来回答需要实时数据的问题
2. 如果工具返回了结果，用自然友好的语言回答，不要提及"工具"这个词
3. 如果用户的问题需要工具但工具不存在，调用 _install_<tool_id> 来引导安装
4. 对于常识性问题，直接回答即可
5. 保持对话上下文，理解用户指代（如"那上海呢"指的是同样的问题在上海的情况）
6. 用简洁友好的语言回答"""

        # 添加上下文信息
        if session.context:
            ctx_text = "\n\n当前对话上下文:\n"
            for k, v in session.context.items():
                ctx_text += f"- {k}: {v}\n"
            agent_prompt += ctx_text

        return agent_prompt

    def _build_install_hint_tools(self) -> List[Dict]:
        """
        构建安装提示工具列表
        让 LLM 知道可以安装哪些能力（作为虚拟工具）
        """
        tools = []
        catalog_tools = self.discovery.get_all_tools()

        for tool in catalog_tools:
            if tool.is_installed:
                continue
            # 为每个未安装的工具创建一个"安装提示"虚拟工具
            tools.append({
                "type": "function",
                "function": {
                    "name": f"_install_{tool.name.lower().replace(' ', '_')}",
                    "description": f"[未安装] {tool.name}: {tool.description} - 当用户需要此能力时调用此函数来引导安装",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "为什么需要安装这个工具"
                            }
                        },
                        "required": ["reason"]
                    }
                }
            })

        return tools

    def _find_tool_id(self, tool) -> Optional[str]:
        """从 catalog 中查找 tool_id"""
        for tid, t in self.discovery._catalog.items():
            if t.name == tool.name:
                return tid
        return tool.name.lower().replace(" ", "_")

    def _is_capability_inquiry(self, message: str) -> bool:
        """检查是否是能力询问"""
        keywords = [
            "你能做什么", "你有什么能力", "你会什么", "你的功能",
            "what can you do", "your capabilities", "你的技能",
            "你能帮我做什么", "你有什么工具", "支持什么", "能力"
        ]
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in keywords)

    def _handle_capability_inquiry(self) -> AgentResponse:
        """处理能力询问"""
        tools = self.registry.get_all_tools()
        catalog_tools = self.discovery.get_all_tools()

        lines = ["这是我的能力清单: \n"]

        if tools:
            lines.append("✅ **已启用的工具:**")
            for tool in tools:
                lines.append(f"  • {tool.name}: {tool.description}")
            lines.append("")

        available_not_installed = [t for t in catalog_tools if not t.is_installed]
        if available_not_installed:
            lines.append("📦 **可安装的工具:**")
            for tool in available_not_installed[:8]:
                lines.append(f"  • {tool.name}: {tool.description}")
            lines.append("")
            lines.append("告诉我你需要什么能力，我可以帮你安装~")

        if not tools and not available_not_installed:
            lines.append("当前没有配置任何工具。")
            lines.append("你可以通过编辑 mcp_servers.yaml 添加 MCP 服务器。")

        return AgentResponse(content="\n".join(lines))

    def _is_install_command(self, message: str) -> bool:
        """检查是否是安装命令"""
        keywords = ["安装", "帮我安装", "install", "装一下", "装"]
        msg_lower = message.lower().strip()
        # 精确匹配短的安装命令
        return msg_lower in keywords or any(msg_lower.startswith(kw) for kw in keywords)

    def _is_cancel_command(self, message: str) -> bool:
        """检查是否是取消命令"""
        keywords = ["不用了", "取消", "算了", "cancel", "不装", "不要"]
        msg_lower = message.lower().strip()
        return msg_lower in keywords

    async def _handle_install_command(
        self,
        session: ConversationSession,
        user_message: str
    ) -> AgentResponse:
        """处理显式的安装命令"""
        # 如果有待安装的工具
        if session.pending_install:
            return await self._execute_install(session, session.pending_install)

        # 尝试从消息中提取工具名称
        msg_clean = user_message.replace("帮我", "").replace("安装", "").replace("install", "").strip()

        if not msg_clean:
            return AgentResponse(content="你想安装什么工具呢？告诉我具体的需求，比如'查天气'、'搜索'之类的~")

        # 搜索相关工具
        suggestions = self.discovery.search_by_intent(msg_clean)
        if suggestions:
            tool = suggestions[0].tool
            tool_id = self._find_tool_id(tool)

            pending = PendingInstall(
                tool_id=tool_id,
                tool_name=tool.name,
                original_message=user_message
            )

            # 检查环境变量
            if tool.mcp_servers:
                server = tool.mcp_servers[0]
                missing_env = []
                for env in server.required_env:
                    if env.get('required', True) and not os.environ.get(env['name']):
                        missing_env.append(env)
                pending.missing_env = missing_env

            if pending.missing_env:
                pending.waiting_for_key = pending.missing_env[0]['name']
                self.conversation.set_pending_install(session.session_id, pending)

                env = pending.missing_env[0]
                text = f"安装 **{tool.name}** 需要一个 API Key:\n"
                text += f"  🔑 **{env['name']}**: {env.get('description', '')}"
                if env.get('obtain_url'):
                    text += f"\n  🔗 获取地址: {env['obtain_url']}"
                text += "\n\n发给我就行~"
                return AgentResponse(content=text)

            self.conversation.set_pending_install(session.session_id, pending)
            return AgentResponse(
                content=f"找到了 **{tool.name}** - {tool.description}\n\n确认安装吗？回复 **'安装'** 确认~",
                pending_install=tool_id
            )

        return AgentResponse(content="没有找到匹配的工具呢 🤔 告诉我你的具体需求，我帮你找找看~")

    def _handle_cancel_command(self, session: ConversationSession) -> AgentResponse:
        """处理取消命令"""
        if session.pending_install:
            tool_name = session.pending_install.tool_name
            self.conversation.clear_pending_install(session.session_id)
            return AgentResponse(content=f"好的，{tool_name} 就不安装啦~ 需要的时候随时告诉我哦 😊")
        return AgentResponse(content="好的~ 有什么需要帮忙的告诉我就行 😊")

    def _save_env_variable(self, name: str, value: str) -> bool:
        """保存环境变量到 .env 文件"""
        try:
            from pathlib import Path
            env_path = Path(__file__).parent.parent.parent / ".env"

            # 读取现有内容
            lines = []
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

            # 查找是否已存在
            found = False
            new_lines = []
            for line in lines:
                if line.strip().startswith(f"{name}="):
                    new_lines.append(f"{name}={value}\n")
                    found = True
                else:
                    new_lines.append(line)

            if not found:
                new_lines.append(f"{name}={value}\n")

            # 写入
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            # 同时设置到当前环境
            os.environ[name] = value

            return True
        except Exception as e:
            logger.error(f"Failed to save env variable: {e}")
            return False


# 全局实例
_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> Optional[AgentOrchestrator]:
    return _orchestrator


def set_orchestrator(orchestrator: AgentOrchestrator):
    global _orchestrator
    _orchestrator = orchestrator
