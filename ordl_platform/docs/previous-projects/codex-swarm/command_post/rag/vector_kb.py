#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - VECTOR KNOWLEDGE BASE (RAG)
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Classification Level: TS/SCI/NOFORN

MILITARY-GRADE RETRIEVAL-AUGMENTED GENERATION SYSTEM
================================================================================
Enterprise vector database with ChromaDB + SQLite hybrid architecture.
Provides semantic search, document ingestion, and knowledge retrieval.

Features:
- Multi-backend support (ChromaDB primary, SQLite fallback)
- Sentence-transformer embeddings (local, no API dependency)
- Document chunking with overlap
- Metadata-rich storage
- Full CRUD operations
- Real-time indexing

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

import os
import sys
import json
import re
import sqlite3
import hashlib
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import threading
import pickle
import gc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("vector_kb")

@dataclass
class SearchResult:
    """Search result with full provenance"""
    document_id: str
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "content": self.content,
            "score": round(self.score, 6),
            "metadata": self.metadata
        }

@dataclass
class Document:
    """Document with full metadata"""
    id: str
    title: str
    content: str
    category: str
    tags: List[str]
    source: str
    created_at: str
    updated_at: str
    chunk_count: int
    embedding_model: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "tags": self.tags,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "chunk_count": self.chunk_count,
            "embedding_model": self.embedding_model
        }

class TextChunker:
    """
    Military-grade text chunking with semantic preservation
    
    Strategies:
    - Paragraph-aware splitting
    - Sentence boundary preservation
    - Configurable overlap for context continuity
    - Token-aware chunking (approximate)
    """
    
    def __init__(self, 
                 chunk_size: int = 512, 
                 chunk_overlap: int = 50,
                 respect_paragraphs: bool = True):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.respect_paragraphs = respect_paragraphs
        
    def chunk_text(self, text: str) -> List[str]:
        """Chunk text with intelligent boundary detection"""
        if not text or not text.strip():
            return []
        
        # Normalize whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        if self.respect_paragraphs:
            paragraphs = re.split(r'\n\s*\n', text)
        else:
            paragraphs = [text]
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            if current_size + para_size <= self.chunk_size:
                current_chunk.append(para)
                current_size += para_size
            else:
                # Save current chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                
                # Handle paragraph larger than chunk_size
                if para_size > self.chunk_size:
                    # Split by sentences
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    current_chunk = []
                    current_size = 0
                    
                    for sent in sentences:
                        sent_size = len(sent)
                        if current_size + sent_size <= self.chunk_size:
                            current_chunk.append(sent)
                            current_size += sent_size
                        else:
                            if current_chunk:
                                chunks.append(' '.join(current_chunk))
                            current_chunk = [sent]
                            current_size = sent_size
                    
                    if current_chunk:
                        chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                else:
                    current_chunk = [para]
                    current_size = para_size
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        # Add overlap
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks)
        
        return chunks
    
    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """Add overlapping content between chunks"""
        overlapped = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped.append(chunk)
            else:
                # Get overlap from previous chunk
                prev_chunk = chunks[i - 1]
                overlap_text = prev_chunk[-self.chunk_overlap:]
                overlapped.append(overlap_text + "\n\n" + chunk)
        return overlapped

class EmbeddingEngine:
    """
    Local embedding engine using sentence-transformers
    No external API dependencies - completely air-gapped capable
    """
    
    DEFAULT_MODEL = 'all-MiniLM-L6-v2'
    ALTERNATIVE_MODELS = [
        'all-MiniLM-L6-v2',      # Fast, good quality (default)
        'all-mpnet-base-v2',     # Higher quality, slower
        'paraphrase-MiniLM-L3-v2', # Ultra-fast
    ]
    
    def __init__(self, model_name: str = None, device: str = None):
        self.model_name = model_name or self.DEFAULT_MODEL
        self.device = device or ('cuda' if self._check_cuda() else 'cpu')
        self.model = None
        self.embedding_dim = None
        self._lock = threading.RLock()
        self._initialize()
    
    def _check_cuda(self) -> bool:
        """Check if CUDA is available"""
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False
    
    def _initialize(self):
        """Initialize the embedding model"""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"[RAG] Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"[RAG] Model loaded. Dimension: {self.embedding_dim}, Device: {self.device}")
        except ImportError:
            logger.error("[RAG] sentence-transformers not installed. Run: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"[RAG] Failed to load model: {e}")
            raise
    
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """Encode text(s) to embeddings"""
        with self._lock:
            if isinstance(texts, str):
                texts = [texts]
            
            try:
                embeddings = self.model.encode(
                    texts, 
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True
                )
                return embeddings
            except Exception as e:
                logger.error(f"[RAG] Encoding error: {e}")
                raise
    
    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text"""
        return self.encode([text])[0]
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.embedding_dim
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between embeddings"""
        return float(np.dot(embedding1, embedding2) / 
                    (np.linalg.norm(embedding1) * np.linalg.norm(embedding2)))

class SQLiteVectorStore:
    """
    SQLite-based vector storage with cosine similarity search
    Fallback when ChromaDB is unavailable
    """
    
    def __init__(self, db_path: str, embedding_dim: int):
        self.db_path = db_path
        self.embedding_dim = embedding_dim
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Enable JSON support
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Vector embeddings table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS vector_embeddings (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vec_doc_id 
                ON vector_embeddings(document_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vec_created 
                ON vector_embeddings(created_at)
            """)
            
            conn.commit()
    
    def add_embeddings(self, 
                       ids: List[str],
                       document_ids: List[str],
                       chunk_indices: List[int],
                       contents: List[str],
                       embeddings: np.ndarray,
                       metadatas: List[Dict]):
        """Add embeddings to store"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            timestamp = datetime.utcnow().isoformat()
            
            for i, emb_id in enumerate(ids):
                embedding_blob = pickle.dumps(embeddings[i].astype(np.float32))
                cursor.execute("""
                    INSERT OR REPLACE INTO vector_embeddings 
                    (id, document_id, chunk_index, content, embedding, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    emb_id,
                    document_ids[i],
                    chunk_indices[i],
                    contents[i],
                    embedding_blob,
                    json.dumps(metadatas[i]),
                    timestamp
                ))
            
            conn.commit()
    
    def search(self, 
               query_embedding: np.ndarray,
               top_k: int = 5) -> List[Tuple[str, str, str, float, Dict]]:
        """Search for similar vectors using cosine similarity"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Fetch all embeddings (for small-medium datasets)
            cursor.execute("""
                SELECT id, document_id, content, embedding, metadata 
                FROM vector_embeddings
            """)
            
            results = []
            query_norm = np.linalg.norm(query_embedding)
            
            for row in cursor.fetchall():
                emb_id, doc_id, content, embedding_blob, metadata_json = row
                embedding = pickle.loads(embedding_blob)
                
                # Cosine similarity
                dot_product = np.dot(query_embedding, embedding)
                emb_norm = np.linalg.norm(embedding)
                similarity = dot_product / (query_norm * emb_norm)
                
                results.append((
                    emb_id, doc_id, content, float(similarity),
                    json.loads(metadata_json) if metadata_json else {}
                ))
            
            # Sort by similarity descending
            results.sort(key=lambda x: x[3], reverse=True)
            return results[:top_k]
    
    def delete_by_document(self, document_id: str):
        """Delete all embeddings for a document"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM vector_embeddings WHERE document_id = ?",
                (document_id,)
            )
            conn.commit()
            return cursor.rowcount
    
    def count(self) -> int:
        """Get total embedding count"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM vector_embeddings")
            return cursor.fetchone()[0]

class ChromaDBStore:
    """
    ChromaDB vector store wrapper
    Primary storage when available
    """
    
    def __init__(self, chroma_path: str, embedding_engine: EmbeddingEngine):
        self.chroma_path = chroma_path
        self.embedding_engine = embedding_engine
        self.client = None
        self.collection = None
        self._initialize()
    
    def _initialize(self):
        """Initialize ChromaDB client"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Configure with optimized settings
            settings = Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True
            )
            
            self.client = chromadb.PersistentClient(
                path=self.chroma_path,
                settings=settings
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="ordl_knowledge",
                metadata={
                    "description": "ORDL Command Post Knowledge Base",
                    "embedding_model": self.embedding_engine.model_name,
                    "created": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"[RAG] ChromaDB initialized at {self.chroma_path}")
            
        except ImportError:
            logger.warning("[RAG] ChromaDB not available")
            raise
        except Exception as e:
            logger.error(f"[RAG] ChromaDB initialization failed: {e}")
            raise
    
    def add_embeddings(self,
                       ids: List[str],
                       document_ids: List[str],
                       chunk_indices: List[int],
                       contents: List[str],
                       embeddings: np.ndarray,
                       metadatas: List[Dict]):
        """Add embeddings to ChromaDB"""
        # ChromaDB stores embeddings as lists
        embedding_lists = embeddings.tolist()
        
        self.collection.add(
            ids=ids,
            embeddings=embedding_lists,
            documents=contents,
            metadatas=metadatas
        )
    
    def search(self, 
               query_embedding: np.ndarray,
               top_k: int = 5) -> List[Tuple[str, str, str, float, Dict]]:
        """Search ChromaDB collection"""
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        output = []
        if results and results['ids'] and results['ids'][0]:
            for i, chunk_id in enumerate(results['ids'][0]):
                distance = results['distances'][0][i]
                # Convert distance to similarity (ChromaDB uses cosine distance)
                similarity = 1 - distance
                metadata = results['metadatas'][0][i]
                content = results['documents'][0][i]
                doc_id = metadata.get('document_id', 'unknown')
                
                output.append((chunk_id, doc_id, content, similarity, metadata))
        
        return output
    
    def delete_by_document(self, document_id: str) -> int:
        """Delete embeddings by document ID"""
        # ChromaDB doesn't support direct metadata filtering for deletion
        # So we need to query first, then delete
        try:
            results = self.collection.get(
                where={"document_id": document_id}
            )
            if results and results['ids']:
                self.collection.delete(ids=results['ids'])
                return len(results['ids'])
        except Exception as e:
            logger.error(f"[RAG] ChromaDB delete error: {e}")
        return 0
    
    def count(self) -> int:
        """Get collection count"""
        return self.collection.count()
    
    def reset(self):
        """Reset entire collection (DANGER)"""
        self.client.reset()
        self._initialize()

class VectorKnowledgeBase:
    """
    Military-grade Vector Knowledge Base
    
    Hybrid architecture:
    - ChromaDB (primary, when available)
    - SQLite + numpy (fallback, always works)
    
    Provides semantic search, document management, and knowledge retrieval
    with enterprise-grade reliability.
    """
    
    def __init__(self,
                 db_path: str = "/opt/codex-swarm/command-post/data/nexus.db",
                 chroma_path: str = "/opt/codex-swarm/command-post/data/chromadb",
                 embedding_model: str = None,
                 chunk_size: int = 512,
                 chunk_overlap: int = 50):
        
        self.db_path = db_path
        self.chroma_path = chroma_path
        self.embedding_model_name = embedding_model
        
        # Initialize components
        self.chunker = TextChunker(chunk_size, chunk_overlap)
        self.embedding_engine: Optional[EmbeddingEngine] = None
        self.vector_store = None
        self.store_type: str = "none"
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize
        self._init_sqlite()
        self._init_embeddings()
        self._init_vector_store()
    
    def _init_sqlite(self):
        """Initialize SQLite document store"""
        os.makedirs(os.path.dirname(self.db_path) or '.', exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kb_documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    tags TEXT,
                    source TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    chunk_count INTEGER DEFAULT 0,
                    embedding_model TEXT,
                    content_hash TEXT
                )
            """)
            
            # Search history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    results_count INTEGER,
                    top_score REAL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            # Indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_kb_category 
                ON kb_documents(category)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_kb_created 
                ON kb_documents(created_at)
            """)
            
            conn.commit()
        
        logger.info(f"[RAG] SQLite store initialized: {self.db_path}")
    
    def _init_embeddings(self):
        """Initialize embedding engine"""
        try:
            self.embedding_engine = EmbeddingEngine(self.embedding_model_name)
        except Exception as e:
            logger.error(f"[RAG] Embedding engine failed: {e}")
            raise
    
    def _init_vector_store(self):
        """Initialize vector store with fallback"""
        # Try ChromaDB first
        try:
            self.vector_store = ChromaDBStore(
                self.chroma_path,
                self.embedding_engine
            )
            self.store_type = "chromadb"
            logger.info("[RAG] Using ChromaDB vector store")
            return
        except Exception as e:
            logger.warning(f"[RAG] ChromaDB unavailable: {e}")
        
        # Fall back to SQLite
        try:
            sqlite_path = self.db_path.replace('.db', '_vectors.db')
            self.vector_store = SQLiteVectorStore(
                sqlite_path,
                self.embedding_engine.get_dimension()
            )
            self.store_type = "sqlite"
            logger.info(f"[RAG] Using SQLite vector store: {sqlite_path}")
        except Exception as e:
            logger.error(f"[RAG] SQLite vector store failed: {e}")
            raise
    
    def ingest_document(self,
                        content: str,
                        title: str,
                        category: str = "general",
                        tags: List[str] = None,
                        source: str = "manual") -> str:
        """
        Ingest a document into the knowledge base
        
        Args:
            content: Document text content
            title: Document title
            category: Document category
            tags: List of tags
            source: Source identifier
            
        Returns:
            Document ID
        """
        with self._lock:
            # Generate document ID
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            doc_id = f"doc-{content_hash[:16]}"
            
            timestamp = datetime.utcnow().isoformat()
            
            # Chunk the document
            chunks = self.chunker.chunk_text(content)
            logger.info(f"[RAG] Ingesting '{title}' - {len(chunks)} chunks")
            
            if not chunks:
                logger.warning(f"[RAG] No chunks generated for: {title}")
                return doc_id
            
            # Generate embeddings
            try:
                embeddings = self.embedding_engine.encode(chunks)
            except Exception as e:
                logger.error(f"[RAG] Embedding generation failed: {e}")
                raise
            
            # Prepare data for vector store
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            document_ids = [doc_id] * len(chunks)
            chunk_indices = list(range(len(chunks)))
            metadatas = []
            for i in range(len(chunks)):
                metadatas.append({
                    "document_id": doc_id,
                    "chunk_index": i,
                    "title": title,
                    "category": category,
                    "source": source,
                    "created_at": timestamp,
                    "total_chunks": len(chunks)
                })
            
            # Store in vector database
            try:
                self.vector_store.add_embeddings(
                    ids=ids,
                    document_ids=document_ids,
                    chunk_indices=chunk_indices,
                    contents=chunks,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
            except Exception as e:
                logger.error(f"[RAG] Vector store error: {e}")
                raise
            
            # Store document metadata in SQLite
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO kb_documents
                    (id, title, content, category, tags, source, created_at, updated_at,
                     chunk_count, embedding_model, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id, title, content[:100000], category,
                    json.dumps(tags or []), source, timestamp, timestamp,
                    len(chunks), self.embedding_engine.model_name, content_hash
                ))
                conn.commit()
            
            logger.info(f"[RAG] Document ingested: {doc_id}")
            return doc_id
    
    def query(self, 
              query: str, 
              top_k: int = 5,
              category: str = None) -> List[SearchResult]:
        """
        Semantic search over knowledge base
        
        Args:
            query: Search query
            top_k: Number of results
            category: Optional category filter
            
        Returns:
            List of SearchResult objects
        """
        with self._lock:
            if not self.vector_store:
                logger.error("[RAG] Vector store not available")
                return []
            
            # Encode query
            try:
                query_embedding = self.embedding_engine.encode_single(query)
            except Exception as e:
                logger.error(f"[RAG] Query encoding failed: {e}")
                return []
            
            # Search
            try:
                raw_results = self.vector_store.search(query_embedding, top_k * 2)
            except Exception as e:
                logger.error(f"[RAG] Search failed: {e}")
                return []
            
            # Convert to SearchResult
            results = []
            for chunk_id, doc_id, content, score, metadata in raw_results:
                # Apply category filter if specified
                if category and metadata.get('category') != category:
                    continue
                
                results.append(SearchResult(
                    document_id=doc_id,
                    chunk_id=chunk_id,
                    content=content,
                    score=score,
                    metadata=metadata
                ))
            
            # Sort by score and limit
            results.sort(key=lambda x: x.score, reverse=True)
            results = results[:top_k]
            
            # Log search
            self._log_search(query, len(results), results[0].score if results else 0)
            
            return results
    
    def _log_search(self, query: str, count: int, top_score: float):
        """Log search to history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO search_history (query, results_count, top_score, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (query, count, top_score, datetime.utcnow().isoformat()))
                conn.commit()
        except Exception as e:
            logger.warning(f"[RAG] Failed to log search: {e}")
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM kb_documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return Document(
                id=row[0],
                title=row[1],
                content=row[2],
                category=row[3],
                tags=json.loads(row[4]) if row[4] else [],
                source=row[5],
                created_at=row[6],
                updated_at=row[7],
                chunk_count=row[8],
                embedding_model=row[9]
            )
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete document and its embeddings"""
        with self._lock:
            try:
                # Delete from vector store
                deleted_count = self.vector_store.delete_by_document(doc_id)
                
                # Delete from SQLite
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM kb_documents WHERE id = ?", (doc_id,))
                    conn.commit()
                    
                    if cursor.rowcount == 0 and deleted_count == 0:
                        return False
                
                logger.info(f"[RAG] Deleted document: {doc_id}")
                return True
            except Exception as e:
                logger.error(f"[RAG] Delete failed: {e}")
                return False
    
    def list_documents(self, 
                       category: str = None,
                       limit: int = 100) -> List[Document]:
        """List documents with optional filtering"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if category:
                cursor.execute("""
                    SELECT * FROM kb_documents 
                    WHERE category = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (category, limit))
            else:
                cursor.execute("""
                    SELECT * FROM kb_documents 
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            
            docs = []
            for row in cursor.fetchall():
                docs.append(Document(
                    id=row[0],
                    title=row[1],
                    content=row[2],
                    category=row[3],
                    tags=json.loads(row[4]) if row[4] else [],
                    source=row[5],
                    created_at=row[6],
                    updated_at=row[7],
                    chunk_count=row[8],
                    embedding_model=row[9]
                ))
            
            return docs
    
    def query_with_context(self, 
                           query: str, 
                           top_k: int = 5) -> Dict[str, Any]:
        """
        Query with full context for LLM consumption
        
        Returns structured result with context window
        """
        results = self.query(query, top_k)
        
        # Build context string
        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(f"[{i}] {r.metadata.get('title', 'Unknown')}\n{r.content}")
        
        context = "\n\n".join(context_parts)
        
        return {
            "query": query,
            "context": context,
            "sources": [r.to_dict() for r in results],
            "total_found": len(results),
            "store_type": self.store_type,
            "embedding_model": self.embedding_engine.model_name if self.embedding_engine else None
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Document counts
            cursor.execute("SELECT COUNT(*) FROM kb_documents")
            total_docs = cursor.fetchone()[0]
            
            # Category breakdown
            cursor.execute("""
                SELECT category, COUNT(*) 
                FROM kb_documents 
                GROUP BY category
            """)
            categories = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Recent searches
            cursor.execute("""
                SELECT COUNT(*), AVG(results_count) 
                FROM search_history 
                WHERE timestamp > datetime('now', '-24 hours')
            """)
            search_stats = cursor.fetchone()
        
        return {
            "total_documents": total_docs,
            "total_chunks": self.vector_store.count() if self.vector_store else 0,
            "categories": categories,
            "store_type": self.store_type,
            "embedding_model": self.embedding_engine.model_name if self.embedding_engine else None,
            "embedding_dimension": self.embedding_engine.get_dimension() if self.embedding_engine else 0,
            "searches_24h": search_stats[0] if search_stats else 0,
            "avg_results_per_search": round(search_stats[1], 2) if search_stats and search_stats[1] else 0
        }
    
    def search_history(self, limit: int = 50) -> List[Dict]:
        """Get recent search history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT query, results_count, top_score, timestamp
                FROM search_history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            return [
                {
                    "query": row[0],
                    "results": row[1],
                    "top_score": row[2],
                    "timestamp": row[3]
                }
                for row in cursor.fetchall()
            ]


# Singleton instance
_kb_instance = None

def get_knowledge_base(**kwargs) -> VectorKnowledgeBase:
    """Get or create knowledge base singleton"""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = VectorKnowledgeBase(**kwargs)
    return _kb_instance
