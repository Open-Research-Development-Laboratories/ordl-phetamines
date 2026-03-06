#!/bin/bash
# =============================================================================
# ORDL PODMAN BUILD SCRIPT
# =============================================================================
# Classification: TOP SECRET//SCI//NOFORN
# Purpose: Build all Podman images
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           ORDL PODMAN BUILD SEQUENCE                             ║"
echo "║                                                                  ║"
echo "║              Classification: TOP SECRET//NOFORN                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${YELLOW}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

cd "$PROJECT_ROOT"

# Check Podman
log_info "Checking Podman installation..."
if ! command -v podman &> /dev/null; then
    log_error "Podman not found. Please install Podman."
    exit 1
fi

PODMAN_VERSION=$(podman --version)
log_ok "Podman found: $PODMAN_VERSION"

# Check podman-compose
log_info "Checking podman-compose..."
if ! command -v podman-compose &> /dev/null; then
    log_error "podman-compose not found. Install with: pip install podman-compose"
    exit 1
fi
log_ok "podman-compose found"

# Build Router image
log_info "Building Router image..."
podman build -f podman/Containerfile.router -t ordl-router:latest .
log_ok "Router image built"

# Build Command Post image
log_info "Building Command Post image..."
podman build -f podman/Containerfile.command-post -t ordl-command-post:latest .
log_ok "Command Post image built"

# List images
echo ""
log_info "Built images:"
podman images | grep ordl-

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    BUILD COMPLETE                                ║"
echo "║                                                                  ║"
echo "║  To start: podman-compose -f podman/podman-compose.yml up -d     ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
