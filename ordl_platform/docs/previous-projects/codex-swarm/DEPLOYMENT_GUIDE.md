# ORDL Command Post v6.0.0 - Deployment & Debug Guide

## Phase 1: Environment Verification

### Step 1.1: Check Python Environment
```bash
cd /opt/codex-swarm
python3 --version  # Need 3.9+
which python3
ls -la venv/  # Check if venv exists
```

### Step 1.2: Activate Virtual Environment
```bash
source venv/bin/activate
which python3  # Should show venv path
pip --version
```

### Step 1.3: Install Core Dependencies
```bash
pip install flask flask-cors flask-limiter requests psutil
pip install chromadb sentence-transformers  # Optional
pip install pyjwt pyotp bcrypt
pip install pytest pytest-asyncio
```

## Phase 2: Static Analysis (Before Runtime)

### Step 2.1: Import Verification
```bash
cd /opt/codex-swarm/command-post
python3 -c "
import sys
sys.path.insert(0, '.')
print('Testing imports...')
try:
    from backend.app_integrated import app
    print('✓ Main app imports OK')
except Exception as e:
    print(f'✗ App import failed: {e}')

try:
    from blueteam.detection.engine import DetectionEngine
    print('✓ Detection engine OK')
except Exception as e:
    print(f'✗ Detection engine: {e}')

try:
    from blueteam.logs.ingestion import LogIngestionEngine
    print('✓ Log ingestion OK')
except Exception as e:
    print(f'✗ Log ingestion: {e}')

try:
    from blueteam.logs.parser import ParserRegistry
    print('✓ Log parser OK')
except Exception as e:
    print(f'✗ Log parser: {e}')

try:
    from blueteam.ir.incident import IncidentManager
    print('✓ Incident manager OK')
except Exception as e:
    print(f'✗ Incident manager: {e}')

try:
    from blueteam.ir.playbooks import PlaybookEngine
    print('✓ Playbook engine OK')
except Exception as e:
    print(f'✗ Playbook engine: {e}')

try:
    from blueteam.intel.ioc import IOCManager
    print('✓ IOC manager OK')
except Exception as e:
    print(f'✗ IOC manager: {e}')

try:
    from blueteam.intel.attck import AttackFramework
    print('✓ ATT&CK framework OK')
except Exception as e:
    print(f'✗ ATT&CK framework: {e}')
"
```

### Step 2.2: Syntax Check All New Modules
```bash
cd /opt/codex-swarm
python3 -m py_compile command-post/blueteam/logs/ingestion.py
python3 -m py_compile command-post/blueteam/logs/parser.py
python3 -m py_compile command-post/blueteam/ir/incident.py
python3 -m py_compile command-post/blueteam/ir/playbooks.py
python3 -m py_compile command-post/blueteam/intel/ioc.py
python3 -m py_compile command-post/blueteam/intel/attck.py
echo "Syntax check complete"
```

## Phase 3: Database Initialization

### Step 3.1: Create Data Directories
```bash
mkdir -p /opt/codex-swarm/command-post/data
mkdir -p /opt/codex-swarm/command-post/uploads
mkdir -p /opt/codex-swarm/command-post/logs
```

### Step 3.2: Initialize Databases
```bash
cd /opt/codex-swarm/command-post
python3 -c "
import sqlite3
import os

# Detection database
conn = sqlite3.connect('data/detection.db')
conn.close()
print('✓ Detection DB initialized')

# Main app database
conn = sqlite3.connect('data/nexus.db')
conn.close()
print('✓ Nexus DB initialized')
"
```

## Phase 4: Router Service Startup

### Step 4.1: Check Router
```bash
cd /opt/codex-swarm/router
python3 -c "from router import app; print('Router imports OK')"
```

### Step 4.2: Start Router (Background)
```bash
cd /opt/codex-swarm/router
export ROUTER_BIND=0.0.0.0
export ROUTER_PORT=18000
python3 router.py > /tmp/router.log 2>&1 &
ROUTER_PID=$!
echo "Router PID: $ROUTER_PID"
sleep 3
curl -s http://localhost:18000/health || echo "Router not responding"
```

## Phase 5: Command Post Startup

### Step 5.1: Set Environment Variables
```bash
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export NEXUS_TOKEN="REPLACE_WITH_ENV_NEXUS_TOKEN"
export DATA_DIR="/opt/codex-swarm/command-post/data"
export UPLOADS_DIR="/opt/codex-swarm/command-post/uploads"
export ROUTER_URL="http://localhost:18000"
```

### Step 5.2: Start Command Post (Background)
```bash
cd /opt/codex-swarm/command-post/backend
python3 app_integrated.py > /tmp/command-post.log 2>&1 &
CP_PID=$!
echo "Command Post PID: $CP_PID"
sleep 5
curl -s http://localhost:18010/health || echo "Command Post not responding"
```

## Phase 6: Deep Debug Session

### Step 6.1: Check Logs
```bash
echo "=== ROUTER LOG ==="
tail -50 /tmp/router.log

echo "=== COMMAND POST LOG ==="
tail -100 /tmp/command-post.log
```

### Step 6.2: API Endpoints Test
```bash
# Health checks
curl -s http://localhost:18000/health | python3 -m json.tool
curl -s http://localhost:18010/health | python3 -m json.tool

# Test detection engine
curl -s http://localhost:18010/api/v1/blueteam/status || echo "BlueTeam API error"
```

### Step 6.3: Database Connectivity
```bash
cd /opt/codex-swarm/command-post
python3 -c "
import sqlite3
conn = sqlite3.connect('data/nexus.db')
cursor = conn.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table';\")
tables = cursor.fetchall()
print('Tables:', tables)
conn.close()
"
```

## Phase 7: Unit Test Execution

```bash
cd /opt/codex-swarm
pytest tests/unit -v --tb=short 2>&1 | head -100
```

## Troubleshooting Quick Reference

### Import Errors
- Check virtual environment is activated
- Install missing packages with pip
- Check PYTHONPATH includes command-post/

### Database Errors
- Ensure data/ directory exists and is writable
- Check SQLite version (need 3.35+)

### Port Conflicts
- Check if ports 18000, 18010 are in use: `lsof -i :18000`
- Kill existing processes if needed

### Permission Errors
- Ensure user owns /opt/codex-swarm directory
- Check write permissions on data/, uploads/, logs/
