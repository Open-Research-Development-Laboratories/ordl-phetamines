# ORDL Command Post v6.0.0

## Open Research and Development Laboratories - AI Operations Center

**Classification:** TOP SECRET//SCI//NOFORN

---

## Overview

The ORDL Command Post is a military-grade AI operations center providing:

- **AI Request Routing** - Intelligent model selection and load balancing
- **Blue Team Security** - Real-time detection, incident response, threat intelligence
- **Agent Orchestration** - Multi-agent system with memory and tool integration
- **MCP Integration** - 7+ MCP servers for extended capabilities

---

## Quick Start

```bash
# Clone and enter directory
cd /opt/codex-swarm

# Run health check
./bin/health-check.sh

# Start the system
./bin/start-ordl.sh

# Or with Podman (recommended for production)
cd podman && ./deploy.sh
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      ORDL COMMAND POST                       │
├─────────────────────────────────────────────────────────────┤
│  Web UI (Port 18010)                                         │
│  ├─ API Server (Flask/FastAPI hybrid)                       │
│  ├─ Blue Team Security                                      │
│  │  ├─ Detection Engine (20+ rules)                         │
│  │  ├─ Log Ingestion (multi-source)                         │
│  │  ├─ Incident Response (playbooks)                        │
│  │  └─ Threat Intelligence (IOCs, ATT&CK)                   │
│  ├─ Agent System                                            │
│  │  ├─ Agent Manager (lifecycle)                            │
│  │  ├─ Memory Store (vector DB)                             │
│  │  └─ Tool Registry (10+ tools)                            │
│  └─ MCP Integration (7 servers)                             │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  AI Router (Port 18000)                                      │
│  ├─ Model Selection (quality/speed/balanced)                │
│  ├─ Load Balancing                                          │
│  └─ Health Monitoring                                       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  Ollama LLM Server (Port 11434)                              │
│  ├─ Model Management                                        │
│  ├─ Inference Engine                                        │
│  └─ Local AI Execution                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
ordl/
├── command-post/           # Main application
│   ├── backend/           # Flask/FastAPI server
│   ├── blueteam/          # Security operations
│   │   ├── detection/     # Detection engine & rules
│   │   ├── logs/          # Log ingestion & parsing
│   │   ├── ir/            # Incident response
│   │   └── intel/         # Threat intelligence
│   ├── agents/            # Agent management
│   ├── mcp_integration/   # MCP client
│   └── data/              # Database & uploads
├── router/                # AI request router
├── podman/                # Podman containers
├── tests/                 # Test suite
└── bin/                   # Helper scripts
```

---

## Features

### Blue Team Security

| Module | Description |
|--------|-------------|
| Detection Engine | Real-time rule-based analysis with 20+ MITRE ATT&CK rules |
| Log Ingestion | Multi-source (files, syslog, APIs, cloud) with real-time tail |
| Log Parsers | 8 formats: Syslog, JSON, Apache, Windows EVTX, CloudTrail, K8s, Suricata, CSV |
| Incident Management | Full lifecycle with timeline, IOC/asset tracking |
| Response Playbooks | Automated response with 4 built-in templates |
| IOC Management | 10 indicator types, STIX 2.1 import/export |
| ATT&CK Framework | 42 techniques, 14 tactics, coverage analysis |

### AI Capabilities

- **Model Routing** - Automatic quality/speed/balanced mode selection
- **Agent System** - Multi-agent orchestration with memory
- **MCP Integration** - GitHub, Context7, Playwright, SSH, Filesystem, Sequential Thinking, Fetch

---

## Requirements

- Python 3.9+
- Node.js 20+ (for MCP servers)
- Podman (optional, for containerized deployment)

---

## Installation

### Native Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r command-post/requirements.txt

# Install MCP servers
./bin/install-mcp-servers.sh
```

### Podman Installation

```bash
# Build images
cd podman && ./build.sh

# Deploy
./deploy.sh
```

---

## Usage

### Starting the System

```bash
# Native mode
./bin/start-ordl.sh

# Podman mode
cd podman && podman-compose up -d
```

### Accessing Services

| Service | URL |
|---------|-----|
| Web UI | http://localhost:18010/static/index.html |
| API | http://localhost:18010 |
| Router | http://localhost:18000 |
| Ollama | http://localhost:11434 |

---

## Development

### Running Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# With coverage
pytest --cov=command-post --cov=router
```

### Code Quality

```bash
# Linting
ruff check command-post/ router/

# Type checking
mypy command-post/ router/

# Security scan
bandit -r command-post/ router/
```

---

## Security

This system is designed for TOP SECRET//SCI//NOFORN environments:

- Rootless Podman containers
- JWT authentication with PyOTP 2FA
- Clearance level access control (UNCLASSIFIED → TS/SCI/NOFORN)
- Post-quantum cryptography ready
- 100% test coverage target

---

## License

**Classification:** TOP SECRET//SCI//NOFORN

Unauthorized access is a federal offense under 18 U.S.C. § 1030.

---

## Contact

**Open Research and Development Laboratories (ORDL)**
- Classification: ORDL-SOVEREIGN
- Version: 6.0.0
- Status: OPERATIONAL
