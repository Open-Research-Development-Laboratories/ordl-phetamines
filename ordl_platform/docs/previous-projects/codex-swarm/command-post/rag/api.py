#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - RAG REST API
================================================================================
Classification: TOP SECRET//SCI//NOFORN

RAG (Retrieval-Augmented Generation) REST API Endpoints
================================================================================
"""

import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from functools import wraps

from . import get_knowledge_base

logger = logging.getLogger('rag.api')

# Blueprint
rag_bp = Blueprint('rag', __name__, url_prefix='/api/rag')

# Global KB instance
kb = None

def init_rag_api(knowledge_base):
    """Initialize API with KB instance"""
    global kb
    kb = knowledge_base
    logger.info("[RAG] API initialized")

# ==================== DOCUMENT MANAGEMENT ====================

@rag_bp.route('/documents', methods=['GET'])
def list_documents():
    """List documents with optional filtering"""
    try:
        category = request.args.get('category')
        limit = request.args.get('limit', 100, type=int)
        
        docs = kb.list_documents(category=category, limit=limit)
        
        return jsonify({
            "status": "success",
            "count": len(docs),
            "documents": [doc.to_dict() for doc in docs],
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"List documents error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@rag_bp.route('/documents', methods=['POST'])
def ingest_document():
    """Ingest a new document"""
    try:
        data = request.get_json()
        
        if not data or 'content' not in data or 'title' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required fields: content, title"
            }), 400
        
        doc_id = kb.ingest_document(
            content=data['content'],
            title=data['title'],
            category=data.get('category', 'general'),
            tags=data.get('tags', []),
            source=data.get('source', 'api')
        )
        
        return jsonify({
            "status": "success",
            "document_id": doc_id,
            "message": "Document ingested successfully",
            "timestamp": datetime.utcnow().isoformat()
        }), 201
    except Exception as e:
        logger.error(f"Ingest document error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@rag_bp.route('/documents/<doc_id>', methods=['GET'])
def get_document(doc_id):
    """Get specific document"""
    try:
        doc = kb.get_document(doc_id)
        if not doc:
            return jsonify({
                "status": "error",
                "message": "Document not found"
            }), 404
        
        return jsonify({
            "status": "success",
            "document": doc.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Get document error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@rag_bp.route('/documents/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """Delete a document"""
    try:
        if kb.delete_document(doc_id):
            return jsonify({
                "status": "success",
                "message": f"Document {doc_id} deleted",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Document not found"
            }), 404
    except Exception as e:
        logger.error(f"Delete document error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== SEARCH ====================

@rag_bp.route('/search', methods=['POST'])
def search():
    """Semantic search"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required field: query"
            }), 400
        
        query = data['query']
        top_k = data.get('top_k', 5)
        category = data.get('category')
        
        results = kb.query(query, top_k=top_k, category=category)
        
        return jsonify({
            "status": "success",
            "query": query,
            "count": len(results),
            "results": [r.to_dict() for r in results],
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@rag_bp.route('/query', methods=['POST'])
def query_with_context():
    """Query with full context for LLM"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required field: query"
            }), 400
        
        result = kb.query_with_context(
            query=data['query'],
            top_k=data.get('top_k', 5)
        )
        
        return jsonify({
            "status": "success",
            **result,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Query with context error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== STATS & HEALTH ====================

@rag_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get knowledge base statistics"""
    try:
        stats = kb.get_stats()
        return jsonify({
            "status": "success",
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@rag_bp.route('/history', methods=['GET'])
def search_history():
    """Get search history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        history = kb.search_history(limit=limit)
        return jsonify({
            "status": "success",
            "count": len(history),
            "history": history,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Search history error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@rag_bp.route('/health', methods=['GET'])
def health_check():
    """RAG system health check"""
    try:
        if kb and kb.vector_store:
            stats = kb.get_stats()
            return jsonify({
                "status": "healthy",
                "module": "rag",
                "store_type": kb.store_type,
                "embedding_model": stats.get('embedding_model'),
                "total_documents": stats.get('total_documents'),
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Knowledge base not initialized"
            }), 503
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== BATCH OPERATIONS ====================

@rag_bp.route('/batch/ingest', methods=['POST'])
def batch_ingest():
    """Ingest multiple documents"""
    try:
        data = request.get_json()
        documents = data.get('documents', [])
        
        if not isinstance(documents, list):
            return jsonify({
                "status": "error",
                "message": "'documents' must be an array"
            }), 400
        
        results = []
        for doc in documents:
            try:
                doc_id = kb.ingest_document(
                    content=doc.get('content', ''),
                    title=doc.get('title', 'Untitled'),
                    category=doc.get('category', 'general'),
                    tags=doc.get('tags', []),
                    source=doc.get('source', 'batch_api')
                )
                results.append({"status": "success", "document_id": doc_id})
            except Exception as e:
                results.append({"status": "error", "message": str(e)})
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        
        return jsonify({
            "status": "success",
            "processed": len(results),
            "successful": success_count,
            "failed": len(results) - success_count,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Batch ingest error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
