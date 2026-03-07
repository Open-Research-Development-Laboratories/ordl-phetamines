# ORDL COMMAND POST v6.0.0 - QUICK REFERENCE
## Classification: TOP SECRET//SCI//NOFORN

---

## START THE SYSTEM
```bash
cd /opt/codex-swarm/command-post
python backend/app_integrated.py
```
Server runs on **http://localhost:18010**

---

## AUTHENTICATION

### Legacy Token (Always Works)
```
REPLACE_WITH_ENV_NEXUS_TOKEN
```

### API Header
```bash
-H "Authorization: Bearer TOKEN_HERE"
```

---

## CORE API ENDPOINTS

### Health
```bash
GET /health
```

### Agents
```bash
GET    /api/agents/agents           # List agents
POST   /api/agents/agents           # Create agent
GET    /api/agents/agents/<id>      # Get agent
DELETE /api/agents/agents/<id>      # Destroy agent
POST   /api/agents/agents/<id>/message  # Send message
GET    /api/agents/tools            # List tools
POST   /api/agents/tools/<name>/execute  # Execute tool
```

### Chat
```bash
POST /api/chat
Body: {"model": "llama-3.3-70b-versatile", "messages": [...]}
```

### Knowledge Base
```bash
POST /api/knowledge/ingest          # Add document
POST /api/knowledge/query           # Search
GET  /api/knowledge                 # List documents
```

### System
```bash
GET /api/system/status              # System metrics
GET /api/system/capabilities        # Available features
GET /api/system/events              # System events
```

---

## AGENT SYSTEM

### Create Agent
```bash
curl -X POST http://localhost:18010/api/agents/agents \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ALPHA-1",
    "persona": "System Architect",
    "model": "llama3.3",
    "clearance": "SECRET",
    "capabilities": ["coding", "architecture"]
  }'
```

### Send Message
```bash
curl -X POST http://localhost:18010/api/agents/agents/AGENT_ID/message \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Your message here"}'
```

### Available Tools (Built-in)
- `redteam_recon` - Reconnaissance
- `redteam_scan` - Vulnerability scan
- `redteam_payload` - Payload generation
- `blueteam_status` - SOC status
- `blueteam_alerts` - Security alerts
- `rag_search` - Knowledge search
- `rag_ingest` - Document ingestion
- `train_hardware` - Training info
- `system_time` - System time

### Tool Syntax in Messages
```
@tool_name(param1=value1, param2=value2)
```
Example:
```
Search our knowledge base: @rag_search(query=cybersecurity, top_k=5)
```

---

## RED TEAM API

### Status
```bash
GET /api/redteam/status
```

### Operations
```bash
GET  /api/redteam/operations
POST /api/redteam/operations        # Create operation
GET  /api/redteam/operations/<id>
```

### Reconnaissance
```bash
POST /api/redteam/recon/scan        # Port scan
GET  /api/redteam/recon/dns?domain=example.com
GET  /api/redteam/recon/subdomains?domain=example.com
```

### Scanning
```bash
POST /api/redteam/scan/service      # Service scan
POST /api/redteam/scan/web          # Web scan
GET  /api/redteam/scan/ssl?host=example.com
```

### Exploits
```bash
GET  /api/redteam/exploits          # List exploits
POST /api/redteam/exploits/<id>/check
POST /api/redteam/exploits/execute  # Run exploit
```

### Payloads
```bash
POST /api/redteam/payloads/generate/reverse_shell
GET  /api/redteam/payloads
```

### C2
```bash
GET  /api/redteam/c2/listeners
POST /api/redteam/c2/listeners      # Create listener
GET  /api/redteam/c2/sessions
POST /api/redteam/c2/kill_switch    # EMERGENCY
```

### Phishing
```bash
GET  /api/redteam/phishing/templates
GET  /api/redteam/phishing/campaigns
POST /api/redteam/phishing/campaigns
```

---

## BLUE TEAM API

### Status
```bash
GET /api/blueteam/status
```

### Alerts
```bash
GET /api/blueteam/alerts            # List alerts
GET /api/blueteam/alerts/<id>
PUT /api/blueteam/alerts/<id>/assign
PUT /api/blueteam/alerts/<id>/close
```

### Incidents
```bash
GET  /api/blueteam/incidents
POST /api/blueteam/incidents
GET  /api/blueteam/incidents/<id>
PUT  /api/blueteam/incidents/<id>/status
```

### IOCs
```bash
GET  /api/blueteam/iocs
POST /api/blueteam/iocs             # Add IOC
GET  /api/blueteam/iocs/<id>
DELETE /api/blueteam/iocs/<id>
```

### Log Ingestion
```bash
POST /api/blueteam/logs/ingest
GET  /api/blueteam/logs/search
```

### Detection Rules
```bash
GET    /api/blueteam/rules
POST   /api/blueteam/rules          # Create rule
PUT    /api/blueteam/rules/<id>/toggle
DELETE /api/blueteam/rules/<id>
```

---

## TRAINING API

### Hardware
```bash
GET /api/training/hardware
```

### Jobs
```bash
GET    /api/training/jobs
POST   /api/training/jobs           # Create job
GET    /api/training/jobs/<id>
DELETE /api/training/jobs/<id>      # Stop job
```

### Create Training Job
```bash
curl -X POST http://localhost:18010/api/training/jobs \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Fine-tune Job",
    "model": "llama-3.1-8b",
    "dataset_path": "dataset/name",
    "max_steps": 100
  }'
```

---

## RAG / KNOWLEDGE BASE

### Ingest Document
```bash
curl -X POST http://localhost:18010/api/knowledge/ingest \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Document content here...",
    "title": "Document Title",
    "category": "technical"
  }'
```

### Query
```bash
curl -X POST http://localhost:18010/api/knowledge/query \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the system architecture?",
    "top_k": 5
  }'
```

---

## SYSTEM DIRECTORIES

| Path | Purpose |
|------|---------|
| `/opt/codex-swarm/command-post/data/nexus.db` | Main database |
| `/opt/codex-swarm/command-post/data/audit_tamper_evident.db` | Audit chain |
| `/opt/codex-swarm/command-post/blueteam/blueteam.db` | Blue team DB |
| `/opt/codex-swarm/command-post/uploads/` | File uploads |
| `/opt/codex-swarm/command-post/models/` | Trained models |
| `/opt/codex-swarm/command-post/datasets/` | Training datasets |

---

## WEBSOCKET (Real-time Chat)

### Connection
```javascript
ws = new WebSocket('ws://localhost:18011');
```

### Authentication
```javascript
ws.send(JSON.stringify({
  type: 'auth',
  token: 'JWT_TOKEN_HERE'
}));
```

### Channels (by clearance)
- `general` - UNCLASSIFIED
- `tech` - CONFIDENTIAL
- `ops` - SECRET
- `intel` - TOP SECRET
- `sci` - TS/SCI
- `noforn` - TS/SCI/NOFORN

---

## CLEARANCE LEVELS

| Level | Value | Max Sessions | Idle Timeout |
|-------|-------|--------------|--------------|
| UNCLASSIFIED | 0 | 5 | 1 hour |
| CONFIDENTIAL | 1 | 3 | 30 min |
| SECRET | 2 | 2 | 15 min |
| TOP SECRET | 3 | 2 | 10 min |
| TS/SCI | 4 | 1 | 5 min |
| TS/SCI/NOFORN | 5 | 1 | 2 min |

---

## PYTHON MODULES

### Core Imports
```python
# Agent System
from agents import get_agent_manager, AgentConfig

# Security
from security.clearance import get_acl, ClearanceLevel
from security.session.manager import get_session_manager
from security.mfa.totp import get_mfa_manager
from security.audit.logger import get_audit_logger

# Red Team
from redteam import get_redteam_manager, OperationStatus, TargetType

# Blue Team
from blueteam import get_blueteam_manager, AlertSeverity, IncidentStatus

# RAG
from rag.vector_kb import get_knowledge_base

# Training
from training.unsloth_trainer import get_trainer

# MCP
from mcp_integration import get_mcp_registry

# Audit
from audit.tamper_evident import get_tamper_evident_audit, AuditEventType
```

---

## TROUBLESHOOTING

### System Won't Start
```bash
# Check Python path
export PYTHONPATH=/opt/codex-swarm/command-post:$PYTHONPATH

# Check database permissions
ls -la /opt/codex-swarm/command-post/data/

# Check for port conflicts
netstat -tlnp | grep 18010
```

### Agent Not Found Error
- Agent IDs may have quotes - use `strip_quotes()`
- Try lookup by name if ID fails
- Check `agents_db` keys: `list(agent_manager.agents.keys())`

### RAG Not Working
- ChromaDB blocked by sqlite3 version (< 3.35.0)
- Using SQLiteVectorStore fallback
- Install newer sqlite3 or use ChromaDB separately

### Training Not Available
- `unsloth` not installed (no GPU support)
- `trl` not installed
- Falls back to transformers (CPU only)

### MCP Tools Not Working
- MCP servers not installed
- Install with: `npx -y @modelcontextprotocol/server-github@latest`
- Or use `npm install -g` for each server

---

## EMERGENCY PROCEDURES

### Kill All C2 Sessions
```bash
curl -X POST http://localhost:18010/api/redteam/c2/kill_switch \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirmation": "KILL_ALL_SESSIONS"}'
```

### Verify Audit Integrity
```python
from audit.tamper_evident import get_tamper_evident_audit
audit = get_tamper_evident_audit()
is_valid, errors = audit.verify_integrity()
```

### Stop All Agents
```python
from agents import get_agent_manager
manager = get_agent_manager()
manager.shutdown()
```

---

## OPERATIONAL STATUS

| Component | Status |
|-----------|--------|
| Core Backend | ✅ OPERATIONAL |
| Agent System | ✅ OPERATIONAL |
| Security | ✅ OPERATIONAL |
| Red Team | ✅ OPERATIONAL |
| Blue Team | ✅ OPERATIONAL |
| RAG | ✅ OPERATIONAL (SQLite fallback) |
| LLM Bridge | ✅ OPERATIONAL |
| MCP | ⚠️ CLIENT READY (servers not installed) |
| Training | ⚠️ CPU FALLBACK |
| WebSocket | ✅ OPERATIONAL |

---

**ORDL Command Post v6.0.0**
**TOP SECRET//SCI//NOFORN**
