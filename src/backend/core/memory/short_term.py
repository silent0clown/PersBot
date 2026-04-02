import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ShortTermMemory:
    """当前对话上下文管理"""

    max_tokens: int = 8000
    compress_threshold: float = 0.8  # 80% 时触发压缩
    
    def __post_init__(self):
        self.messages: List[Dict[str, Any]] = []
        self._system_prompt: Optional[str] = None
    
    def set_system_prompt(self, prompt: str):
        """设置系统提示词"""
        self._system_prompt = prompt
        # 如果还没有消息，添加 system 消息
        if not self.messages or self.messages[0].get("role") != "system":
            self.messages.insert(0, {"role": "system", "content": prompt})
        else:
            self.messages[0]["content"] = prompt
    
    def add(self, role: str, content: str):
        """添加消息"""
        self.messages.append({"role": role, "content": content})
        
        # 当使用量达到上限的 80% 时提前压缩
        current_tokens = self._estimate_tokens()
        if current_tokens > self.max_tokens * self.compress_threshold:
            self._compress()
    
    def add_tool_call(self, tool_name: str, arguments: Dict[str, Any]):
        """添加工具调用消息"""
        self.messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": f"call_{len(self.messages)}",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }]
        })
    
    def add_tool_result(self, tool_call_id: str, result: str):
        """添加工具结果消息"""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result
        })
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """返回当前上下文"""
        return self.messages.copy()
    
    def get_messages_for_llm(self) -> List[Dict[str, Any]]:
        """返回适合发给 LLM 的消息格式"""
        return self.messages.copy()
    
    def clear(self):
        """清空 (保留system prompt)"""
        if self.messages and self.messages[0].get("role") == "system":
            self.messages = [self.messages[0]]
        else:
            self.messages = []
    
    def clear_all(self):
        """完全清空"""
        self.messages = []
    
    def _estimate_tokens(self) -> int:
        """粗略估算 token 数量"""
        total = 0
        for msg in self.messages:
            content = msg.get("content", "")
            # 简单估算: 1 token ≈ 4 字符
            total += len(content) // 4
            # 加上工具调用的估算
            if "tool_calls" in msg:
                import json
                total += len(json.dumps(msg["tool_calls"])) // 4
        return total
    
    def _compress(self):
        """
        压缩策略 (滑动窗口 + 重要性加权):
        1. 保留 system prompt (messages[0])
        2. 保留最近的 2/3 消息 (最近的对话最重要)
        3. 对较早的 1/3 消息用 LLM 生成摘要
        4. 插入摘要作为 system 消息
        """
        if len(self.messages) <= 2:
            return  # 没有可压缩的内容
        
        system = self.messages[0] if self.messages[0].get("role") == "system" else None
        non_system = [m for m in self.messages if m.get("role") != "system"]
        
        if not non_system:
            return
        
        total = len(non_system)
        keep_recent = max(total * 2 // 3, 3)  # 至少保留最近3条
        to_summarize = non_system[:total - keep_recent]
        remaining = non_system[total - keep_recent:]
        
        if not to_summarize:
            return  # 无可压缩内容
        
        # 生成摘要 (这里用简单方法，实际应该调用 LLM)
        summary = self._generate_summary(to_summarize)
        
        # 构建压缩后的消息
        new_messages = []
        if system:
            new_messages.append(system)
        
        new_messages.append({
            "role": "system",
            "content": f"[之前的对话摘要] {summary}"
        })
        new_messages.extend(remaining)
        
        self.messages = new_messages
        logger.info(f"Compressed memory: {total} -> {len(self.messages)} messages")
    
    def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        """生成对话摘要 (简化版)"""
        # 实际实现应该调用 LLM
        # 这里用简单的规则进行摘要
        user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
        assistant_msgs = [m["content"] for m in messages if m.get("role") == "assistant"]
        
        summary_parts = []
        if user_msgs:
            # 取第一和最后一条用户消息
            summary_parts.append(f"用户共发送 {len(user_msgs)} 条消息")
            if user_msgs[0]:
                summary_parts.append(f"最初: {user_msgs[0][:50]}...")
            if len(user_msgs) > 1 and user_msgs[-1]:
                summary_parts.append(f"最后: {user_msgs[-1][:50]}...")
        
        if assistant_msgs:
            summary_parts.append(f"助手回复 {len(assistant_msgs)} 次")
        
        return " | ".join(summary_parts) if summary_parts else "多轮对话"
    
    def get_context_summary(self) -> str:
        """获取当前上下文摘要 (用于日志/调试)"""
        roles = {}
        for msg in self.messages:
            role = msg.get("role", "unknown")
            roles[role] = roles.get(role, 0) + 1
        
        token_count = self._estimate_tokens()
        return f"messages: {len(self.messages)}, tokens: {token_count}, roles: {roles}"
    
    def get_conversation_turns(self) -> int:
        """获取对话轮次 (用户消息数)"""
        return sum(1 for m in self.messages if m.get("role") == "user")