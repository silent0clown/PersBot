import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MemoryAttachment:
    """结构化记忆附件，让 LLM 知道每条记忆的可信度"""
    content: str
    source: str  # "user_told" | "inferred" | "observed"
    relevance: float
    decay: float
    memory_type: str  # "fact" | "preference" | "event" | "emotion"


class MemoryRetriever:
    """记忆检索与注入"""

    def __init__(self, long_term_memory, top_k: int = 5, min_decay: float = 0.1):
        self.long_term = long_term_memory
        self.top_k = top_k
        self.min_decay = min_decay

    def inject_memories(self, user_message: str, system_prompt: str) -> str:
        """
        检索相关记忆并结构化注入到 system prompt 中

        流程:
        1. 用 user_message 检索 top_k 相关记忆
        2. 按 decay_score 过滤 (< min_decay 的不注入)
        3. 转为 MemoryAttachment，附带来源和可信度信息
        4. 格式化后追加到 system prompt
        5. 更新被召回记忆的 last_accessed 和 access_count
        """
        raw_memories = self.long_term.retrieve(user_message, top_k=self.top_k)
        raw_memories = [m for m in raw_memories if m.get("decay_score", 0) > self.min_decay]

        if not raw_memories:
            return system_prompt

        attachments = [
            MemoryAttachment(
                content=m["content"],
                source=m["source"],
                relevance=m.get("relevance", 0.5),
                decay=m.get("decay_score", 0.5),
                memory_type=m["type"]
            )
            for m in raw_memories
        ]

        # 更新访问记录
        for m in raw_memories:
            if m.get("id"):
                self.long_term.update_access(m["id"])

        return system_prompt + "\n\n" + self._format_attachments(attachments)

    def _format_attachments(self, attachments: List[MemoryAttachment]) -> str:
        """结构化格式化记忆，标注来源和可信度"""
        lines = ["[你记得关于主人的以下信息]"]
        
        for a in attachments:
            source_label = {
                "user_told": "主人说过",
                "inferred": "推断",
                "observed": "观察到"
            }
            trust = "高" if a.decay > 0.6 else "中" if a.decay > 0.3 else "低"
            label = source_label.get(a.source, a.source)
            
            type_emoji = {
                "fact": "📌",
                "preference": "💡",
                "event": "📅",
                "emotion": "💭"
            }
            emoji = type_emoji.get(a.memory_type, "📝")
            
            lines.append(f"{emoji} [{label}|可信度:{trust}] {a.content}")
        
        return "\n".join(lines)

    def extract_and_store(self, user_message: str, assistant_response: str, llm_client = None) -> List[Dict[str, Any]]:
        """
        从对话中提取值得记忆的信息并存入

        Args:
            user_message: 用户消息
            assistant_response: 助手回复
            llm_client: LLM 客户端 (用于判断是否值得记忆)

        Returns: 提取的记忆列表
        """
        # 简单规则判断 (实际应该用 LLM)
        memories_to_store = []
        
        # 检查用户消息中是否包含重要信息
        important_patterns = [
            r"我叫",
            r"我.*过敏",
            r"我喜欢",
            r"我讨厌",
            r"我的.*是",
        ]
        
        import re
        for pattern in important_patterns:
            match = re.search(pattern, user_message)
            if match:
                content = match.group(0)
                memories_to_store.append({
                    "content": content,
                    "type": "fact",
                    "importance": 0.8,
                    "source": "user_told"
                })
        
        # 存入长期记忆
        stored_ids = []
        for mem in memories_to_store:
            memory_id = self.long_term.store(
                content=mem["content"],
                mem_type=mem["type"],
                importance=mem["importance"],
                source=mem["source"]
            )
            stored_ids.append(memory_id)
            logger.info(f"Extracted and stored memory: {mem['content'][:50]}...")
        
        return stored_ids

    def get_all_memories(self, memory_type: str = None) -> List[Dict[str, Any]]:
        """获取所有记忆 (管理用)"""
        # 简单实现，实际应该添加过滤
        result = self.long_term.retrieve("", top_k=100)
        if memory_type:
            result = [m for m in result if m.get("type") == memory_type]
        return result

    def forget_memory(self, memory_id: int):
        """删除指定记忆"""
        self.long_term.forget(memory_id)