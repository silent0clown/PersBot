import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .memory_store import MemoryStore
from .memory_search import MemorySearch

logger = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self, workspace: str = None):
        self.workspace = workspace or os.path.expanduser("~/.persbot/workspace")
        self._store = MemoryStore(self.workspace)
        self._search = MemorySearch(self._store, self.workspace)
        self._initialized = False
        
    async def initialize(self):
        if self._initialized:
            return
            
        await self._search.index_all()
        self._initialized = True
        logger.info("MemoryManager initialized")
        
    async def shutdown(self):
        self._initialized = False
        logger.info("MemoryManager shutdown")
        
    async def get_context_for_prompt(self) -> List[Dict[str, Any]]:
        content_parts = []
        
        recent = await self._store.read_today_and_yesterday()
        
        if "today" in recent:
            content_parts.append({
                "type": "daily",
                "date": "today",
                "content": recent["today"]
            })
            
        if "yesterday" in recent:
            content_parts.append({
                "type": "daily",
                "date": "yesterday",
                "content": recent["yesterday"]
            })
            
        longterm = await self._store.read_longterm()
        if longterm:
            content_parts.append({
                "type": "longterm",
                "content": longterm
            })
            
        return content_parts
    
    async def write_daily(self, content: str, date: Optional[datetime] = None):
        await self._store.append_daily(content, date)
        await self._search.refresh_index()
        
    async def write_longterm(self, content: str):
        await self._store.write_longterm(content)
        await self._search.refresh_index()
        
    async def search(
        self, 
        query: str, 
        max_results: int = 5,
        min_score: float = 0.1
    ) -> List[Dict[str, Any]]:
        return await self._search.search(query, max_results, min_score)
        
    async def get_file(self, path: str, from_line: int = None, lines: int = None) -> Dict[str, Any]:
        return await self._store.read_file(path, from_line, lines)
        
    async def list_files(self) -> List[Dict[str, Any]]:
        return await self._store.list_memory_files()
        
    def is_initialized(self) -> bool:
        return self._initialized


_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(workspace: str = None) -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(workspace)
    return _memory_manager
