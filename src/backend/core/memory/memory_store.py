import os
import aiofiles
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class MemoryStore:
    def __init__(self, workspace: str = None):
        self.workspace = Path(workspace or os.path.expanduser("~/.persbot/workspace"))
        self.memory_dir = self.workspace / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_daily_file(self, date: Optional[datetime] = None) -> Path:
        date = date or datetime.now()
        return self.memory_dir / f"{date.strftime('%Y-%m-%d')}.md"
    
    def _get_longterm_file(self) -> Path:
        return self.workspace / "MEMORY.md"
    
    async def read_daily(self, date: Optional[datetime] = None) -> str:
        file_path = self._get_daily_file(date)
        if not file_path.exists():
            return ""
        
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    
    async def read_longterm(self) -> str:
        file_path = self._get_longterm_file()
        if not file_path.exists():
            return ""
        
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    
    async def read_today_and_yesterday(self) -> Dict[str, str]:
        today = datetime.now()
        yesterday = today.replace(day=today.day - 1)
        
        results = {}
        
        today_content = await self.read_daily(today)
        if today_content:
            results["today"] = today_content
            
        yesterday_content = await self.read_daily(yesterday)
        if yesterday_content:
            results["yesterday"] = yesterday_content
            
        return results
    
    async def append_daily(self, content: str, date: Optional[datetime] = None):
        file_path = self._get_daily_file(date)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        async with aiofiles.open(file_path, 'a', encoding='utf-8') as f:
            await f.write(f"\n## {timestamp}\n{content}\n")
            
        logger.info(f"Appended to daily memory: {file_path}")
    
    async def write_longterm(self, content: str):
        file_path = self._get_longterm_file()
        
        async with aiofiles.open(file_path, 'a', encoding='utf-8') as f:
            await f.write(f"\n{content}\n")
            
        logger.info(f"Wrote to longterm memory: {file_path}")
    
    async def read_file(self, path: str, from_line: int = None, lines: int = None) -> Dict[str, Any]:
        file_path = Path(path)
        
        if not file_path.exists():
            return {"text": "", "path": str(path)}
        
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            
        all_lines = content.split('\n')
        
        if from_line is not None and lines is not None:
            start = max(0, from_line - 1)
            end = min(len(all_lines), start + lines)
            selected_lines = all_lines[start:end]
            content = '\n'.join(selected_lines)
            
        return {"text": content, "path": str(path)}
    
    async def list_memory_files(self) -> List[Dict[str, Any]]:
        files = []
        
        for md_file in self.memory_dir.glob("*.md"):
            stat = md_file.stat()
            files.append({
                "path": str(md_file),
                "name": md_file.name,
                "modified": stat.st_mtime
            })
            
        longterm = self._get_longterm_file()
        if longterm.exists():
            stat = longterm.stat()
            files.append({
                "path": str(longterm),
                "name": longterm.name,
                "modified": stat.st_mtime
            })
            
        return files
    
    async def search_in_file(self, path: str, query: str) -> List[Dict[str, Any]]:
        file_path = Path(path)
        
        if not file_path.exists():
            return []
            
        results = []
        
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            if query.lower() in line.lower():
                results.append({
                    "line": i,
                    "content": line,
                    "path": str(path)
                })
                
        return results
