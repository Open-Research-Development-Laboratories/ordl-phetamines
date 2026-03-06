# ORDL Podman Container Infrastructure

## Classification: TOP SECRET//SCI//NOFORN

This directory contains Podman-based containerization for the ORDL Command Post.

### Why Podman?

- **Rootless by default** - Enhanced security for TS/SCI environments
- **Docker-compatible** - Uses same CLI commands
- **systemd integration** - Native service management
- **No daemon required** - Direct container management

### Quick Start

```bash
# Build images
./build.sh

# Deploy stack
./deploy.sh

# Or manually:
podman-compose up -d
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| Ollama | 11434 | LLM inference server |
| Router | 18000 | AI request router |
| Command Post | 18010 | Main application |

### Files

- `Containerfile.command-post` - Main application container
- `Containerfile.router` - Router service container
- `podman-compose.yml` - Multi-service orchestration
- `build.sh` - Build all images
- `deploy.sh` - Deploy stack
- `.containerignore` - Build exclusions
