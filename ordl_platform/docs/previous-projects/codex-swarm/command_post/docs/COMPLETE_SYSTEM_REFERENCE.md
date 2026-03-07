# ORDL COMMAND POST v6.0.0 - COMPLETE SYSTEM REFERENCE
## Classification: TOP SECRET//SCI//NOFORN
## Document Version: 1.0.0 - Comprehensive Technical Documentation
## Generated: 2026-03-02T10:40:00Z

---

# TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Complete File Inventory](#3-complete-file-inventory)
4. [Core Backend System](#4-core-backend-system)
5. [Agent System](#5-agent-system)
6. [Security Infrastructure](#6-security-infrastructure)
7. [Red Team Operations](#7-red-team-operations)
8. [Blue Team Defense](#8-blue-team-defense)
9. [RAG Knowledge Base](#9-rag-knowledge-base)
10. [MCP Integration](#10-mcp-integration)
11. [LLM Provider System](#11-llm-provider-system)
12. [Training Pipeline](#12-training-pipeline)
13. [WebSocket Server](#13-websocket-server)
14. [Database Schemas](#14-database-schemas)
15. [API Endpoints](#15-api-endpoints)
16. [Configuration & Environment](#16-configuration--environment)
17. [Dependencies](#17-dependencies)
18. [Known Issues & TODOs](#18-known-issues--todos)
19. [Operational Procedures](#19-operational-procedures)

---

# 1. EXECUTIVE SUMMARY

## System Classification
- **Classification Level**: TOP SECRET//SCI//NOFORN
- **System Version**: 6.0.0
- **Deployment Status**: 76% Operational (Core Functions Active)
- **Clearance Required**: TS/SCI/NOFORN for full access

## System Purpose
The ORDL Command Post is a military-grade AI operations center providing:
- Multi-agent AI orchestration with LLM integration
- Red Team offensive security capabilities
- Blue Team defensive security operations
- Real-time RAG (Retrieval-Augmented Generation)
- Model fine-tuning and training pipelines
- MCP (Model Context Protocol) server integration
- WebSocket-based operator coordination
- Tamper-evident audit logging

## Operational Status
| Component | Status | Notes |
|-----------|--------|-------|
| Core Backend | ✅ OPERATIONAL | Flask server running on port 18010 |
| Agent System | ✅ OPERATIONAL | Agent creation, messaging, tool execution |
| Security System | ✅ OPERATIONAL | Clearance, sessions, MFA, audit |
| Red Team | ✅ OPERATIONAL | All 6 modules loaded |
| Blue Team | ✅ OPERATIONAL | 19 detection rules active |
| RAG System | ✅ OPERATIONAL | SQLiteVectorStore fallback (ChromaDB blocked) |
| LLM Bridge | ✅ OPERATIONAL | Ollama provider active |
| MCP Integration | ⚠️ PARTIAL | Client ready, servers not installed |
| Training Pipeline | ⚠️ PARTIAL | CPU fallback (unsloth/trl not installed) |
| WebSocket Server | ✅ OPERATIONAL | Port 18011, real-time chat |

---

# 2. SYSTEM ARCHITECTURE OVERVIEW

## 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORDL COMMAND POST v6.0.0                             │
│                    TOP SECRET//SCI//NOFORN                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   FRONTEND   │  │   AGENTS     │  │  SECURITY    │  │   AUDIT      │    │
│  │  (HTML/JS)   │  │   SYSTEM     │  │   LAYER      │  │   CHAIN      │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │            │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐    │
│  │   FLASK      │  │   AGENT      │  │   SESSION    │  │   TAMPER     │    │
│  │   SERVER     │  │   MANAGER    │  │   MANAGER    │  │   EVIDENT    │    │
│  │  (Port 18010)│  │              │  │              │  │   LOGGING    │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │            │
│  ┌──────▼─────────────────▼─────────────────▼─────────────────▼───────┐    │
│  │                         CORE DATABASE                               │    │
│  │                     (SQLite: nexus.db)                              │    │
│  └───────────────────────────────────────────────────────────────────┘    │
│                                      │                                      │
│  ┌───────────────────────────────────┼───────────────────────────────────┐ │
│  │                                   │                                    │ │
│  │  ┌──────────────┐  ┌──────────────▼──────────────┐  ┌──────────────┐ │ │
│  │  │   RAG / KB   │  │      LLM PROVIDER           │  │   TRAINING   │ │ │
│  │  │  (Vector DB) │  │    (Ollama/OpenAI)          │  │   PIPELINE   │ │ │
│  │  └──────────────┘  └─────────────────────────────┘  └──────────────┘ │ │
│  │                                                                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐ │ │
│  │  │  RED TEAM    │  │  BLUE TEAM   │  │      MCP INTEGRATION         │ │ │
│  │  │  (Offensive) │  │  (Defensive) │  │  (8 MCP Server Types)        │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────────┘ │ │
│  │                                                                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐ │ │
│  │  │   SEARCH     │  │   NETWORK    │  │      WEBSOCKET SERVER        │ │ │
│  │  │   ENGINE     │  │  (Scapy)     │  │      (Port 18011)            │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Module Dependencies

```
backend/app_integrated.py
├── security/* (clearance, session, MFA, audit, decorators)
├── auth/jwt_auth.py
├── agents/* (agent, manager, api)
├── rag/* (vector_kb, api)
├── training/* (unsloth_trainer, api)
├── redteam/* (__init__, api, recon, scanning, exploit, payload, social, c2)
├── blueteam/* (__init__, api)
├── mcp_integration/* (client, tools_v2)
├── llm/* (provider, agent_bridge, error_handler)
├── network/packet_crafter.py
├── search/engine.py
├── websocket/server.py
├── sandbox/podman_sandbox.py
└── audit/tamper_evident.py
```

---

# 3. COMPLETE FILE INVENTORY

## 3.1 Python Source Files (Total: 80+ files)

### Backend (4 files)
| File | Lines | Status | Description |
|------|-------|--------|-------------|
| `backend/app_integrated.py` | 2198 | ✅ COMPLETE | Main Flask application |
| `backend/app_integrated_fixed.py` | 2185 | ✅ COMPLETE | Fixed version |
| `backend/app_integrated_v5.py` | 1716 | ⚠️ LEGACY | Version 5 backup |
| `backend/app.py` | 2047 | ⚠️ LEGACY | Original app |
| `backend/app_secure.py` | 714 | ⚠️ LEGACY | Security-focused variant |

### Agents System (5 files)
| File | Lines | Status | Description |
|------|-------|--------|-------------|
| `agents/__init__.py` | 35 | ✅ COMPLETE | Package exports |
| `agents/agent.py` | 1041 | ✅ COMPLETE | Core agent implementation |
| `agents/manager.py` | 328 | ✅ COMPLETE | Agent orchestration |
| `agents/api.py` | 258 | ✅ COMPLETE | REST API endpoints |
| `agents/tools.py` | 0 | ❌ EMPTY | Stub for future tools |
| `agents/memory.py` | 0 | ❌ EMPTY | Stub for future memory |

### Security (11 files)
| File | Lines | Status | Description |
|------|-------|--------|-------------|
| `security/__init__.py` | 175 | ✅ COMPLETE | Security exports |
| `security/clearance.py` | 373 | ✅ COMPLETE | Clearance level system |
| `security/decorators.py` | 286 | ✅ COMPLETE | Auth decorators |
| `security/mfa/totp.py` | 351 | ✅ COMPLETE | TOTP/MFA implementation |
| `security/session/manager.py` | 447 | ✅ COMPLETE | Session lifecycle |
| `security/audit/logger.py` | 564 | ✅ COMPLETE | Audit logging |
| `auth/jwt_auth.py` | 145 | ✅ COMPLETE | JWT authentication |
| `audit/tamper_evident.py` | 596 | ✅ COMPLETE | Tamper-evident chain |
| `security/mfa/__init__.py` | 0 | ❌ EMPTY | Stub |
| `security/session/__init__.py` | 0 | ❌ EMPTY | Stub |
| `security/crypto/__init__.py` | 0 | ❌ EMPTY | Stub |
| `security/audit/__init__.py` | 0 | ❌ EMPTY | Stub |

### Red Team (9 files)
| File | Lines | Status | Description |
|------|-------|--------|-------------|
| `redteam/__init__.py` | 358 | ✅ COMPLETE | RedTeamManager class |
| `redteam/api.py` | 1134 | ✅ COMPLETE | Flask API endpoints |
| `redteam/recon.py` | 615 | ✅ COMPLETE | Reconnaissance module |
| `redteam/scanning.py` | 762 | ✅ COMPLETE | Vulnerability scanner |
| `redteam/exploit.py` | 870 | ✅ COMPLETE | Exploit framework |
| `redteam/payload.py` | 547 | ✅ COMPLETE | Payload generator |
| `redteam/social.py` | 900 | ✅ COMPLETE | Social engineering |
| `redteam/c2.py` | 732 | ✅ COMPLETE | C2 infrastructure |
| `redteam/session_handler.py` | 845 | ✅ COMPLETE | Session management |
| `redteam/database.py` | 530 | ✅ COMPLETE | Database operations |

### Blue Team (12 files)
| File | Lines | Status | Description |
|------|-------|--------|-------------|
| `blueteam/__init__.py` | 1509 | ✅ COMPLETE | BlueTeamManager class |
| `blueteam/api.py` | 740 | ✅ COMPLETE | Flask API endpoints |
| `blueteam/detection/engine.py` | 0 | ❌ EMPTY | Detection engine stub |
| `blueteam/detection/rules.py` | 0 | ❌ EMPTY | Rules stub |
| `blueteam/logs/ingestion.py` | 0 | ❌ EMPTY | Log ingestion stub |
| `blueteam/logs/parser.py` | 0 | ❌ EMPTY | Log parser stub |
| `blueteam/ir/incident.py` | 0 | ❌ EMPTY | Incident stub |
| `blueteam/ir/playbooks.py` | 0 | ❌ EMPTY | Playbooks stub |
| `blueteam/intel/ioc.py` | 0 | ❌ EMPTY | IOC stub |
| `blueteam/intel/attck.py` | 0 | ❌ EMPTY | ATT&CK stub |
| `blueteam/database.py` | 0 | ❌ EMPTY | Database stub |

### RAG System (3 files)
| File | Lines | Status | Description |
|------|-------|--------|-------------|
| `rag/vector_kb.py` | 970 | ✅ COMPLETE | Vector knowledge base |
| `rag/api.py` | 277 | ✅ COMPLETE | RAG API endpoints |
| `rag/__init__.py` | 4 | ✅ COMPLETE | Package init |

### MCP Integration (3 files)
| File | Lines | Status | Description |
|------|-------|--------|-------------|
| `mcp_integration/client.py` | 318 | ✅ COMPLETE | JSON-RPC MCP client |
| `mcp_integration/tools_v2.py` | 358 | ✅ COMPLETE | MCP tool registry v2 |
| `mcp_integration/tools.py` | 736 | ⚠️ LEGACY | Old tools module |
| `mcp_integration/__init__.py` | 19 | ✅ COMPLETE | Package init |
| `mcp/mcp_server.py` | 732 | ✅ COMPLETE | MCP server implementation |

### LLM System (4 files)
| File | Lines | Status | Description |
|------|-------|--------|-------------|
| `llm/provider.py` | 505 | ✅ COMPLETE | LLM provider classes |
| `llm/agent_bridge.py` | 547 | ✅ COMPLETE | Agent-LLM bridge |
| `llm/error_handler.py` | 333 | ✅ COMPLETE | Error handling |
| `llm/__init__.py` | 56 | ✅ COMPLETE | Package init |

### Training (3 files)
| File | Lines | Status | Description |
|------|-------|--------|-------------|
| `training/unsloth_trainer.py` | 1093 | ✅ COMPLETE | Training pipeline |
| `training/api.py` | 223 | ✅ COMPLETE | Training API |
| `training/__init__.py` | 4 | ✅ COMPLETE | Package init |

### Other Modules (9 files)
| File | Lines | Status | Description |
|------|-------|--------|-------------|
| `websocket/server.py` | 590 | ✅ COMPLETE | WebSocket server |
| `network/packet_crafter.py` | 1059 | ✅ COMPLETE | Network packet crafting |
| `search/engine.py` | 395 | ✅ COMPLETE | Search engine |
| `sandbox/podman_sandbox.py` | 192 | ✅ COMPLETE | Code sandbox |
| `auth/__init__.py` | 4 | ✅ COMPLETE | Package init |
| `rag/__init__.py` | 4 | ✅ COMPLETE | Package init |
| `search/__init__.py` | 4 | ✅ COMPLETE | Package init |
| `sandbox/__init__.py` | 4 | ✅ COMPLETE | Package init |
| `websocket/__init__.py` | 4 | ✅ COMPLETE | Package init |
| `network/__init__.py` | 18 | ✅ COMPLETE | Package init |
| `mcp/__init__.py` | 14 | ✅ COMPLETE | Package init |

## 3.2 Static Files
| File | Size | Description |
|------|------|-------------|
| `static/index.html` | 148KB | Main dashboard UI |
| `static/playground.html` | 13KB | API playground |
| `static/playground-enhanced.html` | 7KB | Enhanced playground |
| `static/app-enhanced.js` | - | Enhanced JavaScript |
| `static/font-fix.css` | - | Font styling fixes |

### Library Files (static/lib/)
- `tailwindcss@3.4.1.js`
- `gsap@3.12.2.min.js`
- `alpine@3.14.3.js`
- `chart.js@4.4.1.umd.min.js`
- `socket.io@4.7.2.min.js`
- `axios@1.6.2.min.js`
- `fontawesome@6.5.1.all.min.css`
- `three@0.160.0.min.js`

## 3.3 Configuration Files
| File | Description |
|------|-------------|
| `requirements.txt` | Python dependencies |
| `containers/c-sandbox/entrypoint.sh` | C sandbox entry |

---

# 4. CORE BACKEND SYSTEM

## 4.1 Main Application (`backend/app_integrated.py`)

### Environment Configuration
```python
DATA_DIR = "/opt/codex-swarm/command-post/data"
UPLOADS_DIR = "/opt/codex-swarm/command-post/uploads"
MODELS_DIR = "/opt/codex-swarm/command-post/models"
STATIC_FOLDER = "/opt/codex-swarm/command-post/static"
DB_PATH = "/opt/codex-swarm/command-post/data/nexus.db"
ROUTER_URL = os.environ.get('ROUTER_URL', 'http://localhost:18000')
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'ordl-secret-key-change-in-production')
NEXUS_TOKEN = os.environ.get('NEXUS_TOKEN', 'REPLACE_WITH_ENV_NEXUS_TOKEN')
```

### Module Availability Flags
| Flag | Description |
|------|-------------|
| `SECURITY_AVAILABLE` | USG-grade security system |
| `AUTH_AVAILABLE` | JWT authentication |
| `SANDBOX_AVAILABLE` | Podman code sandbox |
| `TRAINING_AVAILABLE` | LLM training pipeline |
| `AGENTS_AVAILABLE` | Multi-agent system |
| `RAG_AVAILABLE` | RAG knowledge base |
| `NETWORK_AVAILABLE` | Network tools |
| `SEARCH_AVAILABLE` | Search engine |
| `MCP_AVAILABLE` | MCP servers |
| `WEBSOCKET_AVAILABLE` | Real-time chat |
| `REDTEAM_AVAILABLE` | Offensive security |
| `BLUETEAM_AVAILABLE` | Defensive security |

### Database Tables (18 tables)
1. `agents` - Agent storage
2. `agent_audit_logs` - Agent activity
3. `swarm_operations` - Multi-agent ops
4. `training_jobs` - Training jobs
5. `custom_models` - Fine-tuned models
6. `research_tasks` - Research tracking
7. `file_uploads` - File management
8. `conversations` - Chat history
9. `tools` - Custom tools
10. `mcp_servers` - MCP server registry
11. `network_captures` - Packet captures
12. `system_events` - System logs
13. `knowledge_base` - RAG documents
14. `auth_users` - User accounts
15. `refresh_tokens` - Token storage
16. `kb_documents` - Knowledge documents
17. `agent_tasks` - Agent task queue
18. `agent_memory` - Agent conversations

### In-Memory Data Stores
```python
agents_db = {}              # Legacy agent storage
agent_audit_logs = {}       # Audit trails
swarm_operations = {}       # Swarm ops
network_captures = {}       # Network data
research_tasks = {}         # Research tracking
file_uploads = {}           # Uploaded files
conversations_db = {}       # Conversations
custom_models = []          # Trained models
tools_registry = {}         # Custom tools
mcp_servers = {}            # MCP connections
knowledge_base = {}         # KB entries
request_count = {'total': 0, 'per_minute': []}
```

---

# 5. AGENT SYSTEM

## 5.1 Agent Class (`agents/agent.py`)

### AgentStatus Enum
```python
class AgentStatus(Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PROCESSING = "processing"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    DESTROYED = "destroyed"
```

### TaskPriority Enum
```python
class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4
```

### AgentConfig Dataclass
```python
@dataclass
class AgentConfig:
    agent_id: str
    name: str
    persona: str
    model: str = "default"
    clearance: str = "SECRET"
    capabilities: List[str] = field(default_factory=list)
    max_context_length: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2048
    tools_enabled: List[str] = field(default_factory=list)
    auto_tool_use: bool = True
    memory_enabled: bool = True
```

### Agent Class Methods
| Method | Description |
|--------|-------------|
| `__init__(config, tool_registry)` | Initialize agent |
| `to_dict()` | Serialize to dict |
| `process_message(message)` | Process user message |
| `_extract_tool_calls(message)` | Parse @tool(args) syntax |
| `_generate_response(message)` | LLM response generation |
| `_fallback_response(message)` | Offline mode response |
| `execute_task(task)` | Execute assigned task |
| `stop()` | Stop agent |
| `pause()` | Pause agent |
| `resume()` | Resume agent |
| `destroy()` | Cleanup and destroy |

### ToolRegistry Class
**Built-in Tools (11 total):**
1. `redteam_recon` - Target reconnaissance
2. `redteam_scan` - Vulnerability scan
3. `redteam_payload` - Payload generation
4. `blueteam_status` - SOC status
5. `blueteam_alerts` - Security alerts
6. `blueteam_ingest` - Log ingestion
7. `rag_search` - Knowledge search
8. `rag_ingest` - Document ingestion
9. `train_hardware` - Training hardware info
10. `train_create_job` - Create training job
11. `system_time` - System time
12. `system_status` - System status

**MCP Tools (14 total):**
- GitHub: search_repos, get_repo, search_code
- Context7: query, resolve
- Playwright: navigate, screenshot, extract_text
- Filesystem: read_file, list_directory, search_files
- Fetch: fetch_url
- Sequential Thinking: think_sequential, think_analyze

## 5.2 AgentManager Class (`agents/manager.py`)

### Manager Statistics
```python
self.stats = {
    "agents_created": 0,
    "agents_destroyed": 0,
    "tasks_completed": 0,
    "tasks_failed": 0,
    "started_at": datetime.utcnow().isoformat()
}
```

### AgentManager Methods
| Method | Description |
|--------|-------------|
| `create_agent(config_dict)` | Create new agent |
| `get_agent(agent_id)` | Get agent by ID |
| `destroy_agent(agent_id)` | Destroy agent |
| `list_agents()` | List all agents |
| `send_message(agent_id, message)` | Send message |
| `create_task(description, priority, agent_id, payload)` | Create task |
| `get_stats()` | Get manager stats |
| `get_tools()` | List available tools |
| `execute_tool(tool_name, **kwargs)` | Execute tool |
| `shutdown()` | Shutdown manager |

### Database Schema (agent_tasks)
```sql
CREATE TABLE agent_tasks (
    task_id TEXT PRIMARY KEY,
    agent_id TEXT,
    priority INTEGER,
    description TEXT,
    payload TEXT,
    status TEXT,
    created_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    result TEXT,
    error TEXT
)
```

---

# 6. SECURITY INFRASTRUCTURE

## 6.1 Clearance System (`security/clearance.py`)

### ClearanceLevel Enum
```python
class ClearanceLevel(IntEnum):
    UNCLASSIFIED = 0
    CONFIDENTIAL = 1
    SECRET = 2
    TOP_SECRET = 3
    TS_SCI = 4
    TS_SCI_NOFORN = 5
```

### Standard Compartments
- `HCS` - HUMINT Control System
- `KLONDIKE` - SIGINT collection
- `GAMMA` - Sensitive SIGINT
- `TALENT KEYHOLE` - Satellite reconnaissance
- `ORCON` - Originator Controlled
- `NOFORN` - No Foreign Nationals
- `REL TO` - Releasable To

### ORDL_RESOURCES Dictionary (35 resources)
Resources defined for:
- Core system (login, status)
- Agents (list, control, deploy)
- Intelligence (search, OSINT, HUMINT, SIGINT, IMINT)
- Network Operations (monitor, capture, exploit)
- Red Team (recon, scan, exploit, payload)
- Blue Team (monitor, respond, forensics)
- Admin (users, audit, clearance)

## 6.2 Session Management (`security/session/manager.py`)

### SessionStatus Enum
```python
class SessionStatus(Enum):
    ACTIVE = "active"
    IDLE = "idle"
    LOCKED = "locked"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    SUSPICIOUS = "suspicious"
```

### Timeout Configuration by Clearance
| Clearance | Idle Timeout | Absolute Timeout |
|-----------|--------------|------------------|
| UNCLASSIFIED | 1 hour | 8 hours |
| CONFIDENTIAL | 30 min | 4 hours |
| SECRET | 15 min | 2 hours |
| TOP SECRET | 10 min | 1 hour |
| TS/SCI | 5 min | 30 min |
| TS/SCI/NOFORN | 2 min | 15 min |

### Max Concurrent Sessions
| Clearance | Max Sessions |
|-----------|--------------|
| UNCLASSIFIED | 5 |
| CONFIDENTIAL | 3 |
| SECRET | 2 |
| TOP SECRET | 2 |
| TS/SCI | 1 |
| TS/SCI/NOFORN | 1 |

### SessionManager Methods
| Method | Description |
|--------|-------------|
| `create_session(...)` | Create new session |
| `get_session(session_id)` | Get session by ID |
| `validate_session(...)` | Validate with security checks |
| `touch_session(session_id)` | Update activity |
| `lock_session(session_id)` | Lock session |
| `unlock_session(session_id, mfa_verified)` | Unlock session |
| `terminate_session(session_id)` | End session |
| `terminate_all_user_sessions(user)` | End all user sessions |
| `get_user_sessions(user)` | List user sessions |
| `get_stats()` | Get session stats |

## 6.3 Tamper-Evident Audit (`audit/tamper_evident.py`)

### AuditEventType Enum (30+ events)
- Security: AUTHENTICATION_SUCCESS, AUTHENTICATION_FAILURE, AUTHORIZATION_DENIED, SESSION_CREATED, SESSION_DESTROYED
- Data: DATA_READ, DATA_WRITE, DATA_DELETE, DATA_EXPORT
- Red Team: REDTEAM_OPERATION_STARTED, REDTEAM_OPERATION_COMPLETED, REDTEAM_SCAN_EXECUTED, REDTEAM_PAYLOAD_GENERATED
- Blue Team: BLUETEAM_ALERT_GENERATED, BLUETEAM_INCIDENT_CREATED, BLUETEAM_IOC_ADDED, BLUETEAM_LOG_INGESTED
- Training: TRAINING_JOB_STARTED, TRAINING_JOB_COMPLETED, TRAINING_MODEL_EXPORTED
- Agent: AGENT_CREATED, AGENT_DESTROYED, AGENT_MESSAGE_SENT, AGENT_TOOL_EXECUTED
- MCP: MCP_TOOL_INVOKED, MCP_DATA_RETRIEVED
- System: SYSTEM_STARTUP, SYSTEM_SHUTDOWN, CONFIG_CHANGED, BACKUP_CREATED
- Integrity: INTEGRITY_CHECK_PASSED, INTEGRITY_CHECK_FAILED, CHAIN_VERIFIED, CHAIN_CORRUPTION_DETECTED

### AuditEntry Dataclass
```python
@dataclass
class AuditEntry:
    entry_id: str
    timestamp: str
    sequence_number: int
    event_type: str
    user_id: str
    user_clearance: str
    resource_id: str
    action: str
    status: str
    details: Dict[str, Any]
    classification: str
    previous_hash: str      # Chain linkage
    entry_hash: str         # SHA-256 of entry
    hmac_signature: str     # HMAC-SHA256
```

### TamperEvidentAuditLog Methods
| Method | Description |
|--------|-------------|
| `create_entry(...)` | Create new audit entry |
| `verify_integrity(start_sequence)` | Verify chain integrity |
| `get_entries(...)` | Query audit entries |
| `export_chain(output_path)` | Export for forensics |
| `get_statistics()` | Get audit stats |

---

# 7. RED TEAM OPERATIONS

## 7.1 RedTeamManager (`redteam/__init__.py`)

### OperationStatus Enum
```python
class OperationStatus(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RECON = "reconnaissance"
    SCANNING = "scanning"
    EXPLOITATION = "exploitation"
    POST_EXPLOITATION = "post_exploitation"
    PERSISTENCE = "persistence"
    EXFILTRATION = "exfiltration"
    COVERING_TRACKS = "covering_tracks"
    COMPLETED = "completed"
    ABORTED = "aborted"
    COMPROMISED = "compromised"
```

### TargetType Enum
```python
class TargetType(Enum):
    IP_ADDRESS = "ip_address"
    DOMAIN = "domain"
    SUBNET = "subnet"
    WEB_APPLICATION = "web_application"
    WIRELESS_NETWORK = "wireless_network"
    MOBILE_DEVICE = "mobile_device"
    IOT_DEVICE = "iot_device"
    INDUSTRIAL_SYSTEM = "industrial_system"
    CLOUD_INFRASTRUCTURE = "cloud_infrastructure"
```

### RedTeamManager Sub-modules
| Module | Class | Purpose |
|--------|-------|---------|
| `recon` | ReconManager | Reconnaissance |
| `scanner` | VulnerabilityScanner | Vulnerability scanning |
| `exploit` | ExploitFramework | Exploit execution |
| `payload` | PayloadGenerator | Payload creation |
| `social` | SocialEngineering | Social engineering |
| `c2` | C2Infrastructure | Command & control |

## 7.2 Red Team API Endpoints (`redteam/api.py`)

### Operations (4 endpoints)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/redteam/status` | GET | System status |
| `/api/redteam/operations` | GET | List operations |
| `/api/redteam/operations` | POST | Create operation |
| `/api/redteam/operations/<id>` | GET | Get operation |
| `/api/redteam/operations/<id>/status` | PUT | Update status |

### Targets (2 endpoints)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/redteam/targets` | GET | List targets |
| `/api/redteam/targets` | POST | Add target |

### Reconnaissance (3 endpoints)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/redteam/recon/scan` | POST | Port scan |
| `/api/redteam/recon/dns` | GET | DNS lookup |
| `/api/redteam/recon/subdomains` | GET | Enumerate subdomains |

### Vulnerability Scanning (3 endpoints)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/redteam/scan/service` | POST | Scan service |
| `/api/redteam/scan/web` | POST | Web app scan |
| `/api/redteam/scan/ssl` | GET | SSL analysis |

### Exploit Framework (4 endpoints)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/redteam/exploits` | GET | List exploits |
| `/api/redteam/exploits/<id>/check` | POST | Check vulnerable |
| `/api/redteam/exploits/execute` | POST | Execute exploit |
| `/api/redteam/sessions` | GET | List sessions |
| `/api/redteam/sessions/<id>/interact` | POST | Interact with session |

### Payload Generation (2 endpoints)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/redteam/payloads/generate/reverse_shell` | POST | Generate payload |
| `/api/redteam/payloads` | GET | List payloads |

### Social Engineering (3 endpoints)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/redteam/phishing/templates` | GET | List templates |
| `/api/redteam/phishing/campaigns` | GET | List campaigns |
| `/api/redteam/phishing/campaigns` | POST | Create campaign |
| `/api/redteam/phishing/campaigns/<id>/stats` | GET | Campaign stats |

### C2 Infrastructure (4 endpoints)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/redteam/c2/listeners` | GET | List listeners |
| `/api/redteam/c2/listeners` | POST | Create listener |
| `/api/redteam/c2/sessions` | GET | List C2 sessions |
| `/api/redteam/c2/kill_switch` | POST | EMERGENCY kill all |

---

# 8. BLUE TEAM DEFENSE

## 8.1 BlueTeamManager (`blueteam/__init__.py`)

### AlertSeverity Enum
```python
class AlertSeverity(Enum):
    CRITICAL = "CRITICAL"      # Immediate response
    HIGH = "HIGH"              # Within 1 hour
    MEDIUM = "MEDIUM"          # Within 4 hours
    LOW = "LOW"                # Within 24 hours
    INFO = "INFO"              # Informational
```

### IncidentStatus Enum
```python
class IncidentStatus(Enum):
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    INVESTIGATING = "INVESTIGATING"
    CONTAINED = "CONTAINED"
    ERADICATED = "ERADICATED"
    RECOVERED = "RECOVERED"
    CLOSED = "CLOSED"
```

### IOCType Enum
```python
class IOCType(Enum):
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    HASH_MD5 = "hash_md5"
    HASH_SHA1 = "hash_sha1"
    HASH_SHA256 = "hash_sha256"
    FILE_NAME = "file_name"
    REGISTRY_KEY = "registry_key"
    MUTEX = "mutex"
    YARA_RULE = "yara_rule"
    SIGNATURE = "signature"
```

### LogSource Enum
```python
class LogSource(Enum):
    SYSLOG = "syslog"
    WINDOWS = "windows"
    LINUX_AUTH = "linux_auth"
    APACHE = "apache"
    NGINX = "nginx"
    FIREWALL = "firewall"
    IDS = "ids"
    EDR = "edr"
    CLOUD_TRAIL = "cloud_trail"
    CUSTOM = "custom"
```

## 8.2 Built-in Detection Rules (19 rules)

| Rule ID | Name | Severity | MITRE Techniques |
|---------|------|----------|------------------|
| BT-AUTH-001 | Multiple Failed Logins | HIGH | T1110, T1110.001 |
| BT-PRIV-001 | Privilege Escalation | CRITICAL | T1068, T1548, T1548.001 |
| BT-NET-001 | Suspicious Outbound | HIGH | T1041, T1048, T1071 |
| BT-NET-002 | Port Scan | MEDIUM | T1046 |
| BT-MAL-001 | Suspicious Process | HIGH | T1059, T1204, T1204.002 |
| BT-MAL-002 | Encoded PowerShell | CRITICAL | T1059.001, T1027, T1027.001 |
| BT-LAT-001 | Suspicious RDP | HIGH | T1021.001 |
| BT-LAT-002 | SMB Lateral Movement | HIGH | T1021.002, T1570 |
| BT-EXF-001 | Large Data Transfer | HIGH | T1041, T1048 |
| BT-EXF-002 | Clipboard Access | MEDIUM | T1115 |
| BT-PER-001 | New Scheduled Task | MEDIUM | T1053, T1053.005 |
| BT-PER-002 | Registry Run Key | HIGH | T1547, T1547.001 |
| BT-DEF-001 | Service Stop | CRITICAL | T1562, T1562.001 |
| BT-DEF-002 | Log Cleared | CRITICAL | T1070, T1070.001 |
| BT-WEB-001 | SQL Injection | HIGH | T1190 |
| BT-WEB-002 | Directory Traversal | MEDIUM | T1083, T1083.001 |
| BT-WEB-003 | XSS Attempt | MEDIUM | T1189 |

## 8.3 BlueTeamManager Methods

### IOC Management
| Method | Description |
|--------|-------------|
| `add_ioc(...)` | Add new IOC |
| `check_ioc(value)` | Check if value matches IOC |
| `get_iocs(...)` | Get IOCs with filtering |
| `delete_ioc(ioc_id)` | Delete IOC |

### Log Ingestion & Analysis
| Method | Description |
|--------|-------------|
| `ingest_log(...)` | Ingest and analyze log |
| `_normalize_log(...)` | Normalize to common schema |
| `_check_iocs_in_log(...)` | Check for IOC matches |
| `_run_detection(...)` | Run detection rules |

### Incident Management
| Method | Description |
|--------|-------------|
| `create_incident(...)` | Create incident case |
| `update_incident_status(...)` | Update incident status |
| `get_incident(incident_id)` | Get incident |
| `get_incidents(...)` | List incidents |
| `add_containment_action(...)` | Add containment action |

### Alert Management
| Method | Description |
|--------|-------------|
| `get_alert(alert_id)` | Get alert |
| `get_alerts(...)` | List alerts |
| `assign_alert(alert_id, analyst)` | Assign to analyst |
| `close_alert(alert_id, resolution)` | Close alert |

---

# 9. RAG KNOWLEDGE BASE

## 9.1 VectorKnowledgeBase (`rag/vector_kb.py`)

### Store Types
| Type | Description |
|------|-------------|
| `chromadb` | Primary (when available) |
| `sqlite` | Fallback (always works) |

### Embedding Models
| Model | Description |
|-------|-------------|
| `all-MiniLM-L6-v2` | Default (fast, good quality) |
| `all-mpnet-base-v2` | Higher quality, slower |
| `paraphrase-MiniLM-L3-v2` | Ultra-fast |

### VectorKnowledgeBase Methods
| Method | Description |
|--------|-------------|
| `ingest_document(...)` | Add document to KB |
| `query(query, top_k, category)` | Semantic search |
| `get_document(doc_id)` | Get document by ID |
| `delete_document(doc_id)` | Remove document |
| `list_documents(...)` | List documents |
| `query_with_context(...)` | Query with context for LLM |
| `get_stats()` | Get KB statistics |
| `search_history(limit)` | Get recent searches |

## 9.2 TextChunker Configuration
```python
chunk_size: int = 512
chunk_overlap: int = 50
respect_paragraphs: bool = True
```

---

# 10. MCP INTEGRATION

## 10.1 MCPClient (`mcp_integration/client.py`)

### JSONRPCMessage Dataclass
```python
@dataclass
class JSONRPCMessage:
    id: Optional[str]
    method: Optional[str]
    params: Optional[Dict]
    result: Optional[Any]
    error: Optional[Dict]
```

### MCPClient Methods
| Method | Description |
|--------|-------------|
| `connect()` | Start server and connect |
| `_initialize()` | Send initialize request |
| `call_tool(tool_name, arguments)` | Execute tool |
| `list_tools()` | List available tools |
| `disconnect()` | Close connection |

## 10.2 MCPToolRegistry (`mcp_integration/tools_v2.py`)

### MCPResult Dataclass
```python
@dataclass
class MCPResult:
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: int = 0
    cached: bool = False
```

### Available MCP Tools (14 tools)

**GitHub MCP Server:**
- `github_search_repos` - Search repositories
- `github_get_repo` - Get repository info
- `github_search_code` - Search code

**Context7 MCP Server:**
- `context7_query` - Query documentation
- `context7_resolve` - Resolve library ID

**Playwright MCP Server:**
- `playwright_navigate` - Navigate to URL
- `playwright_screenshot` - Take screenshot
- `playwright_extract_text` - Extract text

**Filesystem MCP Server:**
- `fs_read_file` - Read file
- `fs_list_directory` - List directory
- `fs_search_files` - Search files

**Fetch MCP Server:**
- `fetch_url` - Fetch webpage as markdown

**Sequential Thinking MCP Server:**
- `think_sequential` - Structured thinking
- `think_analyze` - Analyze data

### MCPToolRegistry Methods
| Method | Description |
|--------|-------------|
| `execute_tool(tool_name, **kwargs)` | Execute MCP tool |
| `list_tools()` | List available tools |
| `get_stats()` | Get execution statistics |

---

# 11. LLM PROVIDER SYSTEM

## 11.1 LLM Provider Classes (`llm/provider.py`)

### LLMProviderType Enum
```python
class LLMProviderType(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
```

### MessageRole Enum
```python
class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
```

## 11.2 OllamaProvider
```python
class OllamaProvider(LLMProvider):
    def __init__(self, 
                 model: str = "llama3.3",
                 base_url: str = "http://localhost:11434",
                 temperature: float = 0.7,
                 max_tokens: int = 4096)
```

### Methods
| Method | Description |
|--------|-------------|
| `_check_model()` | Verify model availability |
| `complete(messages, tools)` | Generate completion |
| `complete_stream(messages, tools)` | Streaming completion |

## 11.3 OpenAIProvider
```python
class OpenAIProvider(LLMProvider):
    def __init__(self,
                 model: str = "gpt-4",
                 api_key: Optional[str] = None,
                 base_url: str = "https://api.openai.com/v1",
                 temperature: float = 0.7,
                 max_tokens: int = 4096)
```

## 11.4 LLMProviderFactory
```python
class LLMProviderFactory:
    _providers: Dict[str, type] = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
    }
```

### Methods
| Method | Description |
|--------|-------------|
| `create(provider_type, **kwargs)` | Create provider instance |
| `register(name, provider_class)` | Register new provider |
| `list_providers()` | List available providers |

---

# 12. TRAINING PIPELINE

## 12.1 UnslothTrainer (`training/unsloth_trainer.py`)

### TrainingStatus Enum
```python
class TrainingStatus(Enum):
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"
```

### DatasetFormat Enum
```python
class DatasetFormat(Enum):
    ALPACA = "alpaca"
    CHAT = "chat"
    TEXT = "text"
    JSONL = "jsonl"
    CSV = "csv"
```

## 12.2 TrainingConfig
```python
@dataclass
class TrainingConfig:
    job_id: str
    name: str
    base_model: str
    output_model: str
    dataset_source: str
    dataset_path: str
    learning_rate: float = 2e-4
    batch_size: int = 2
    gradient_accumulation_steps: int = 4
    max_steps: int = 1000
    lora_r: int = 16
    lora_alpha: int = 32
    load_in_4bit: bool = True
```

## 12.3 UnslothTrainer Methods
| Method | Description |
|--------|-------------|
| `create_job(config_dict)` | Create training job |
| `start_training(job_id)` | Start training |
| `stop_job(job_id)` | Stop training |
| `get_job(job_id)` | Get job details |
| `list_jobs()` | List all jobs |
| `get_job_metrics(job_id)` | Get training metrics |
| `get_hardware_info()` | Get hardware info |
| `_train_with_unsloth(job)` | GPU training |
| `_train_with_transformers(job)` | CPU/GPU training |

---

# 13. WEBSOCKET SERVER

## 13.1 WebSocketServer (`websocket/server.py`)

### Default Channels
```python
DEFAULT_CHANNELS = {
    'general': 'UNCLASSIFIED',
    'tech': 'CONFIDENTIAL',
    'ops': 'SECRET',
    'intel': 'TOP SECRET',
    'sci': 'TS/SCI',
    'noforn': 'TS/SCI/NOFORN'
}
```

### Message Types
- `auth` - Authentication
- `auth_success` - Auth success
- `message` - Chat message
- `message_confirm` - Message confirmation
- `join_channel` - Join channel
- `leave_channel` - Leave channel
- `channel_joined` - Channel joined
- `channel_left` - Channel left
- `typing` - Typing indicator
- `direct_message` - Direct message
- `dm_confirm` - DM confirmation
- `ping` / `pong` - Keepalive
- `status` - Status change
- `presence` / `presence_list` - Online status
- `system` - System message
- `history` - Message history
- `error` - Error message

## 13.2 WebSocketServer Methods
| Method | Description |
|--------|-------------|
| `start()` | Start server |
| `stop()` | Stop server |
| `_handle_connection(...)` | Handle connection |
| `_handle_message(...)` | Handle message |
| `_join_channel(...)` | Join channel |
| `_leave_channel(...)` | Leave channel |
| `_broadcast_to_channel(...)` | Broadcast message |
| `get_stats()` | Get server stats |

---

# 14. DATABASE SCHEMAS

## 14.1 Main Database (nexus.db)

### agents
```sql
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT,
    persona TEXT,
    model TEXT,
    clearance TEXT DEFAULT 'SECRET',
    status TEXT DEFAULT 'idle',
    created_at TEXT,
    tasks_completed INTEGER DEFAULT 0,
    capabilities TEXT,
    description TEXT,
    config TEXT
)
```

### agent_audit_logs
```sql
CREATE TABLE agent_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT,
    timestamp TEXT,
    action TEXT,
    details TEXT,
    operation_id TEXT
)
```

### swarm_operations
```sql
CREATE TABLE swarm_operations (
    id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    status TEXT,
    agents TEXT,
    objective TEXT,
    progress INTEGER,
    created_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    results TEXT
)
```

### training_jobs
```sql
CREATE TABLE training_jobs (
    id TEXT PRIMARY KEY,
    name TEXT,
    model TEXT,
    dataset TEXT,
    output_model TEXT,
    status TEXT,
    progress INTEGER,
    epochs TEXT,
    loss REAL,
    started_at TEXT,
    completed_at TEXT,
    config TEXT
)
```

### training_metrics
```sql
CREATE TABLE training_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT,
    step INTEGER,
    epoch INTEGER,
    loss REAL,
    learning_rate REAL,
    timestamp TEXT,
    FOREIGN KEY (job_id) REFERENCES training_jobs(job_id)
)
```

### knowledge_base
```sql
CREATE TABLE knowledge_base (
    id TEXT PRIMARY KEY,
    title TEXT,
    content TEXT,
    category TEXT,
    tags TEXT,
    source TEXT,
    created_at TEXT,
    updated_at TEXT,
    embedding_id TEXT
)
```

### kb_documents
```sql
CREATE TABLE kb_documents (
    id TEXT PRIMARY KEY,
    title TEXT,
    content TEXT,
    category TEXT DEFAULT 'general',
    tags TEXT,
    source TEXT,
    created_at TEXT,
    updated_at TEXT,
    chunk_count INTEGER DEFAULT 0,
    embedding_model TEXT,
    content_hash TEXT
)
```

### vector_embeddings
```sql
CREATE TABLE vector_embeddings (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding BLOB NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL
)
```

### search_history
```sql
CREATE TABLE search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    results_count INTEGER,
    top_score REAL,
    timestamp TEXT NOT NULL
)
```

### system_events
```sql
CREATE TABLE system_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    level TEXT,
    component TEXT,
    message TEXT,
    details TEXT
)
```

### auth_users
```sql
CREATE TABLE auth_users (
    id TEXT PRIMARY KEY,
    codename TEXT UNIQUE,
    password_hash TEXT,
    clearance TEXT DEFAULT 'UNCLASSIFIED',
    created_at TEXT,
    is_active BOOLEAN DEFAULT 1
)
```

### refresh_tokens
```sql
CREATE TABLE refresh_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT,
    created_at TEXT,
    expires_at TEXT,
    revoked BOOLEAN DEFAULT 0
)
```

### mcp_servers
```sql
CREATE TABLE mcp_servers (
    id TEXT PRIMARY KEY,
    name TEXT,
    endpoint TEXT,
    type TEXT,
    auth_token TEXT,
    status TEXT DEFAULT 'disconnected',
    capabilities TEXT,
    created_at TEXT,
    last_connected TEXT
)
```

## 14.2 Audit Database (audit_tamper_evident.db)

### audit_chain
```sql
CREATE TABLE audit_chain (
    entry_id TEXT PRIMARY KEY,
    sequence_number INTEGER UNIQUE NOT NULL,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    user_id TEXT NOT NULL,
    user_clearance TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT NOT NULL,
    classification TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL,
    hmac_signature TEXT NOT NULL
)
```

## 14.3 Blue Team Database (blueteam.db)

### log_entries
```sql
CREATE TABLE log_entries (
    entry_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_host TEXT NOT NULL,
    raw_message TEXT,
    normalized TEXT,
    parsed_fields TEXT,
    tags TEXT,
    alert_triggered INTEGER DEFAULT 0
)
```

### alerts
```sql
CREATE TABLE alerts (
    alert_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    source TEXT NOT NULL,
    rule_name TEXT,
    rule_id TEXT,
    raw_data TEXT,
    ioc_matches TEXT,
    related_events TEXT,
    status TEXT DEFAULT 'OPEN',
    assigned_to TEXT,
    incident_id TEXT,
    mitre_techniques TEXT,
    cvss_score REAL
)
```

### incidents
```sql
CREATE TABLE incidents (
    incident_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    lead_analyst TEXT,
    assigned_team TEXT,
    related_alerts TEXT,
    affected_assets TEXT,
    timeline TEXT,
    evidence_refs TEXT,
    containment_actions TEXT,
    root_cause TEXT,
    lessons_learned TEXT
)
```

### iocs
```sql
CREATE TABLE iocs (
    ioc_id TEXT PRIMARY KEY,
    ioc_type TEXT NOT NULL,
    value TEXT NOT NULL UNIQUE,
    added_at TEXT NOT NULL,
    source TEXT,
    confidence INTEGER,
    severity TEXT,
    description TEXT,
    threat_actor TEXT,
    campaign TEXT,
    first_seen TEXT,
    last_seen TEXT,
    hit_count INTEGER DEFAULT 0
)
```

### detection_rules
```sql
CREATE TABLE detection_rules (
    rule_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    severity TEXT,
    source_types TEXT,
    conditions TEXT,
    mitre_techniques TEXT,
    enabled INTEGER DEFAULT 1,
    created_at TEXT,
    hit_count INTEGER DEFAULT 0,
    last_hit TEXT
)
```

---

# 15. API ENDPOINTS

## 15.1 Health & Status
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/api/system/capabilities` | GET | Yes | System capabilities |
| `/api/system/status` | GET | Yes | System metrics |
| `/api/system/events` | GET | Yes | System events |

## 15.2 Authentication
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/login` | POST | No | Login |
| `/api/auth/me` | GET | Yes | Current user |

## 15.3 Agents (via Blueprint)
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/agents/health` | GET | No | Agent system health |
| `/api/agents/agents` | GET | Yes | List agents |
| `/api/agents/agents` | POST | Yes | Create agent |
| `/api/agents/agents/<id>` | GET | Yes | Get agent |
| `/api/agents/agents/<id>` | DELETE | Yes | Destroy agent |
| `/api/agents/agents/<id>/message` | POST | Yes | Send message |
| `/api/agents/agents/<id>/memory` | GET | Yes | Get memory |
| `/api/agents/tools` | GET | Yes | List tools |
| `/api/agents/tools/<name>/execute` | POST | Yes | Execute tool |
| `/api/agents/tasks` | POST | Yes | Create task |
| `/api/agents/stats` | GET | Yes | Get stats |

## 15.4 Agents (Legacy)
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/agents` | GET | Yes | List agents (legacy) |
| `/api/agents` | POST | Yes | Create agent (legacy) |
| `/api/agents/_legacy/<id>` | GET | Yes | Get agent |
| `/api/agents/_legacy/<id>` | DELETE | Yes | Delete agent |
| `/api/agents/_legacy/<id>/message` | POST | Yes | Send message |
| `/api/agents/_legacy/<id>/control` | POST | Yes | Control agent |

## 15.5 Swarm Operations
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/swarm/operations` | GET | Yes | List operations |
| `/api/swarm/operations` | POST | Yes | Create operation |
| `/api/swarm/operations/<id>` | GET | Yes | Get operation |

## 15.6 Training
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/training/hardware` | GET | Yes | Hardware info |
| `/api/training/jobs` | GET | Yes | List jobs |
| `/api/training/jobs` | POST | Yes | Create job |
| `/api/training/jobs/<id>` | GET | Yes | Get job |
| `/api/training/jobs/<id>` | DELETE | Yes | Stop job |

## 15.7 Sandbox
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/sandbox/execute` | POST | Yes | Execute code |
| `/api/sandbox/languages` | GET | Yes | List languages |

## 15.8 RAG / Knowledge Base
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/knowledge/ingest` | POST | Yes | Ingest document |
| `/api/knowledge/query` | POST | Yes | Query KB |
| `/api/knowledge` | GET | Yes | List entries |
| `/api/knowledge` | POST | Yes | Create entry |
| `/api/knowledge/<id>` | DELETE | Yes | Delete entry |

## 15.9 Network
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/network/status` | GET | Yes | Network status |
| `/api/network/adapters` | GET | Yes | List adapters |
| `/api/network/adapters/<if>/kill` | POST | Yes | Kill adapter |
| `/api/network/adapters/<if>/revive` | POST | Yes | Revive adapter |

## 15.10 Search
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/search` | POST | Yes | Deep search |

## 15.11 Chat
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/chat` | POST | Yes | Chat completion |

## 15.12 Conversations
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/conversations` | GET | Yes | List conversations |
| `/api/conversations` | POST | Yes | Create conversation |
| `/api/conversations/<id>` | DELETE | Yes | Delete conversation |

## 15.13 Research
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/research/tasks` | GET | Yes | List tasks |
| `/api/research/tasks` | POST | Yes | Create task |

## 15.14 Files
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/files` | GET | Yes | List files |
| `/api/files/upload` | POST | Yes | Upload file |
| `/api/files/<id>/download` | GET | Yes | Download file |

## 15.15 Tools
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/tools` | GET | Yes | List tools |

## 15.16 MCP Servers
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/mcp/servers` | GET | Yes | List servers |
| `/api/mcp/servers` | POST | Yes | Create server |
| `/api/mcp/servers/<id>/connect` | POST | Yes | Connect server |
| `/api/mcp/servers/<id>` | DELETE | Yes | Delete server |

## 15.17 Security
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/security/status` | GET | Yes | Security status |

---

# 16. CONFIGURATION & ENVIRONMENT

## 16.1 Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `ROUTER_URL` | `http://localhost:18000` | LLM Router URL |
| `JWT_SECRET_KEY` | `ordl-secret-key-change-in-production` | JWT signing key |
| `NEXUS_TOKEN` | (hardcoded) | Legacy API token |
| `OPENAI_API_KEY` | None | OpenAI API key |

## 16.2 File Paths
| Path | Description |
|------|-------------|
| `/opt/codex-swarm/command-post/data/nexus.db` | Main database |
| `/opt/codex-swarm/command-post/data/audit_tamper_evident.db` | Audit chain |
| `/opt/codex-swarm/command-post/data/chromadb` | ChromaDB storage |
| `/opt/codex-swarm/command-post/blueteam/blueteam.db` | Blue team DB |
| `/opt/codex-swarm/command-post/uploads/` | File uploads |
| `/opt/codex-swarm/command-post/models/` | Trained models |
| `/opt/codex-swarm/command-post/datasets/` | Training datasets |
| `/opt/codex-swarm/command-post/static/` | Static files |
| `/var/log/ordl/blueteam.log` | Blue team logs |

## 16.3 Network Ports
| Port | Service |
|------|---------|
| 18010 | Flask HTTP API |
| 18011 | WebSocket Server |
| 11434 | Ollama (external) |
| 18000 | LLM Router (external) |

---

# 17. DEPENDENCIES

## 17.1 Core Dependencies (from requirements.txt)
```
flask==3.0.0
flask-cors==4.0.0
flask-limiter==3.5.0
werkzeug==3.0.1
requests==2.31.0
aiohttp==3.9.1
chromadb==0.4.18
torch>=2.0.0
transformers>=4.36.0
datasets>=2.14.0
sentence-transformers==2.2.2
accelerate>=0.25.0
bitsandbytes>=0.41.0
pyjwt==2.8.0
cryptography==41.0.7
pyotp==2.9.0
bcrypt==4.1.2
scapy==2.5.0
psutil==5.9.6
playwright==1.40.0
beautifulsoup4==4.12.2
websockets==12.0
python-socketio==5.10.0
python-dateutil==2.8.2
numpy==1.26.2
pandas==2.1.4
tqdm==4.66.1
pyyaml==6.0.1
pytest==7.4.3
black==23.11.0
```

## 17.2 Optional Dependencies (Not Installed)
| Package | Purpose |
|---------|---------|
| `unsloth` | GPU-optimized training |
| `trl` | Transformer reinforcement learning |
| `peft` | Parameter-efficient fine-tuning |

## 17.3 MCP Server Dependencies (Not Installed)
| Package | Command |
|---------|---------|
| `@modelcontextprotocol/server-github` | `npx -y @modelcontextprotocol/server-github@latest` |
| `@upstash/context7-mcp` | `npx -y @upstash/context7-mcp@latest` |
| `@playwright/mcp` | `npx -y @playwright/mcp@latest` |
| `@modelcontextprotocol/server-filesystem` | `npx -y @modelcontextprotocol/server-filesystem` |
| `mcp-server-fetch` | `uvx mcp-server-fetch` |
| `@modelcontextprotocol/server-sequential-thinking` | `npx -y @modelcontextprotocol/server-sequential-thinking` |

---

# 18. KNOWN ISSUES & TODOs

## 18.1 Critical Issues (Fixed)
| Issue | Status | Resolution |
|-------|--------|------------|
| Agent SQL column mismatch | ✅ FIXED | Changed `agent_id` to `id` |
| Agent send quote handling | ✅ FIXED | Added strip_quotes() + name lookup |
| Blueprint/app route collision | ✅ FIXED | Renamed legacy routes to `_legacy` |
| MCP subprocess approach | ✅ FIXED | Created proper JSON-RPC client |

## 18.2 Active Issues
| Issue | Severity | Description |
|-------|----------|-------------|
| ChromaDB unavailable | MEDIUM | System sqlite3 3.34.1 < 3.35.0 required |
| MCP servers not installed | MEDIUM | Need npm/uvx to install MCP servers |
| Training dependencies missing | LOW | unsloth/trl/datasets not installed |
| 19 empty module files | LOW | Stub files at 0 bytes need implementation |

## 18.3 TODO Items

### High Priority
- [ ] Install MCP servers for full MCP functionality
- [ ] Upgrade system sqlite3 to 3.35.0+ for ChromaDB
- [ ] Implement empty Blue Team submodules
- [ ] Add comprehensive test suite

### Medium Priority
- [ ] Port 37 missing API endpoints from v4.0
- [ ] Add WebSocket authentication
- [ ] Implement podman sandbox for C/Java
- [ ] Add model versioning and rollback

### Low Priority
- [ ] Add Prometheus metrics endpoint
- [ ] Implement distributed agent mode
- [ ] Add vector database clustering
- [ ] Create Grafana dashboards

## 18.4 Empty Files Requiring Implementation
```
agents/tools.py (0 bytes)
agents/memory.py (0 bytes)
blueteam/detection/__init__.py (0 bytes)
blueteam/detection/engine.py (0 bytes)
blueteam/detection/rules.py (0 bytes)
blueteam/intel/__init__.py (0 bytes)
blueteam/intel/ioc.py (0 bytes)
blueteam/intel/attck.py (0 bytes)
blueteam/ir/__init__.py (0 bytes)
blueteam/ir/incident.py (0 bytes)
blueteam/ir/playbooks.py (0 bytes)
blueteam/logs/__init__.py (0 bytes)
blueteam/logs/ingestion.py (0 bytes)
blueteam/logs/parser.py (0 bytes)
blueteam/database.py (0 bytes)
security/audit/__init__.py (0 bytes)
security/crypto/__init__.py (0 bytes)
security/mfa/__init__.py (0 bytes)
security/session/__init__.py (0 bytes)
audit/__init__.py (0 bytes)
```

---

# 19. OPERATIONAL PROCEDURES

## 19.1 Starting the System
```bash
cd /opt/codex-swarm/command-post
python -c "from backend.app_integrated import app; app.run(host='0.0.0.0', port=18010, debug=False, threaded=True)"
```

## 19.2 API Authentication
```bash
# Using legacy token
curl -H "Authorization: Bearer REPLACE_WITH_ENV_NEXUS_TOKEN" \
  http://localhost:18010/api/agents

# Using JWT (after login)
curl -X POST http://localhost:18010/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"codename": "OPERATOR", "password": "token-here"}'
```

## 19.3 Creating an Agent
```bash
curl -X POST http://localhost:18010/api/agents/agents \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "RESEARCH-1",
    "persona": "Research Analyst",
    "model": "llama3.3",
    "clearance": "SECRET"
  }'
```

## 19.4 Sending Message to Agent
```bash
curl -X POST http://localhost:18010/api/agents/agents/AGENT_ID/message \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze this data and provide summary"}'
```

## 19.5 Emergency Procedures

### Kill All C2 Sessions
```bash
curl -X POST http://localhost:18010/api/redteam/c2/kill_switch \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirmation": "KILL_ALL_SESSIONS"}'
```

### Verify Audit Chain Integrity
```python
from audit.tamper_evident import get_tamper_evident_audit
audit = get_tamper_evident_audit()
is_valid, errors = audit.verify_integrity()
print(f"Integrity: {'PASS' if is_valid else 'FAIL'}")
```

---

# APPENDIX A: MITRE ATT&CK TECHNIQUES

The system implements detection for the following MITRE ATT&CK techniques:

| Technique | Name | Tactic |
|-----------|------|--------|
| T1110 | Brute Force | Credential Access |
| T1068 | Exploitation for Privilege Escalation | Privilege Escalation |
| T1041 | Exfiltration Over C2 Channel | Exfiltration |
| T1046 | Network Service Scanning | Discovery |
| T1059 | Command and Scripting Interpreter | Execution |
| T1021.001 | Remote Desktop Protocol | Lateral Movement |
| T1021.002 | SMB/Windows Admin Shares | Lateral Movement |
| T1027 | Obfuscated Files or Information | Defense Evasion |
| T1115 | Clipboard Data | Collection |
| T1053 | Scheduled Task/Job | Execution |
| T1547 | Boot or Logon Autostart Execution | Persistence |
| T1562 | Impair Defenses | Defense Evasion |
| T1070 | Indicator Removal | Defense Evasion |
| T1190 | Exploit Public-Facing Application | Initial Access |
| T1189 | Drive-by Compromise | Initial Access |
| T1083 | File and Directory Discovery | Discovery |

---

# APPENDIX B: CLEARANCE LEVELS

| Level | Value | Description |
|-------|-------|-------------|
| UNCLASSIFIED | 0 | Public information |
| CONFIDENTIAL | 1 | Sensitive information |
| SECRET | 2 | National security info |
| TOP SECRET | 3 | Highly sensitive |
| TS/SCI | 4 | Sensitive Compartmented |
| TS/SCI/NOFORN | 5 | US Eyes Only |

---

**END OF DOCUMENT**

*This document is classified TOP SECRET//SCI//NOFORN*
*Authorized personnel only*
*ORDL Cyber Operations Division*
