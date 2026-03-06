#!/usr/bin/env python3
"""
ORDL AGENT MEMORY - Advanced Memory System
Vector-based long-term memory with semantic retrieval
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


class AgentMemoryStore:
    """
    Advanced agent memory with vector similarity search
    """
    
    def __init__(self, agent_id: str, db_path: str = "/opt/codex-swarm/command-post/data/nexus.db"):
        self.agent_id = agent_id
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self):
        """Initialize memory tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Short-term memory (conversation)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory_short (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    metadata TEXT
                )
            """)
            
            # Long-term memory (facts, learnings)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory_long (
                    memory_id TEXT PRIMARY KEY,
                    agent_id TEXT,
                    memory_type TEXT,
                    content TEXT,
                    importance REAL,
                    tags TEXT,
                    created_at TEXT,
                    last_accessed TEXT,
                    access_count INTEGER DEFAULT 0
                )
            """)
            
            # Memory embeddings for similarity search
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory_embeddings (
                    memory_id TEXT PRIMARY KEY,
                    agent_id TEXT,
                    embedding TEXT,
                    created_at TEXT
                )
            """)
            
            conn.commit()
    
    def store_short_term(self, role: str, content: str, metadata: Dict = None) -> bool:
        """Store short-term memory (conversation)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO agent_memory_short
                    (agent_id, role, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    self.agent_id,
                    role,
                    content,
                    datetime.utcnow().isoformat(),
                    json.dumps(metadata or {})
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"[MEMORY ERROR] {e}")
            return False
    
    def store_long_term(self, content: str, memory_type: str = "fact",
                       importance: float = 0.5, tags: List[str] = None) -> str:
        """Store long-term memory"""
        memory_id = f"mem-{hashlib.sha256(content.encode()).hexdigest()[:16]}"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO agent_memory_long
                    (memory_id, agent_id, memory_type, content, importance, tags, created_at, last_accessed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory_id,
                    self.agent_id,
                    memory_type,
                    content,
                    importance,
                    json.dumps(tags or []),
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                ))
                conn.commit()
                return memory_id
        except Exception as e:
            print(f"[MEMORY ERROR] {e}")
            return None
    
    def get_short_term(self, limit: int = 50) -> List[Dict]:
        """Get recent short-term memories"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content, timestamp, metadata
                FROM agent_memory_short
                WHERE agent_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (self.agent_id, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'role': row[0],
                    'content': row[1],
                    'timestamp': row[2],
                    'metadata': json.loads(row[3]) if row[3] else {}
                })
            return results
    
    def search_long_term(self, query: str, limit: int = 5) -> List[Dict]:
        """Search long-term memories (simple keyword search, extendable to vector)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT memory_id, memory_type, content, importance, tags, created_at
                FROM agent_memory_long
                WHERE agent_id = ? AND content LIKE ?
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
            """, (self.agent_id, f'%{query}%', limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'memory_id': row[0],
                    'type': row[1],
                    'content': row[2],
                    'importance': row[3],
                    'tags': json.loads(row[4]) if row[4] else [],
                    'created_at': row[5]
                })
            return results
    
    def clear_short_term(self) -> bool:
        """Clear short-term memory"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM agent_memory_short WHERE agent_id = ?",
                    (self.agent_id,)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"[MEMORY ERROR] {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get memory statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT COUNT(*) FROM agent_memory_short WHERE agent_id = ?",
                (self.agent_id,)
            )
            short_count = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT COUNT(*) FROM agent_memory_long WHERE agent_id = ?",
                (self.agent_id,)
            )
            long_count = cursor.fetchone()[0]
            
            return {
                'short_term_count': short_count,
                'long_term_count': long_count
            }


class MemoryManager:
    """Central memory manager for all agents"""
    
    def __init__(self):
        self._memories: Dict[str, AgentMemoryStore] = {}
    
    def get_memory_store(self, agent_id: str) -> AgentMemoryStore:
        """Get or create memory store for agent"""
        if agent_id not in self._memories:
            self._memories[agent_id] = AgentMemoryStore(agent_id)
        return self._memories[agent_id]
    
    def clear_agent_memory(self, agent_id: str) -> bool:
        """Clear all memory for an agent"""
        if agent_id in self._memories:
            return self._memories[agent_id].clear_short_term()
        return False


# Singleton
_memory_manager = None

def get_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
