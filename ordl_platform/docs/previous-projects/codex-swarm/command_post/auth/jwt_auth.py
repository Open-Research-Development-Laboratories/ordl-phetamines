#!/usr/bin/env python3
"""ORDL JWT Authentication with RBAC"""
import os, jwt, hashlib, secrets, logging, sqlite3
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jwt_auth")

class Permission(Enum):
    CHAT_READ = "chat:read"
    CHAT_WRITE = "chat:write"
    AGENT_READ = "agent:read"
    AGENT_WRITE = "agent:write"
    SWARM_EXECUTE = "swarm:execute"
    TRAINING_READ = "training:read"
    TRAINING_EXECUTE = "training:execute"
    NETWORK_READ = "network:read"
    NETWORK_EXECUTE = "network:execute"
    PACKET_CRAFT = "network:packet_craft"
    ADMIN_READ = "admin:read"
    SYSTEM_ADMIN = "system:admin"

CLEARANCE_PERMISSIONS = {
    'UNCLASSIFIED': [Permission.CHAT_READ, Permission.CHAT_WRITE],
    'CONFIDENTIAL': [Permission.CHAT_READ, Permission.CHAT_WRITE, Permission.AGENT_READ],
    'SECRET': [Permission.CHAT_READ, Permission.CHAT_WRITE, Permission.AGENT_READ,
               Permission.AGENT_WRITE, Permission.SWARM_EXECUTE, Permission.TRAINING_READ],
    'TOP SECRET': [Permission.CHAT_READ, Permission.CHAT_WRITE, Permission.AGENT_READ,
                   Permission.AGENT_WRITE, Permission.SWARM_EXECUTE, Permission.TRAINING_READ,
                   Permission.TRAINING_EXECUTE, Permission.NETWORK_READ, Permission.NETWORK_EXECUTE],
    'TS/SCI': [Permission.CHAT_READ, Permission.CHAT_WRITE, Permission.AGENT_READ,
               Permission.AGENT_WRITE, Permission.SWARM_EXECUTE, Permission.TRAINING_READ,
               Permission.TRAINING_EXECUTE, Permission.NETWORK_READ, Permission.NETWORK_EXECUTE,
               Permission.PACKET_CRAFT, Permission.ADMIN_READ],
    'TS/SCI/NOFORN': list(Permission)
}

@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    access_expires_in: int
    refresh_expires_in: int
    token_type: str = "Bearer"

class JWTAuthManager:
    def __init__(self, db_path: str = "/opt/codex-swarm/command-post/data/nexus.db",
                 secret_key: Optional[str] = None):
        self.db_path = db_path
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
        self.access_token_lifetime = timedelta(minutes=15)
        self.refresh_token_lifetime = timedelta(days=7)
        self.token_blacklist: set = set()
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS auth_users (
            id TEXT PRIMARY KEY, codename TEXT UNIQUE, password_hash TEXT,
            clearance TEXT DEFAULT 'UNCLASSIFIED', created_at TEXT, is_active BOOLEAN DEFAULT 1)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS refresh_tokens (
            token_hash TEXT PRIMARY KEY, user_id TEXT, created_at TEXT, expires_at TEXT, revoked BOOLEAN DEFAULT 0)''')
        conn.commit()
        conn.close()
        self._create_default_admin()
    
    def _create_default_admin(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM auth_users')
        if cursor.fetchone()[0] == 0:
            admin_id = "admin-001"
            admin_password = secrets.token_urlsafe(16)
            password_hash = self._hash_password(admin_password)
            cursor.execute('''INSERT INTO auth_users (id, codename, password_hash, clearance, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?)''', (admin_id, "ADMIN", password_hash, "TS/SCI/NOFORN", datetime.utcnow().isoformat(), True))
            conn.commit()
            logger.warning(f"Created default admin. Password: {admin_password}")
        conn.close()
    
    def _hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        return f"{salt}${pwdhash}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        try:
            salt, stored_hash = password_hash.split('$')
            pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
            return pwdhash == stored_hash
        except:
            return False
    
    def authenticate(self, codename: str, password: str, mfa_code: Optional[str] = None,
                    ip_address: str = None) -> Tuple[bool, Optional[TokenPair], str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, codename, password_hash, clearance, is_active FROM auth_users WHERE codename = ?', (codename,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return False, None, "Invalid credentials"
        user_id, codename, password_hash, clearance, is_active = row
        if not is_active:
            return False, None, "Account disabled"
        if not self._verify_password(password, password_hash):
            return False, None, "Invalid credentials"
        token_pair = self._generate_tokens(user_id, codename, clearance)
        return True, token_pair, "Authentication successful"
    
    def _generate_tokens(self, user_id: str, codename: str, clearance: str) -> TokenPair:
        now = datetime.utcnow()
        access_payload = {"sub": user_id, "codename": codename, "clearance": clearance,
                         "iat": now, "exp": now + self.access_token_lifetime, "type": "access"}
        access_token = jwt.encode(access_payload, self.secret_key, algorithm="HS256")
        refresh_payload = {"sub": user_id, "iat": now, "exp": now + self.refresh_token_lifetime, "type": "refresh"}
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm="HS256")
        return TokenPair(access_token=access_token, refresh_token=refresh_token,
                        access_expires_in=int(self.access_token_lifetime.total_seconds()),
                        refresh_expires_in=int(self.refresh_token_lifetime.total_seconds()))
    
    def verify_token(self, token: str) -> Tuple[bool, Optional[Dict], str]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            if payload.get("type") != "access":
                return False, None, "Invalid token type"
            return True, payload, "Valid token"
        except jwt.ExpiredSignatureError:
            return False, None, "Token expired"
        except jwt.InvalidTokenError:
            return False, None, "Invalid token"
    
    def has_permission(self, clearance: str, permission: Permission) -> bool:
        permissions = CLEARANCE_PERMISSIONS.get(clearance, [])
        return permission in permissions

_auth_manager = None
def get_auth_manager():
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = JWTAuthManager()
    return _auth_manager
