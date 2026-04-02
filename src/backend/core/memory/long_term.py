import os
import sqlite3
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent


class MemoryType:
    """记忆类型"""
    FACT = "fact"           # 事实 (用户主动告知)
    PREFERENCE = "preference"  # 偏好
    EVENT = "event"         # 事件
    EMOTION = "emotion"     # 情感


class MemorySource:
    """记忆来源"""
    USER_TOLD = "user_told"    # 用户主动告知
    INFERRED = "inferred"       # LLM 推断
    OBSERVED = "observed"        # 行为观察


@dataclass
class Memory:
    """记忆条目"""
    id: Optional[int] = None
    type: str = "fact"
    content: str = ""
    embedding: Optional[bytes] = None
    importance: float = 0.5
    access_count: int = 0
    created_at: datetime = None
    last_accessed: datetime = None
    expires_at: Optional[datetime] = None
    decay_score: float = 1.0
    source: str = "inferred"
    is_deleted: bool = False
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_accessed is None:
            self.last_accessed = datetime.now()


class LongTermMemory:
    """持久化长期记忆"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = BASE_DIR / "data" / "memory.db"
        
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        
        # 配置 embedding
        self._embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self._embedding_dim = 1536  # text-embedding-3-small 维度
        
        logger.info(f"LongTermMemory initialized at {db_path}")

    def _init_tables(self):
        """初始化数据库表"""
        cursor = self.conn.cursor()
        
        # 长期记忆表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB,
                importance REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                decay_score REAL DEFAULT 1.0,
                source TEXT DEFAULT 'inferred',
                is_deleted INTEGER DEFAULT 0
            )
        """)
        
        # 对话历史归档表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                channel TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                token_count INTEGER
            )
        """)
        
        # 索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_decay ON memories(decay_score DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_deleted ON memories(is_deleted)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history(user_id)")
        
        self.conn.commit()

    def store(
        self,
        content: str,
        mem_type: str = "fact",
        importance: float = 0.5,
        source: str = "inferred",
        expires_at: str = None
    ) -> int:
        """存入一条长期记忆"""
        # 计算 embedding
        embedding = self._compute_embedding(content)
        
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO memories 
               (type, content, embedding, importance, source, expires_at) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (mem_type, content, embedding, importance, source, expires_at)
        )
        self.conn.commit()
        
        memory_id = cursor.lastrowid
        logger.debug(f"Stored memory {memory_id}: {content[:50]}...")
        return memory_id

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        检索与 query 最相关的 top_k 条记忆
        
        检索策略:
        1. 向量相似度
        2. 过滤已删除和过期记忆
        3. 综合排序: similarity * 0.6 + decay_score * 0.3 + importance * 0.1
        """
        query_embedding = self._compute_embedding(query)
        
        cursor = self.conn.cursor()
        
        # 获取所有未删除且未过期的记忆
        now = datetime.now().isoformat()
        cursor.execute("""
            SELECT * FROM memories 
            WHERE is_deleted = 0 
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY decay_score DESC
            LIMIT 100
        """, (now,))
        
        rows = cursor.fetchall()
        memories = []
        
        for row in rows:
            mem = dict(row)
            mem["created_at"] = datetime.fromisoformat(mem["created_at"])
            mem["last_accessed"] = datetime.fromisoformat(mem["last_accessed"])
            
            # 计算向量相似度
            if mem["embedding"]:
                similarity = self._cosine_similarity(
                    query_embedding,
                    np.frombuffer(mem["embedding"], dtype=np.float32)
                )
                mem["relevance"] = similarity
                
                # 综合评分
                score = (
                    similarity * 0.6 +
                    mem["decay_score"] * 0.3 +
                    mem["importance"] * 0.1
                )
                mem["score"] = score
                memories.append(mem)
        
        # 按综合评分排序
        memories.sort(key=lambda x: x["score"], reverse=True)
        
        # 返回 top_k
        return memories[:top_k]

    def update_access(self, memory_id: int):
        """更新记忆的访问信息"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE memories 
            SET access_count = access_count + 1, 
                last_accessed = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (memory_id,))
        self.conn.commit()

    def forget(self, memory_id: int):
        """软删除一条记忆"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE memories SET is_deleted = 1 WHERE id = ?",
            (memory_id,)
        )
        self.conn.commit()
        logger.info(f"Forgot memory {memory_id}")

    def decay_all(self):
        """批量更新所有记忆的衰减分数"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, importance, source, access_count, last_accessed 
            FROM memories 
            WHERE is_deleted = 0
        """)
        
        now = datetime.now()
        for row in cursor.fetchall():
            memory_id = row[0]
            importance = row[1]
            source = row[2]
            access_count = row[3]
            last_accessed = datetime.fromisoformat(row[4])
            
            # 计算衰减分数
            decay_score = self._calculate_decay_score(
                importance, source, access_count, last_accessed, now
            )
            
            cursor.execute(
                "UPDATE memories SET decay_score = ? WHERE id = ?",
                (decay_score, memory_id)
            )
        
        self.conn.commit()
        logger.info("Memory decay updated")

    def _compute_embedding(self, text: str) -> Optional[bytes]:
        """计算文本 embedding (简化版，返回 None)"""
        # 实际应该调用 embedding API
        # 这里用随机向量模拟，以便测试检索功能
        try:
            vector = np.random.randn(self._embedding_dim).astype(np.float32)
            # 归一化
            vector = vector / np.linalg.norm(vector)
            return vector.tobytes()
        except Exception as e:
            logger.warning(f"Failed to compute embedding: {e}")
            return None

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        try:
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
        except:
            return 0.0

    def _calculate_decay_score(
        self,
        importance: float,
        source: str,
        access_count: int,
        last_accessed: datetime,
        now: datetime
    ) -> float:
        """计算衰减分数"""
        days_ago = (now - last_accessed).days
        
        # 来源权重
        source_weight = {
            "user_told": 1.5,
            "inferred": 1.0,
            "observed": 0.8
        }
        importance_factor = importance * source_weight.get(source, 1.0)
        
        # 时间衰减
        recency_factor = 1.0 / (1.0 + 0.05 * days_ago)
        
        # 频率稳固
        frequency_factor = min(1.0, access_count / 5)
        
        # 用户主动告知的记忆，最低 0.5
        score = importance_factor * recency_factor * max(0.3, frequency_factor)
        if source == "user_told":
            score = max(score, 0.5)
        
        return min(1.0, score)

    def archive_chat(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        channel: str = "cli"
    ):
        """归档对话"""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO chat_history 
               (session_id, user_id, role, content, channel) 
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, user_id, role, content, channel)
        )
        self.conn.commit()

    def get_chat_history(
        self,
        session_id: str = None,
        user_id: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取对话历史"""
        cursor = self.conn.cursor()
        
        if session_id:
            cursor.execute("""
                SELECT * FROM chat_history 
                WHERE session_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (session_id, limit))
        elif user_id:
            cursor.execute("""
                SELECT * FROM chat_history 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (user_id, limit))
        else:
            cursor.execute(f"""
                SELECT * FROM chat_history 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """关闭数据库连接"""
        self.conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM memories WHERE is_deleted = 0")
        total_memories = cursor.fetchone()[0]
        
        cursor.execute("SELECT type, COUNT(*) FROM memories WHERE is_deleted = 0 GROUP BY type")
        type_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("SELECT COUNT(*) FROM chat_history")
        total_chats = cursor.fetchone()[0]
        
        return {
            "total_memories": total_memories,
            "type_counts": type_counts,
            "total_chats": total_chats
        }