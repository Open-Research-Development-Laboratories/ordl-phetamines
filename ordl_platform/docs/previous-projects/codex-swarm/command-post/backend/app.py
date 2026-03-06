#!/usr/bin/env python3
"""
ORDL Command Post v5.0.0 - Fully Integrated
Military-grade AI operations center
Classification: TOP SECRET//NOFORN//SCI
"""

import os
import sys
import json
import time
import uuid
import sqlite3
import psutil
import requests
import threading
import subprocess
import hashlib
import io
import contextlib
import asyncio
from datetime import datetime
from functools import wraps
from urllib.parse import quote

from flask import Flask, request, jsonify, Response, stream_with_context, send_from_directory, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Add parent directory to path
sys.path.insert(0, '/opt/codex-swarm/command-post')


# =============================================================================
# SECURITY MODULE IMPORTS
# =============================================================================
try:
    from security.clearance import (
        ClearanceLevel, ClearanceAttributes, get_acl, 
        ORDL_RESOURCES, AccessControlList
    )
    from security.audit.logger import (
        get_audit_logger, AuditEventType, AuditSeverity, AuditRecord
    )
    from security.session.manager import (
        get_session_manager, SessionManager, SessionStatus, Session
    )
    from security.mfa.totp import get_mfa_manager, MFAType, TOTPGenerator
    from security.decorators import (
        require_auth, require_clearance, require_mfa, require_session,
        audit_log, require_secret, require_top_secret, require_sci, require_noforn
    )
    SECURITY_AVAILABLE = True
    print("[SECURITY] USG-grade security system loaded")
except ImportError as e:
    print(f"[SECURITY WARNING] Security modules unavailable: {e}")
    SECURITY_AVAILABLE = False
    
    # Create stub decorators if security not available
    def require_auth(f):
        return f
    def require_clearance(level):
        def decorator(f):
            return f
        return decorator
    def require_mfa(f):
        return f
    def require_session(f):
        return f
    def audit_log(*args, **kwargs):
        def decorator(f):
            return f
        return decorator
    def require_secret(f):
        return f
    def require_top_secret(f):
        return f
    def require_sci(f):
        return f
    def require_noforn(f):
        return f

# =============================================================================
# CONFIGURATION
# =============================================================================
DATA_DIR = "/opt/codex-swarm/command-post/data"
UPLOADS_DIR = "/opt/codex-swarm/command-post/uploads"
MODELS_DIR = "/opt/codex-swarm/command-post/models"
STATIC_FOLDER = "/opt/codex-swarm/command-post/static"
DB_PATH = os.path.join(DATA_DIR, "nexus.db")

ROUTER_URL = os.environ.get('ROUTER_URL', 'http://localhost:18000')
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'ordl-secret-key-change-in-production')
NEXUS_TOKEN = os.environ.get('NEXUS_TOKEN', 'WINSOCK!IS!GOAT!ORDL3991!-3dc65a69fda7069b53e40ff05c9f5620')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)


# =============================================================================
# SECURITY INITIALIZATION
# =============================================================================
security_acl = None
audit_logger = None
session_manager = None
mfa_manager = None

if SECURITY_AVAILABLE:
    try:
        security_acl = get_acl()
        audit_logger = get_audit_logger()
        session_manager = get_session_manager()
        mfa_manager = get_mfa_manager()
        print("[SECURITY] All security components initialized")
    except Exception as e:
        print(f"[SECURITY ERROR] Failed to initialize: {e}")
        SECURITY_AVAILABLE = False

# =============================================================================
# RED TEAM INITIALIZATION
# =============================================================================
REDTEAM_AVAILABLE = False
redteam_manager = None

try:
    from redteam import get_redteam_manager
    from redteam.database import init_redteam_database
    from redteam.api import redteam_bp, init_redteam_api
    
    # Initialize Red Team database
    init_redteam_database()
    
    # Initialize Red Team manager with audit logger
    redteam_manager = get_redteam_manager(audit_logger)
    
    # Initialize Red Team API
    init_redteam_api(redteam_manager)
    
    REDTEAM_AVAILABLE = True
    print("[SECURITY] Red Team Operations module loaded")
except ImportError as e:
    print(f"[WARNING] Red Team module unavailable: {e}")
    REDTEAM_AVAILABLE = False

# =============================================================================
# FLASK APP SETUP
# =============================================================================
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='/static')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://www.ordl.org", "https://defend.ordl.org", "http://localhost:18010", "http://localhost:8080"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type", "X-Requested-With"],
        "supports_credentials": True
    },
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"]
    }
})

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per minute", "1000 per hour"]
)

# Register Red Team Blueprint
if REDTEAM_AVAILABLE:
    try:
        app.register_blueprint(redteam_bp)
        print("[SECURITY] Red Team API registered")
    except Exception as e:
        print(f"[WARNING] Failed to register Red Team API: {e}")


# =============================================================================
# REQUEST CONTEXT SETUP
# =============================================================================
@app.before_request
def setup_request_context():
    """Set up security context for each request"""
    g.user = None
    g.token = None
    g.session = None
    g.session_id = None
    g.start_time = time.time()

@app.after_request
def log_request(response):
    """Log request to audit system"""
    if audit_logger and hasattr(g, 'user') and g.user:
        duration_ms = int((time.time() - g.start_time) * 1000)
        
        # Determine event type based on response status
        if response.status_code >= 500:
            event_type = AuditEventType.SYSTEM_ERROR
            severity = AuditSeverity.ERROR
        elif response.status_code == 403:
            event_type = AuditEventType.ACCESS_DENIED
            severity = AuditSeverity.WARNING
        elif response.status_code == 401:
            event_type = AuditEventType.AUTHENTICATION_FAILURE
            severity = AuditSeverity.WARNING
        else:
            event_type = AuditEventType.DATA_READ
            severity = AuditSeverity.INFO
        
        # Create audit record
        try:
            audit_logger.create_record(
                event_type=event_type,
                user_codename=g.user.get('codename', 'unknown'),
                user_clearance=g.user.get('clearance', 'UNCLASSIFIED'),
                session_id=g.get('session_id', 'unknown'),
                resource_id=request.endpoint or 'unknown',
                action=request.method,
                status='SUCCESS' if response.status_code < 400 else 'FAILURE',
                severity=severity,
                source_ip=request.remote_addr or '127.0.0.1',
                source_host=request.host or 'localhost',
                result_code=response.status_code,
                bytes_transferred=response.content_length or 0
            )
        except Exception as e:
            print(f"[AUDIT ERROR] Failed to log: {e}")
    
    return response

# =============================================================================
# MODULE LOADING WITH FALLBACKS
# =============================================================================

# Auth Module
try:
    from auth.jwt_auth import get_auth_manager, Permission
    AUTH_AVAILABLE = True
    print("[OK] Auth module loaded")
except Exception as e:
    AUTH_AVAILABLE = False
    print(f"[WARN] Auth module unavailable: {e}")

# Sandbox Module
try:
    from sandbox.podman_sandbox import get_sandbox, Language
    SANDBOX_AVAILABLE = True
    print("[OK] Sandbox module loaded")
except Exception as e:
    SANDBOX_AVAILABLE = False
    print(f"[WARN] Sandbox module unavailable: {e}")

# Training Module
try:
    from training.unsloth_trainer import get_trainer
    TRAINING_AVAILABLE = True
    print("[OK] Training module loaded")
except Exception as e:
    TRAINING_AVAILABLE = False
    print(f"[WARN] Training module unavailable: {e}")

# RAG Module
try:
    from rag.vector_kb import get_knowledge_base
    RAG_AVAILABLE = True
    print("[OK] RAG module loaded")
except Exception as e:
    RAG_AVAILABLE = False
    print(f"[WARN] RAG module unavailable: {e}")

# Network Module
try:
    from network.packet_crafter import get_packet_crafter, get_network_control, get_traffic_shaper
    NETWORK_AVAILABLE = True
    print("[OK] Network module loaded")
except Exception as e:
    NETWORK_AVAILABLE = False
    print(f"[WARN] Network module unavailable: {e}")

# Search Module
try:
    from search.engine import get_search_engine
    SEARCH_AVAILABLE = True
    print("[OK] Search module loaded")
except Exception as e:
    SEARCH_AVAILABLE = False
    print(f"[WARN] Search module unavailable: {e}")

# MCP Module
try:
    from mcp.mcp_server import MCPServer, MCPTransport
    MCP_AVAILABLE = True
    print("[OK] MCP module loaded")
except Exception as e:
    MCP_AVAILABLE = False
    print(f"[WARN] MCP module unavailable: {e}")

# WebSocket Module
try:
    from websocket.server import get_websocket_server
    WEBSOCKET_AVAILABLE = True
    print("[OK] WebSocket module loaded")
except Exception as e:
    WEBSOCKET_AVAILABLE = False
    print(f"[WARN] WebSocket module unavailable: {e}")

# =============================================================================
# DATABASE SETUP
# =============================================================================
def init_database():
    """Initialize all database tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Core tables
    tables = [
        '''CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY, name TEXT, persona TEXT, model TEXT,
            clearance TEXT DEFAULT 'SECRET', status TEXT DEFAULT 'idle',
            created_at TEXT, tasks_completed INTEGER DEFAULT 0,
            capabilities TEXT, description TEXT, config TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS agent_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT,
            timestamp TEXT, action TEXT, details TEXT, operation_id TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS swarm_operations (
            id TEXT PRIMARY KEY, name TEXT, type TEXT, status TEXT,
            agents TEXT, objective TEXT, progress INTEGER,
            created_at TEXT, started_at TEXT, completed_at TEXT, results TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS training_jobs (
            id TEXT PRIMARY KEY, name TEXT, model TEXT, dataset TEXT,
            output_model TEXT, status TEXT, progress INTEGER,
            epochs TEXT, loss REAL, started_at TEXT, completed_at TEXT, config TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS custom_models (
            id TEXT PRIMARY KEY, name TEXT, base_model TEXT, trained_at TEXT,
            job_id TEXT, performance_metrics TEXT, deployment_status TEXT DEFAULT 'ready')''',
        
        '''CREATE TABLE IF NOT EXISTS research_tasks (
            id TEXT PRIMARY KEY, query TEXT, type TEXT, status TEXT,
            progress INTEGER, sources TEXT, findings TEXT, summary TEXT,
            created_at TEXT, completed_at TEXT, tags TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS file_uploads (
            id TEXT PRIMARY KEY, name TEXT, size INTEGER, type TEXT,
            uploaded_at TEXT, status TEXT, content_hash TEXT, analysis TEXT, file_path TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY, title TEXT, model TEXT,
            created_at TEXT, updated_at TEXT, messages TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS tools (
            id TEXT PRIMARY KEY, name TEXT, description TEXT, code TEXT,
            language TEXT, created_at TEXT, usage_count INTEGER DEFAULT 0, enabled BOOLEAN DEFAULT 1)''',
        
        '''CREATE TABLE IF NOT EXISTS mcp_servers (
            id TEXT PRIMARY KEY, name TEXT, endpoint TEXT, type TEXT,
            auth_token TEXT, status TEXT DEFAULT 'disconnected',
            capabilities TEXT, created_at TEXT, last_connected TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS network_captures (
            id TEXT PRIMARY KEY, interface TEXT, filter TEXT, status TEXT,
            packets INTEGER, started_at TEXT, stopped_at TEXT, data_path TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT,
            level TEXT, component TEXT, message TEXT, details TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS knowledge_base (
            id TEXT PRIMARY KEY, title TEXT, content TEXT, category TEXT,
            tags TEXT, source TEXT, created_at TEXT, updated_at TEXT, embedding_id TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS auth_users (
            id TEXT PRIMARY KEY, codename TEXT UNIQUE, password_hash TEXT,
            clearance TEXT DEFAULT 'UNCLASSIFIED', created_at TEXT, is_active BOOLEAN DEFAULT 1)''',
        
        '''CREATE TABLE IF NOT EXISTS refresh_tokens (
            token_hash TEXT PRIMARY KEY, user_id TEXT, created_at TEXT,
            expires_at TEXT, revoked BOOLEAN DEFAULT 0)''',
        
        '''CREATE TABLE IF NOT EXISTS kb_documents (
            id TEXT PRIMARY KEY, title TEXT, content TEXT, category TEXT,
            tags TEXT, source TEXT, created_at TEXT, chunk_count INTEGER DEFAULT 0)'''
    ]
    
    for table_sql in tables:
        cursor.execute(table_sql)
    
    conn.commit()
    conn.close()
    log_system_event('info', 'database', 'Database initialized successfully')

def get_db():
    """Get database connection for current request"""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Close database connection at end of request"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def log_system_event(level, component, message, details=None):
    """Log system events to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_events (timestamp, level, component, message, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.utcnow().isoformat(), level, component, message, 
              json.dumps(details) if details else None))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to log event: {e}")

# =============================================================================
# AUTHENTICATION
# =============================================================================
def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing authorization"}), 401
        
        token = auth_header.split(' ')[1]
        
        # Try JWT auth first
        if AUTH_AVAILABLE:
            auth_manager = get_auth_manager()
            valid, payload, msg = auth_manager.verify_token(token)
            if valid:
                g.user = payload
                return f(*args, **kwargs)
        
        # Fallback to legacy token
        if token == NEXUS_TOKEN:
            g.user = {'codename': 'LEGACY', 'clearance': 'TS/SCI/NOFORN'}
            return f(*args, **kwargs)
        
        return jsonify({"error": "Invalid token"}), 403
    return decorated

def require_clearance(min_clearance):
    """Decorator to require minimum clearance level"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            clearance_levels = ['UNCLASSIFIED', 'CONFIDENTIAL', 'SECRET', 'TOP SECRET', 'TS/SCI', 'TS/SCI/NOFORN']
            user_clearance = g.get('user', {}).get('clearance', 'UNCLASSIFIED')
            if clearance_levels.index(user_clearance) < clearance_levels.index(min_clearance):
                return jsonify({"error": "Insufficient clearance"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# =============================================================================
# AI GENERATION HELPERS
# =============================================================================
def generate_with_ai(prompt, model='llama-3.3-70b-versatile', system_prompt=None, temperature=0.7, max_tokens=4096):
    """Generate AI response via router"""
    try:
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        
        response = requests.post(
            f'{ROUTER_URL}/v1/responses',
            headers={'Authorization': f'Bearer {NEXUS_TOKEN}'},
            json={
                'model': model,
                'input': messages,
                'temperature': temperature,
                'max_tokens': max_tokens
            },
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'content': data.get('response', 'No response'),
                'model': data.get('model', model),
                'latency_ms': data.get('latency_ms'),
                'tokens_used': data.get('usage', {}).get('total_tokens', 0)
            }
        else:
            return {'success': False, 'error': f'Router error: {response.status_code}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def scrape_website(url):
    """Scrape a website and return structured data"""
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.encoding = response.encoding or 'utf-8'
        html = response.text
        
        import re
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE | re.DOTALL)
        title = re.sub(r'\s+', ' ', title_match.group(1).strip()) if title_match else 'No title'
        
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)', html, re.IGNORECASE)
        description = desc_match.group(1) if desc_match else 'No description'
        
        headings = re.findall(r'<h([1-3])[^>]*>([^<]+)</h\1>', html, re.IGNORECASE | re.DOTALL)
        headings = [re.sub(r'\s+', ' ', h[1].strip()) for h in headings[:10]]
        
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return {
            'url': url,
            'title': title,
            'description': description,
            'headings': headings,
            'word_count': len(text.split()),
            'content_preview': text[:1000],
            'scraped_at': datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {'url': url, 'error': str(e), 'scraped_at': datetime.utcnow().isoformat()}

# =============================================================================
# IN-MEMORY DATA STORES
# =============================================================================
agents_db = {}
agent_audit_logs = {}
swarm_operations = {}
network_captures = {}
research_tasks = {}
file_uploads = {}
conversations_db = {}
custom_models = []
tools_registry = {}
mcp_servers = {}
knowledge_base = {}
request_count = {'total': 0, 'per_minute': []}

# =============================================================================
# DATA LOADING
# =============================================================================
def load_data_from_db():
    """Load all data from database into memory"""
    global agents_db, agent_audit_logs, custom_models
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Load agents
        cursor.execute('SELECT * FROM agents')
        for row in cursor.fetchall():
            agents_db[row[0]] = {
                'id': row[0], 'name': row[1], 'persona': row[2], 'model': row[3],
                'clearance': row[4], 'status': row[5], 'created_at': row[6],
                'tasks_completed': row[7], 'capabilities': json.loads(row[8]) if row[8] else [],
                'description': row[9], 'config': json.loads(row[10]) if row[10] else {}
            }
        
        # Load audit logs
        cursor.execute('SELECT * FROM agent_audit_logs ORDER BY timestamp DESC')
        for row in cursor.fetchall():
            agent_id = row[1]
            if agent_id not in agent_audit_logs:
                agent_audit_logs[agent_id] = []
            agent_audit_logs[agent_id].append({
                'timestamp': row[2], 'action': row[3], 'details': row[4], 'operation_id': row[5]
            })
        
        # Load custom models
        cursor.execute('SELECT * FROM custom_models')
        for row in cursor.fetchall():
            custom_models.append({
                'id': row[0], 'name': row[1], 'base_model': row[2], 'trained_at': row[3],
                'job_id': row[4], 'performance_metrics': json.loads(row[5]) if row[5] else {},
                'deployment_status': row[6]
            })
        
        # Load tools
        cursor.execute('SELECT * FROM tools WHERE enabled=1')
        for row in cursor.fetchall():
            tools_registry[row[0]] = {
                'id': row[0], 'name': row[1], 'description': row[2],
                'code': row[3], 'language': row[4], 'created_at': row[5],
                'usage_count': row[6]
            }
        
        # Load MCP servers
        cursor.execute('SELECT * FROM mcp_servers')
        for row in cursor.fetchall():
            mcp_servers[row[0]] = {
                'id': row[0], 'name': row[1], 'endpoint': row[2], 'type': row[3],
                'auth_token': row[4], 'status': row[5],
                'capabilities': json.loads(row[6]) if row[6] else [],
                'created_at': row[7], 'last_connected': row[8]
            }
        
        # Load knowledge base
        cursor.execute('SELECT * FROM knowledge_base')
        for row in cursor.fetchall():
            knowledge_base[row[0]] = {
                'id': row[0], 'title': row[1], 'content': row[2],
                'category': row[3], 'tags': json.loads(row[4]) if row[4] else [],
                'source': row[5], 'created_at': row[6], 'updated_at': row[7],
                'embedding_id': row[8]
            }
        
        conn.close()
        
        # Create default agents if none
        if not agents_db:
            init_default_agents()
            
    except Exception as e:
        print(f"Error loading data: {e}")
        init_default_agents()

def init_default_agents():
    """Initialize default agents"""
    global agents_db, agent_audit_logs
    
    default_agents = [
        {
            'id': 'alpha-1', 'name': 'ALPHA-1', 'persona': 'System Architect',
            'model': 'llama-3.3-70b-versatile', 'clearance': 'TS/SCI/NOFORN',
            'status': 'active', 'created_at': datetime.utcnow().isoformat(),
            'tasks_completed': 47,
            'capabilities': ['architecture', 'design', 'planning', 'system_design'],
            'description': 'Designs system architecture and infrastructure.'
        },
        {
            'id': 'beta-3', 'name': 'BETA-3', 'persona': 'Security Engineer',
            'model': 'llama-3.1-8b-instant', 'clearance': 'TS/SCI',
            'status': 'idle', 'created_at': datetime.utcnow().isoformat(),
            'tasks_completed': 23,
            'capabilities': ['security', 'audit', 'hardening', 'vulnerability_scanning'],
            'description': 'Performs security audits and hardening.'
        },
        {
            'id': 'gamma-7', 'name': 'GAMMA-7', 'persona': 'Code Specialist',
            'model': 'llama-3.1-8b-instant', 'clearance': 'SECRET',
            'status': 'active', 'created_at': datetime.utcnow().isoformat(),
            'tasks_completed': 156,
            'capabilities': ['coding', 'debugging', 'refactoring', 'implementation'],
            'description': 'Writes and refactors code.'
        },
        {
            'id': 'omega-1', 'name': 'OMEGA-1', 'persona': 'Research Analyst',
            'model': 'llama-3.3-70b-versatile', 'clearance': 'TOP SECRET',
            'status': 'active', 'created_at': datetime.utcnow().isoformat(),
            'tasks_completed': 89,
            'capabilities': ['research', 'analysis', 'data_processing', 'reporting'],
            'description': 'Deep research and analysis specialist.'
        }
    ]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for agent in default_agents:
        agents_db[agent['id']] = agent
        agent_audit_logs[agent['id']] = [{
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'DEPLOYED',
            'details': f"Agent {agent['name']} initialized"
        }]
        
        cursor.execute('''
            INSERT OR REPLACE INTO agents (id, name, persona, model, clearance, status, 
                created_at, tasks_completed, capabilities, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (agent['id'], agent['name'], agent['persona'], agent['model'], 
              agent['clearance'], agent['status'], agent['created_at'],
              agent['tasks_completed'], json.dumps(agent['capabilities']), agent['description']))
        
        cursor.execute('''
            INSERT INTO agent_audit_logs (agent_id, timestamp, action, details)
            VALUES (?, ?, ?, ?)
        ''', (agent['id'], datetime.utcnow().isoformat(), 'DEPLOYED', 
              f"Agent {agent['name']} initialized"))
    
    conn.commit()
    conn.close()

# =============================================================================
# SECURITY HEADERS
# =============================================================================
@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; connect-src 'self' *; "
        "img-src 'self' data: blob:; media-src 'self'; frame-ancestors 'none';"
    )
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================
@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "version": "5.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "sandbox": SANDBOX_AVAILABLE,
            "training": TRAINING_AVAILABLE,
            "rag": RAG_AVAILABLE,
            "auth": AUTH_AVAILABLE,
            "network": NETWORK_AVAILABLE,
            "search": SEARCH_AVAILABLE,
            "mcp": MCP_AVAILABLE,
            "websocket": WEBSOCKET_AVAILABLE
        }
    })

@app.route('/api/system/capabilities')
@require_auth
def capabilities():
    return jsonify({
        "components": {
            "sandbox": {
                "available": SANDBOX_AVAILABLE,
                "languages": ["python", "c", "cpp", "java"] if SANDBOX_AVAILABLE else []
            },
            "training": {"available": TRAINING_AVAILABLE},
            "rag": {"available": RAG_AVAILABLE},
            "auth": {
                "available": AUTH_AVAILABLE,
                "clearance_levels": ["UNCLASSIFIED", "CONFIDENTIAL", "SECRET", "TOP SECRET", "TS/SCI", "TS/SCI/NOFORN"]
            },
            "network": {"available": NETWORK_AVAILABLE},
            "search": {"available": SEARCH_AVAILABLE}
        }
    })

@app.route('/api/system/status')
@require_auth
def system_status():
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_io = psutil.net_io_counters()
        
        interfaces = []
        for name, addrs in psutil.net_if_addrs().items():
            if name != 'lo':
                for addr in addrs:
                    if addr.family == 2:  # IPv4
                        interfaces.append({'name': name, 'address': addr.address})
        
        # Check router
        router_status = 'offline'
        router_latency = None
        try:
            start = time.time()
            r = requests.get(f'{ROUTER_URL}/health', timeout=3)
            router_latency = round((time.time() - start) * 1000, 2)
            router_status = 'online' if r.status_code == 200 else 'degraded'
        except:
            pass
        
        return jsonify({
            'status': 'operational' if router_status == 'online' else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '5.0.0',
            'metrics': {
                'cpu': {'percent': cpu, 'cores': psutil.cpu_count()},
                'memory': {
                    'percent': memory.percent,
                    'used_gb': round(memory.used / (1024**3), 2),
                    'total_gb': round(memory.total / (1024**3), 2)
                },
                'storage': {
                    'percent': disk.percent,
                    'free_gb': round(disk.free / (1024**3), 2)
                },
                'network': {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'interfaces': interfaces
                },
                'agents': {
                    'total': len(agents_db),
                    'active': sum(1 for a in agents_db.values() if a['status'] == 'active')
                }
            },
            'router': {'status': router_status, 'latency_ms': router_latency}
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/system/events')
@require_auth
def get_system_events():
    try:
        limit = request.args.get('limit', 100, type=int)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM system_events 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        events = []
        for row in cursor.fetchall():
            events.append({
                'id': row[0], 'timestamp': row[1], 'level': row[2],
                'component': row[3], 'message': row[4],
                'details': json.loads(row[5]) if row[5] else None
            })
        conn.close()
        return jsonify({'events': events, 'count': len(events)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    codename = data.get('codename', '')
    password = data.get('password', '')
    
    # Check for legacy token authentication (backward compatibility)
    if password == NEXUS_TOKEN:
        return jsonify({
            "success": True,
            "access_token": NEXUS_TOKEN,
            "refresh_token": NEXUS_TOKEN,
            "user": {"codename": codename or "OPERATOR", "clearance": "TS/SCI/NOFORN"}
        })
    
    # Try JWT authentication if available
    if AUTH_AVAILABLE:
        auth_manager = get_auth_manager()
        success, tokens, msg = auth_manager.authenticate(
            codename, 
            password,
            ip_address=request.remote_addr
        )
        
        if success:
            return jsonify({
                "success": True,
                "access_token": tokens.access_token,
                "refresh_token": tokens.refresh_token,
                "expires_in": tokens.access_expires_in,
                "user": {"codename": codename, "clearance": "SECRET"}
            })
    
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    return jsonify({"user": g.get('user', {})})

# =============================================================================
# AGENT ENDPOINTS
# =============================================================================
@app.route('/api/agents', methods=['GET'])
@require_auth
def list_agents():
    return jsonify({
        'agents': list(agents_db.values()),
        'count': len(agents_db),
        'active': sum(1 for a in agents_db.values() if a['status'] == 'active')
    })

@app.route('/api/agents', methods=['POST'])
@require_auth
def create_agent():
    data = request.get_json()
    agent_id = str(uuid.uuid4())[:8]
    
    agent = {
        'id': agent_id,
        'name': data.get('name', f'AGENT-{agent_id.upper()}'),
        'persona': data.get('persona', 'General Purpose'),
        'model': data.get('model', 'llama-3.3-70b-versatile'),
        'clearance': data.get('clearance', 'SECRET'),
        'status': 'active',
        'created_at': datetime.utcnow().isoformat(),
        'tasks_completed': 0,
        'capabilities': data.get('capabilities', []),
        'description': data.get('description', 'AI agent ready for tasks.'),
        'config': data.get('config', {})
    }
    
    agents_db[agent_id] = agent
    agent_audit_logs[agent_id] = []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO agents (id, name, persona, model, clearance, status, 
            created_at, tasks_completed, capabilities, description, config)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (agent['id'], agent['name'], agent['persona'], agent['model'], 
          agent['clearance'], agent['status'], agent['created_at'],
          agent['tasks_completed'], json.dumps(agent['capabilities']), 
          agent['description'], json.dumps(agent['config'])))
    
    cursor.execute('''
        INSERT INTO agent_audit_logs (agent_id, timestamp, action, details)
        VALUES (?, ?, ?, ?)
    ''', (agent_id, datetime.utcnow().isoformat(), 'CREATED',
          f"Agent {agent['name']} deployed"))
    
    conn.commit()
    conn.close()
    
    log_system_event('info', 'agents', f"Agent {agent['name']} created", {'agent_id': agent_id})
    return jsonify({'success': True, 'agent': agent}), 201

@app.route('/api/agents/<agent_id>', methods=['GET'])
@require_auth
def get_agent(agent_id):
    if agent_id not in agents_db:
        return jsonify({'error': 'Agent not found'}), 404
    
    agent = agents_db[agent_id].copy()
    agent['audit_log_count'] = len(agent_audit_logs.get(agent_id, []))
    agent['recent_logs'] = agent_audit_logs.get(agent_id, [])[:10]
    return jsonify(agent)

@app.route('/api/agents/<agent_id>', methods=['DELETE'])
@require_auth
def delete_agent(agent_id):
    if agent_id not in agents_db:
        return jsonify({'error': 'Agent not found'}), 404
    
    agent_name = agents_db[agent_id]['name']
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO agent_audit_logs (agent_id, timestamp, action, details)
        VALUES (?, ?, ?, ?)
    ''', (agent_id, datetime.utcnow().isoformat(), 'TERMINATED',
          f"Agent {agent_name} terminated"))
    cursor.execute('DELETE FROM agents WHERE id = ?', (agent_id,))
    conn.commit()
    conn.close()
    
    del agents_db[agent_id]
    if agent_id in agent_audit_logs:
        del agent_audit_logs[agent_id]
    
    return jsonify({'success': True})

@app.route('/api/agents/<agent_id>/control', methods=['POST'])
@require_auth
def control_agent(agent_id):
    if agent_id not in agents_db:
        return jsonify({'error': 'Agent not found'}), 404
    
    data = request.get_json()
    action = data.get('action')
    valid_actions = ['activate', 'deactivate', 'pause', 'resume']
    
    if action not in valid_actions:
        return jsonify({'error': f'Invalid action. Use: {valid_actions}'}), 400
    
    old_status = agents_db[agent_id]['status']
    
    if action == 'activate':
        agents_db[agent_id]['status'] = 'active'
    elif action == 'deactivate':
        agents_db[agent_id]['status'] = 'idle'
    elif action == 'pause':
        agents_db[agent_id]['status'] = 'paused'
    elif action == 'resume':
        agents_db[agent_id]['status'] = 'active'
    
    new_status = agents_db[agent_id]['status']
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE agents SET status = ? WHERE id = ?', (new_status, agent_id))
    cursor.execute('''
        INSERT INTO agent_audit_logs (agent_id, timestamp, action, details)
        VALUES (?, ?, ?, ?)
    ''', (agent_id, datetime.utcnow().isoformat(), action.upper(),
          f"Status: {old_status} -> {new_status}"))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'agent': agents_db[agent_id]})

# =============================================================================
# SWARM OPERATIONS
# =============================================================================
@app.route('/api/swarm/operations', methods=['GET'])
@require_auth
def list_swarm_operations():
    return jsonify({
        'operations': list(swarm_operations.values()),
        'count': len(swarm_operations),
        'running': sum(1 for op in swarm_operations.values() if op['status'] == 'running')
    })

@app.route('/api/swarm/operations', methods=['POST'])
@require_auth
def create_swarm_operation():
    data = request.get_json()
    op_id = f"swarm-{str(uuid.uuid4())[:8]}"
    
    operation = {
        'id': op_id,
        'name': data.get('name', 'Unnamed Operation'),
        'type': data.get('type', 'distributed'),
        'status': 'initializing',
        'agents': data.get('agents', []),
        'objective': data.get('objective', ''),
        'progress': 0,
        'created_at': datetime.utcnow().isoformat(),
        'started_at': None,
        'completed_at': None,
        'results': []
    }
    
    swarm_operations[op_id] = operation
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO swarm_operations (id, name, type, status, agents, objective, progress, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (op_id, operation['name'], operation['type'], operation['status'],
          json.dumps(operation['agents']), operation['objective'], 0, operation['created_at']))
    conn.commit()
    conn.close()
    
    def run_swarm():
        time.sleep(1)
        operation['status'] = 'running'
        operation['started_at'] = datetime.utcnow().isoformat()
        
        assigned_agents = [agents_db.get(aid) for aid in operation['agents'] if aid in agents_db]
        total = len(assigned_agents)
        
        for idx, agent in enumerate(assigned_agents):
            system_prompt = f"You are {agent['name']}, a {agent['persona']}."
            prompt = f"Task: {operation['objective']}\n\nProvide your expert analysis."
            
            result = generate_with_ai(prompt, agent['model'], system_prompt)
            
            operation['results'].append({
                'agent': agent['name'],
                'output': result['content'] if result['success'] else result['error'],
                'timestamp': datetime.utcnow().isoformat()
            })
            
            operation['progress'] = int(((idx + 1) / total) * 100)
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('UPDATE swarm_operations SET progress = ?, results = ? WHERE id = ?',
                          (operation['progress'], json.dumps(operation['results']), op_id))
            conn.commit()
            conn.close()
        
        operation['status'] = 'completed'
        operation['completed_at'] = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE swarm_operations SET status = ?, completed_at = ? WHERE id = ?',
                      ('completed', operation['completed_at'], op_id))
        conn.commit()
        conn.close()
    
    threading.Thread(target=run_swarm, daemon=True).start()
    return jsonify({'success': True, 'operation': operation}), 201

@app.route('/api/swarm/operations/<op_id>', methods=['GET'])
@require_auth
def get_swarm_operation(op_id):
    if op_id not in swarm_operations:
        return jsonify({'error': 'Operation not found'}), 404
    return jsonify(swarm_operations[op_id])

# =============================================================================
# TRAINING ENDPOINTS
# =============================================================================
@app.route('/api/training/hardware')
@require_auth
def training_hardware():
    if not TRAINING_AVAILABLE:
        return jsonify({"error": "Training not available"}), 503
    return jsonify(get_trainer().get_hardware_info())

@app.route('/api/training/jobs', methods=['GET'])
@require_auth
def list_training_jobs():
    if not TRAINING_AVAILABLE:
        return jsonify({"jobs": [], "count": 0}), 200
    return jsonify({
        "jobs": get_trainer().list_jobs(),
        "count": len(get_trainer().jobs)
    })

@app.route('/api/training/jobs', methods=['POST'])
@require_auth
def create_training_job():
    if not TRAINING_AVAILABLE:
        return jsonify({"error": "Training not available"}), 503
    
    data = request.get_json()
    job_id = f"train-{str(uuid.uuid4())[:8]}"
    
    config = {
        'job_id': job_id,
        'name': data.get('name', 'Training Job'),
        'base_model': data.get('model', 'llama-3.1-8b'),
        'output_model': f"custom-{data.get('name', 'model').lower().replace(' ', '-')}",
        'dataset_source': data.get('dataset_source', 'upload'),
        'dataset_path': data.get('dataset_path', ''),
        'max_steps': data.get('max_steps', 100)
    }
    
    trainer = get_trainer()
    job = trainer.create_job(config)
    trainer.start_training(job_id)
    
    return jsonify({"success": True, "job": job.to_dict()}), 201

@app.route('/api/training/jobs/<job_id>', methods=['GET'])
@require_auth
def get_training_job(job_id):
    if not TRAINING_AVAILABLE:
        return jsonify({"error": "Training not available"}), 503
    job = get_trainer().get_job(job_id)
    return jsonify(job) if job else (jsonify({"error": "Not found"}), 404)

@app.route('/api/training/jobs/<job_id>', methods=['DELETE'])
@require_auth
def stop_training_job(job_id):
    if not TRAINING_AVAILABLE:
        return jsonify({"error": "Training not available"}), 503
    success = get_trainer().stop_job(job_id)
    return jsonify({"success": success})

# =============================================================================
# SANDBOX ENDPOINTS
# =============================================================================
@app.route('/api/sandbox/execute', methods=['POST'])
@require_auth
def execute_sandbox():
    data = request.get_json()
    code = data.get('code', '')
    language = data.get('language', 'python')
    clearance = data.get('clearance', 'SECRET')
    
    if SANDBOX_AVAILABLE:
        sandbox = get_sandbox()
        if language == 'python':
            result = sandbox.execute_python(code, clearance, data.get('inputs'))
            return jsonify({
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "exit_code": result.exit_code,
                "execution_time_ms": result.execution_time_ms
            })
        else:
            return jsonify({"error": f"Language {language} requires podman setup"}), 400
    else:
        # Fallback to restricted execution
        return execute_restricted_python(code)

def execute_restricted_python(code):
    """Restricted Python execution fallback"""
    try:
        dangerous = ['import os', 'subprocess', 'eval(', 'exec(', 'open(', '__import__']
        for pattern in dangerous:
            if pattern in code:
                return jsonify({"error": f"Security violation: {pattern}"}), 403
        
        allowed_imports = ['math', 'random', 'datetime', 'json', 're', 'statistics']
        
        def safe_import(name, *args, **kwargs):
            if name not in allowed_imports:
                raise ImportError(f"Import of '{name}' not allowed")
            return __import__(name, *args, **kwargs)
        
        allowed_builtins = {
            'len': len, 'str': str, 'int': int, 'float': float,
            'list': list, 'dict': dict, 'range': range,
            'sum': sum, 'min': min, 'max': max,
            '__import__': safe_import
        }
        
        exec_globals = {'__builtins__': allowed_builtins}
        exec_locals = {}
        
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            exec(code, exec_globals, exec_locals)
        
        return jsonify({
            'success': True,
            'output': stdout_capture.getvalue(),
            'result': exec_locals.get('result')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sandbox/languages', methods=['GET'])
@require_auth
def list_sandbox_languages():
    languages = ['python']
    if SANDBOX_AVAILABLE:
        languages.extend(['c', 'cpp', 'java'])
    return jsonify({"languages": languages})

# =============================================================================
# RAG / KNOWLEDGE BASE ENDPOINTS
# =============================================================================
@app.route('/api/knowledge/ingest', methods=['POST'])
@require_auth
def knowledge_ingest():
    if not RAG_AVAILABLE:
        return jsonify({"error": "RAG not available"}), 503
    
    data = request.get_json()
    kb = get_knowledge_base()
    doc_id = kb.ingest_document(
        content=data.get('content', ''),
        title=data.get('title', 'Untitled'),
        category=data.get('category', 'general'),
        tags=data.get('tags', []),
        source=data.get('source', 'manual')
    )
    return jsonify({"success": True, "document_id": doc_id})

@app.route('/api/knowledge/query', methods=['POST'])
@require_auth
def knowledge_query():
    if not RAG_AVAILABLE:
        return jsonify({"error": "RAG not available"}), 503
    
    data = request.get_json()
    kb = get_knowledge_base()
    results = kb.query_with_answer(data.get('query', ''), top_k=data.get('top_k', 5))
    return jsonify(results)

@app.route('/api/knowledge', methods=['GET'])
@require_auth
def list_knowledge():
    return jsonify({
        'entries': list(knowledge_base.values()),
        'count': len(knowledge_base)
    })

@app.route('/api/knowledge', methods=['POST'])
@require_auth
def create_knowledge_entry():
    data = request.get_json()
    entry_id = f"kb-{str(uuid.uuid4())[:8]}"
    
    entry = {
        'id': entry_id,
        'title': data.get('title', 'Untitled'),
        'content': data.get('content', ''),
        'category': data.get('category', 'general'),
        'tags': data.get('tags', []),
        'source': data.get('source', 'manual'),
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }
    
    knowledge_base[entry_id] = entry
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO knowledge_base (id, title, content, category, tags, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (entry_id, entry['title'], entry['content'], entry['category'],
          json.dumps(entry['tags']), entry['source'], entry['created_at'], entry['updated_at']))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'entry': entry}), 201

@app.route('/api/knowledge/<entry_id>', methods=['DELETE'])
@require_auth
def delete_knowledge_entry(entry_id):
    if entry_id in knowledge_base:
        del knowledge_base[entry_id]
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM knowledge_base WHERE id = ?', (entry_id,))
        conn.commit()
        conn.close()
    return jsonify({'success': True})

# =============================================================================
# NETWORK ENDPOINTS
# =============================================================================
@app.route('/api/network/status', methods=['GET'])
@require_auth
def network_status():
    try:
        net_io = psutil.net_io_counters()
        connections = psutil.net_connections()
        
        interfaces = []
        for name, addrs in psutil.net_if_addrs().items():
            if name != 'lo':
                interface_data = {'name': name, 'addresses': []}
                for addr in addrs:
                    if addr.family == 2:  # IPv4
                        interface_data['addresses'].append({'type': 'ipv4', 'address': addr.address})
                interfaces.append(interface_data)
        
        return jsonify({
            'interfaces': interfaces,
            'traffic': {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            },
            'connections': {'total': len(connections)},
            'adapters': interfaces
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/network/adapters', methods=['GET'])
@require_auth
def network_adapters():
    if NETWORK_AVAILABLE:
        return jsonify({"adapters": get_network_control()._get_adapters()})
    
    # Fallback
    adapters = []
    try:
        result = subprocess.run(["ip", "-j", "addr", "show"], capture_output=True, text=True)
        if result.returncode == 0:
            interfaces = json.loads(result.stdout)
            for iface in interfaces:
                name = iface.get("ifname", "")
                if name == "lo":
                    continue
                ip_addr = ""
                for addr_info in iface.get("addr_info", []):
                    if addr_info.get("family") == "inet":
                        ip_addr = addr_info.get("local", "")
                        break
                adapters.append({"name": name, "ip": ip_addr, "up": iface.get("operstate") == "UP"})
    except:
        pass
    return jsonify({"adapters": adapters})

@app.route('/api/network/adapters/<interface>/kill', methods=['POST'])
@require_auth
def network_adapter_kill(interface):
    if NETWORK_AVAILABLE:
        return jsonify({"success": get_network_control().adapter_kill(interface)})
    return jsonify({"error": "Network module not available"}), 503

@app.route('/api/network/adapters/<interface>/revive', methods=['POST'])
@require_auth
def network_adapter_revive(interface):
    if NETWORK_AVAILABLE:
        return jsonify({"success": get_network_control().adapter_revive(interface)})
    return jsonify({"error": "Network module not available"}), 503

# =============================================================================
# SEARCH ENDPOINTS
# =============================================================================
@app.route('/api/search', methods=['POST'])
@require_auth
def search():
    if not SEARCH_AVAILABLE:
        # Fallback to basic scraping
        data = request.get_json()
        query = data.get('query', '')
        return jsonify({
            "query": query,
            "results": [{"title": f"Result for {query}", "url": "#", "snippet": "Search module not available"}],
            "scraped_pages": []
        })
    
    data = request.get_json()
    query = data.get('query', '')
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(get_search_engine().deep_search(query))
        loop.close()
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================================================
# CHAT ENDPOINTS
# =============================================================================
@app.route('/api/chat', methods=['POST'])
@require_auth
@limiter.limit("60 per minute")
def chat():
    request_count['total'] += 1
    request_count['per_minute'].append(time.time())
    
    data = request.get_json()
    model = data.get('model', 'llama-3.3-70b-versatile')
    messages = data.get('messages', [])
    stream = data.get('stream', False)
    
    if stream:
        return Response(
            stream_with_context(stream_chat(messages, model, data)),
            mimetype='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
        )
    
    try:
        response = requests.post(
            f'{ROUTER_URL}/v1/responses',
            headers={'Authorization': f'Bearer {NEXUS_TOKEN}'},
            json={
                'model': model,
                'input': messages,
                'temperature': data.get('temperature', 0.7),
                'max_tokens': data.get('max_tokens', 4096)
            },
            timeout=120
        )
        
        router_data = response.json()
        if 'response' in router_data:
            return jsonify({
                'choices': [{
                    'message': {'role': 'assistant', 'content': router_data['response']},
                    'finish_reason': 'stop'
                }],
                'model': router_data.get('model', model),
                'latency_ms': router_data.get('latency_ms'),
                'usage': router_data.get('usage', {})
            })
        return jsonify(router_data), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def stream_chat(messages, model, data):
    """Stream chat response"""
    try:
        response = requests.post(
            f'{ROUTER_URL}/v1/responses',
            headers={'Authorization': f'Bearer {NEXUS_TOKEN}'},
            json={
                'model': model,
                'input': messages,
                'temperature': data.get('temperature', 0.7),
                'max_tokens': data.get('max_tokens', 4096),
                'stream': True
            },
            timeout=120,
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                try:
                    decoded = line.decode('utf-8')
                    if decoded.startswith('data: '):
                        decoded = decoded[6:]
                    chunk = json.loads(decoded)
                    if 'response' in chunk:
                        yield f"data: {json.dumps({'content': chunk['response']})}\n\n"
                except:
                    pass
        yield f"data: {json.dumps({'done': True})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

# =============================================================================
# CONVERSATIONS ENDPOINTS
# =============================================================================
@app.route('/api/conversations', methods=['GET'])
@require_auth
def list_conversations():
    # Load from DB if needed
    if not conversations_db:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM conversations ORDER BY updated_at DESC')
            for row in cursor.fetchall():
                conversations_db[row[0]] = {
                    'id': row[0], 'title': row[1], 'created_at': row[2],
                    'updated_at': row[3], 'messages': json.loads(row[4]) if row[4] else []
                }
            conn.close()
        except:
            pass
    
    convs = sorted(conversations_db.values(), key=lambda x: x.get('updated_at', ''), reverse=True)
    return jsonify({'conversations': convs, 'count': len(convs)})

@app.route('/api/conversations', methods=['POST'])
@require_auth
def create_conversation():
    data = request.get_json()
    conv_id = f"conv-{str(uuid.uuid4())[:8]}"
    
    conversation = {
        'id': conv_id,
        'title': data.get('title', 'New Conversation'),
        'model': data.get('model', 'llama-3.3-70b-versatile'),
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'messages': []
    }
    
    conversations_db[conv_id] = conversation
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO conversations (id, title, created_at, updated_at, messages)
        VALUES (?, ?, ?, ?, ?)
    ''', (conv_id, conversation['title'], conversation['created_at'],
          conversation['updated_at'], '[]'))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'conversation': conversation}), 201

@app.route('/api/conversations/<conv_id>', methods=['DELETE'])
@require_auth
def delete_conversation(conv_id):
    if conv_id in conversations_db:
        del conversations_db[conv_id]
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM conversations WHERE id = ?', (conv_id,))
        conn.commit()
        conn.close()
    return jsonify({'success': True})

# =============================================================================
# RESEARCH ENDPOINTS
# =============================================================================
@app.route('/api/research/tasks', methods=['GET'])
@require_auth
def list_research_tasks():
    return jsonify({
        'tasks': list(research_tasks.values()),
        'count': len(research_tasks)
    })

@app.route('/api/research/tasks', methods=['POST'])
@require_auth
def create_research_task():
    data = request.get_json()
    task_id = f"research-{str(uuid.uuid4())[:8]}"
    
    task = {
        'id': task_id,
        'query': data.get('query', ''),
        'type': data.get('type', 'web_search'),
        'status': 'pending',
        'progress': 0,
        'sources': [],
        'findings': [],
        'summary': '',
        'created_at': datetime.utcnow().isoformat(),
        'completed_at': None
    }
    
    research_tasks[task_id] = task
    
    def run_research():
        time.sleep(1)
        task['status'] = 'researching'
        
        # Basic web scraping
        query = task['query']
        urls = [f'https://en.wikipedia.org/wiki/{query.replace(" ", "_")}']
        
        for url in urls:
            scraped = scrape_website(url)
            if 'error' not in scraped:
                task['sources'].append({
                    'url': scraped['url'],
                    'title': scraped['title'],
                    'relevance': 0.9
                })
                task['findings'].append(f"{scraped['title']}: {scraped['description'][:200]}")
        
        # Generate summary
        if task['findings']:
            prompt = f"Summarize research on '{query}':\n" + "\n".join(task['findings'])
            result = generate_with_ai(prompt, 'llama-3.3-70b-versatile')
            if result['success']:
                task['summary'] = result['content']
        
        task['status'] = 'completed'
        task['progress'] = 100
        task['completed_at'] = datetime.utcnow().isoformat()
    
    threading.Thread(target=run_research, daemon=True).start()
    return jsonify({'success': True, 'task': task}), 201

# =============================================================================
# FILES ENDPOINTS
# =============================================================================
@app.route('/api/files', methods=['GET'])
@require_auth
def list_files():
    return jsonify({
        'files': list(file_uploads.values()),
        'count': len(file_uploads)
    })

@app.route('/api/files/upload', methods=['POST'])
@require_auth
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    file_id = f"file-{str(uuid.uuid4())[:8]}"
    filename = file.filename
    file_path = os.path.join(UPLOADS_DIR, f"{file_id}_{filename}")
    
    file.save(file_path)
    
    file_info = {
        'id': file_id,
        'name': filename,
        'size': os.path.getsize(file_path),
        'type': file.content_type or 'application/octet-stream',
        'uploaded_at': datetime.utcnow().isoformat(),
        'status': 'uploaded',
        'file_path': file_path
    }
    
    file_uploads[file_id] = file_info
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO file_uploads (id, name, size, type, uploaded_at, status, file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (file_id, file_info['name'], file_info['size'], file_info['type'],
          file_info['uploaded_at'], file_info['status'], file_path))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'file': file_info}), 201

@app.route('/api/files/<file_id>/download', methods=['GET'])
@require_auth
def download_file(file_id):
    if file_id not in file_uploads:
        return jsonify({'error': 'File not found'}), 404
    
    file_info = file_uploads[file_id]
    file_path = file_info['file_path']
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found on disk'}), 404
    
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    
    return send_from_directory(directory, filename, as_attachment=True, 
                               download_name=file_info['name'])

# =============================================================================
# TOOLS ENDPOINTS
# =============================================================================
@app.route('/api/tools', methods=['GET'])
@require_auth
def list_tools():
    built_in = [
        {'id': 'web_search', 'name': 'Web Search', 'description': 'Search and scrape websites', 
         'icon': 'fas fa-search', 'type': 'built_in', 'enabled': True},
        {'id': 'code_execution', 'name': 'Code Execution', 'description': 'Execute code in sandbox',
         'icon': 'fas fa-code', 'type': 'built_in', 'enabled': SANDBOX_AVAILABLE},
        {'id': 'file_analysis', 'name': 'File Analysis', 'description': 'Analyze uploaded files',
         'icon': 'fas fa-file-alt', 'type': 'built_in', 'enabled': True},
        {'id': 'system_info', 'name': 'System Information', 'description': 'Get system metrics',
         'icon': 'fas fa-server', 'type': 'built_in', 'enabled': True}
    ]
    
    custom = [
        {'id': tid, 'name': t['name'], 'description': t['description'],
         'icon': 'fas fa-puzzle-piece', 'type': 'custom', 'enabled': True}
        for tid, t in tools_registry.items()
    ]
    
    return jsonify({'tools': built_in + custom, 'count': len(built_in) + len(custom)})

# =============================================================================
# MCP SERVERS ENDPOINTS
# =============================================================================
@app.route('/api/mcp/servers', methods=['GET'])
@require_auth
def list_mcp_servers():
    return jsonify({
        'servers': list(mcp_servers.values()),
        'count': len(mcp_servers),
        'connected': sum(1 for s in mcp_servers.values() if s['status'] == 'connected')
    })

@app.route('/api/mcp/servers', methods=['POST'])
@require_auth
def create_mcp_server():
    data = request.get_json()
    server_id = f"mcp-{str(uuid.uuid4())[:8]}"
    
    server = {
        'id': server_id,
        'name': data.get('name', 'MCP Server'),
        'endpoint': data.get('endpoint', ''),
        'type': data.get('type', 'stdio'),
        'auth_token': data.get('auth_token', ''),
        'status': 'disconnected',
        'capabilities': [],
        'created_at': datetime.utcnow().isoformat(),
        'last_connected': None
    }
    
    mcp_servers[server_id] = server
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO mcp_servers (id, name, endpoint, type, auth_token, status, capabilities, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (server_id, server['name'], server['endpoint'], server['type'],
          server['auth_token'], 'disconnected', '[]', server['created_at']))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'server': server}), 201

@app.route('/api/mcp/servers/<server_id>/connect', methods=['POST'])
@require_auth
def connect_mcp_server(server_id):
    if server_id not in mcp_servers:
        return jsonify({'error': 'Server not found'}), 404
    
    server = mcp_servers[server_id]
    
    # Simulate connection attempt
    if server['type'] == 'http':
        try:
            r = requests.get(f"{server['endpoint']}/health", timeout=5)
            if r.status_code == 200:
                server['status'] = 'connected'
                server['last_connected'] = datetime.utcnow().isoformat()
        except:
            server['status'] = 'error'
    else:
        server['status'] = 'connected'
        server['last_connected'] = datetime.utcnow().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE mcp_servers SET status = ?, last_connected = ? WHERE id = ?
    ''', (server['status'], server['last_connected'], server_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'server': server})

@app.route('/api/mcp/servers/<server_id>', methods=['DELETE'])
@require_auth
def delete_mcp_server(server_id):
    if server_id in mcp_servers:
        del mcp_servers[server_id]
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM mcp_servers WHERE id = ?', (server_id,))
        conn.commit()
        conn.close()
    return jsonify({'success': True})

# =============================================================================
# STATIC FILE SERVING
# =============================================================================
@app.route('/')
def index():
    return send_from_directory(STATIC_FOLDER, 'index.html')

@app.route('/lib/<path:filename>')
def serve_lib(filename):
    """Serve files from static/lib directory"""
    return send_from_directory(os.path.join(STATIC_FOLDER, 'lib'), filename)

@app.route('/font-fix.css')
def serve_font_fix():
    """Serve font-fix.css from static directory"""
    return send_from_directory(STATIC_FOLDER, 'font-fix.css')

# =============================================================================
# INITIALIZATION
# =============================================================================
init_database()
load_data_from_db()

# =============================================================================
# SECURITY ENDPOINTS
# =============================================================================

@app.route('/api/security/status', methods=['GET'])
@require_auth
def security_status():
    """Get security system status"""
    status = {
        "security_available": SECURITY_AVAILABLE,
        "version": "6.0.0",
        "classification": "TOP SECRET//NOFORN//SCI"
    }
    
    if SECURITY_AVAILABLE:
        if security_acl:
            status['acl'] = {
                "resources_defined": len(security_acl.resources)
            }
        
        if session_manager:
            stats = session_manager.get_stats()
            status['sessions'] = stats
        
        if audit_logger:
            status['audit'] = {
                "database_path": AUDIT_DB_PATH,
                "operational": True
            }
        
        if mfa_manager:
            status['mfa'] = {
                "operational": True
            }
    
    return jsonify(status)


@app.route('/api/auth/mfa/enroll', methods=['POST'])
@require_auth
def mfa_enroll():
    """Enroll TOTP MFA for user"""
    if not mfa_manager:
        return jsonify({"error": "MFA_NOT_AVAILABLE"}), 503
    
    user = g.get('user', {})
    codename = user.get('codename', 'unknown')
    
    try:
        result = mfa_manager.enroll_totp(codename, device_name="ORDL Terminal")
        return jsonify({
            "success": True,
            "device_id": result['device']['device_id'],
            "qr_code": result['qr_code_png'],
            "backup_codes": result['backup_codes'],
            "secret": result['secret']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/auth/mfa/verify', methods=['POST'])
@require_auth
def mfa_verify():
    """Verify MFA code"""
    if not mfa_manager:
        return jsonify({"error": "MFA_NOT_AVAILABLE"}), 503
    
    data = request.get_json()
    code = data.get('code', '').strip()
    
    if not code:
        return jsonify({"error": "CODE_REQUIRED"}), 400
    
    user = g.get('user', {})
    codename = user.get('codename', 'unknown')
    
    valid = False
    factor_type = None
    
    if mfa_manager.verify_totp(codename, code):
        valid = True
        factor_type = 'totp'
    elif mfa_manager.verify_backup_code(codename, code):
        valid = True
        factor_type = 'backup'
    
    if valid:
        return jsonify({"success": True, "factor": factor_type})
    else:
        return jsonify({"error": "INVALID_CODE"}), 401


@app.route('/api/sessions', methods=['GET'])
@require_auth
def list_sessions():
    """List active sessions for user"""
    user = g.get('user', {})
    codename = user.get('codename', 'unknown')
    
    if session_manager:
        sessions = session_manager.get_user_sessions(codename)
        return jsonify({
            "sessions": sessions,
            "count": len(sessions)
        })
    
    return jsonify({"sessions": [], "count": 0})


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
@require_auth
def terminate_session_endpoint(session_id):
    """Terminate a specific session"""
    user = g.get('user', {})
    codename = user.get('codename', 'unknown')
    
    if session_manager:
        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({"error": "SESSION_NOT_FOUND"}), 404
        
        if session.user_codename != codename and user.get('clearance') != 'TS/SCI/NOFORN':
            return jsonify({"error": "UNAUTHORIZED"}), 403
        
        session_manager.terminate_session(session_id, "USER_TERMINATED")
        return jsonify({"success": True})
    
    return jsonify({"error": "SESSION_MANAGER_UNAVAILABLE"}), 503


@app.route('/api/audit/logs', methods=['GET'])
@require_auth
def query_audit_logs():
    """Query audit logs (admin only)"""
    if not audit_logger:
        return jsonify({"error": "AUDIT_NOT_AVAILABLE"}), 503
    
    user = request.args.get('user')
    event_type = request.args.get('event_type')
    severity = request.args.get('severity')
    limit = request.args.get('limit', 1000, type=int)
    
    try:
        records = audit_logger.query(
            user_codename=user,
            event_type=event_type,
            severity=severity,
            limit=limit
        )
        
        return jsonify({
            "records": [r.to_dict() for r in records],
            "count": len(records)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/audit/integrity', methods=['GET'])
@require_auth
def verify_audit_integrity():
    """Verify audit log chain integrity"""
    if not audit_logger:
        return jsonify({"error": "AUDIT_NOT_AVAILABLE"}), 503
    
    valid, message = audit_logger.verify_integrity()
    
    return jsonify({
        "valid": valid,
        "message": message
    })
# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
if __name__ == '__main__':
    log_system_event('info', 'server', 'ORDL Command Post v5.0.0 starting')
    
    # Get port from environment or use default
    port = int(os.environ.get('API_PORT', 18010))
    
    # Verify router
    try:
        r = requests.get(f'{ROUTER_URL}/health', timeout=5)
        if r.status_code == 200:
            log_system_event('info', 'router', 'Router connection verified')
        else:
            log_system_event('warning', 'router', 'Router returned non-200 status')
    except Exception as e:
        log_system_event('error', 'router', f'Router connection failed: {str(e)}')
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║           ORDL COMMAND POST v5.0.0 - OPERATIONAL                 ║
║                                                                  ║
║  API:      http://0.0.0.0:{port}                                  ║
║  Health:   http://0.0.0.0:{port}/health                           ║
║  Static:   http://0.0.0.0:{port}/static/index.html                ║
║                                                                  ║
║  Components:                                                     ║
║    - Auth:        {'✅' if AUTH_AVAILABLE else '❌'}                                             ║
║    - Sandbox:     {'✅' if SANDBOX_AVAILABLE else '❌'}                                             ║
║    - Training:    {'✅' if TRAINING_AVAILABLE else '❌'}                                             ║
║    - RAG:         {'✅' if RAG_AVAILABLE else '❌'}                                             ║
║    - Network:     {'✅' if NETWORK_AVAILABLE else '❌'}                                             ║
║    - Search:      {'✅' if SEARCH_AVAILABLE else '❌'}                                             ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

