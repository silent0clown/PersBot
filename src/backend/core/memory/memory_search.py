import os
import re
import math
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: Dict[str, List[str]] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_length: float = 0
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.N: int = 0
        
    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        return [w for w in words if len(w) > 1]
    
    def add_document(self, doc_id: str, content: str):
        tokens = self._tokenize(content)
        self.documents[doc_id] = tokens
        self.doc_lengths[doc_id] = len(tokens)
        
        for term in set(tokens):
            self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1
            
        self.N = len(self.documents)
        
        total_length = sum(self.doc_lengths.values())
        self.avg_doc_length = total_length / self.N if self.N > 0 else 0
        
        for term, df in self.doc_freqs.items():
            self.idf[term] = math.log((self.N - df + 0.5) / (df + 0.5) + 1)
    
    def _score(self, doc_id: str, query: str) -> float:
        if doc_id not in self.documents:
            return 0.0
            
        query_tokens = self._tokenize(query)
        doc_tokens = self.documents[doc_id]
        doc_length = self.doc_lengths[doc_id]
        
        score = 0.0
        doc_tf = Counter(doc_tokens)
        
        for term in query_tokens:
            if term not in self.idf:
                continue
                
            tf = doc_tf.get(term, 0)
            idf = self.idf[term]
            
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
            
            score += idf * numerator / denominator
            
        return score
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.documents:
            return []
            
        scores = []
        for doc_id in self.documents:
            score = self._score(doc_id, query)
            if score > 0:
                scores.append((doc_id, score))
                
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return [{"doc_id": doc_id, "score": score} for doc_id, score in scores[:top_k]]


class MemorySearch:
    def __init__(self, store, workspace: str = None):
        self.store = store
        self.workspace = Path(workspace or os.path.expanduser("~/.persbot/workspace"))
        self._index: Dict[str, str] = {}
        self._bm25 = BM25()
        self._indexed = False
        
    async def index_all(self):
        files = await self.store.list_memory_files()
        
        self._index.clear()
        self._bm25 = BM25()
        
        for file_info in files:
            path = file_info["path"]
            try:
                async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    
                self._index[path] = content
                self._bm25.add_document(path, content)
                
            except Exception as e:
                logger.error(f"Failed to index {path}: {e}")
                
        self._indexed = True
        logger.info(f"Indexed {len(self._index)} memory files")
        
    async def search(
        self, 
        query: str, 
        max_results: int = 5,
        min_score: float = 0.1
    ) -> List[Dict[str, Any]]:
        if not self._indexed:
            await self.index_all()
            
        results = self._bm25.search(query, top_k=max_results * 2)
        
        output = []
        for result in results:
            doc_id = result["doc_id"]
            score = result["score"]
            
            if score < min_score:
                continue
                
            content = self._index.get(doc_id, "")
            lines = content.split('\n')
            
            matched_lines = []
            query_lower = query.lower()
            for i, line in enumerate(lines, 1):
                if query_lower in line.lower():
                    matched_lines.append({
                        "line": i,
                        "content": line.strip()
                    })
                    
            snippet = "\n".join(l["content"] for l in matched_lines[:10])
            
            output.append({
                "path": doc_id,
                "score": score,
                "snippet": snippet[:500],
                "matched_lines": matched_lines[:5]
            })
            
            if len(output) >= max_results:
                break
                
        return output
    
    async def refresh_index(self):
        await self.index_all()
        
    def is_indexed(self) -> bool:
        return self._indexed


import aiofiles
