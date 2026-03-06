#!/bin/bash
# =============================================================================
# ORDL PODMAN DEPLOY SCRIPT
# =============================================================================
# Classification: TOP SECRET//SCI//NOFORN
# Purpose: Deploy full ORDL stack with Podman
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           ORDL PODMAN DEPLOYMENT                                 ║"
echo "║                                                                  ║"
echo "║              Classification: TOP SECRET//NOFORN                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${YELLOW}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }

log_info "Starting deployment..."

# Deploy with podman-compose
cd "$SCRIPT_DIR"
podman-compose up -d

echo ""
log_ok "Deployment complete!"
echo ""
echo -e "${CYAN}Services:${NC}"
echo "  Ollama:       http://localhost:11434"
echo "  Router:       http://localhost:18000"
echo "  Command Post: http://localhost:18010"
echo ""
echo -e "${CYAN}Commands:${NC}"
echo "  View logs:  podman-compose logs -f"
echo "  Stop:       podman-compose down"
echo "  Status:     podman ps"
