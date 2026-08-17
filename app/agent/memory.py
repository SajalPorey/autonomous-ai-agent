import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models.agent import MemoryItem


class MemoryManager:
    """Manages short-term working context and persistent memory storage for Sazon."""

    def __init__(self, memory_file: str = ".sazon_memory.json"):
        self.memory_file = memory_file
        self.short_term_memory: List[MemoryItem] = []
        self.persistent_memory: Dict[str, MemoryItem] = {}
        self._load_persistent()

    def add_working_memory(self, content: str, category: str = "observation", metadata: Optional[Dict[str, Any]] = None):
        item = MemoryItem(
            id=f"mem_{len(self.short_term_memory) + 1}",
            content=content,
            category=category,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        self.short_term_memory.append(item)

    def save_persistent(self, key: str, value: str, category: str = "knowledge"):
        item = MemoryItem(
            id=key,
            content=value,
            category=category,
            timestamp=datetime.utcnow()
        )
        self.persistent_memory[key] = item
        self._save_to_disk()

    def get_persistent(self, key: str) -> Optional[str]:
        item = self.persistent_memory.get(key)
        return item.content if item else None

    def search_memories(self, query: str) -> List[MemoryItem]:
        query_lower = query.lower()
        results = []
        for mem in self.short_term_memory + list(self.persistent_memory.values()):
            if query_lower in mem.content.lower() or query_lower in mem.id.lower():
                results.append(mem)
        return results

    def get_context_summary(self) -> str:
        if not self.short_term_memory and not self.persistent_memory:
            return "No prior context available."

        lines = ["--- Agent Context & Memory ---"]
        if self.persistent_memory:
            lines.append("Saved Knowledge:")
            for k, v in self.persistent_memory.items():
                lines.append(f"  - [{k}]: {v.content[:150]}")
        
        if self.short_term_memory:
            lines.append("Recent Observations:")
            for mem in self.short_term_memory[-5:]:
                lines.append(f"  - ({mem.category}): {mem.content[:150]}")

        return "\n".join(lines)

    def _load_persistent(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.persistent_memory[k] = MemoryItem(**v)
            except Exception:
                self.persistent_memory = {}

    def _save_to_disk(self):
        try:
            serialized = {k: v.model_dump(mode="json") for k, v in self.persistent_memory.items()}
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save persistent memory: {e}")
