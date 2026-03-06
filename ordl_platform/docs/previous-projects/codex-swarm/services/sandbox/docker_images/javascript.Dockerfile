# ORDL Command Post - JavaScript (Node.js 20) Sandbox Image
# Hardened container for secure JavaScript/Node.js code execution

FROM node:20-alpine

# Security: Create non-root user
RUN addgroup -g 1000 -S ordlrunner && \
    adduser -u 1000 -S ordlrunner -G ordlrunner -s /sbin/nologin -h /tmp

# Install minimal dependencies
RUN apk add --no-cache \
    coreutils \
    time

# Set working directory
WORKDIR /tmp

# Security: Set restrictive permissions
RUN chmod 755 /tmp && \
    chown ordlrunner:ordlrunner /tmp

# Create a restricted package.json for sandbox environment
RUN cat > /tmp/package.json << 'EOF'
{
  "name": "ordl-sandbox",
  "version": "1.0.0",
  "private": true,
  "description": "ORDL Command Post JavaScript Sandbox",
  "dependencies": {}
}
EOF

# Pre-install commonly used packages (safe ones only)
RUN npm install --prefix /tmp \
    lodash@4.17.21 \
    moment@2.29.4 \
    axios@1.6.0 2>&1 | tail -5

# Create execution wrapper script
RUN cat > /usr/local/bin/run_node.sh << 'EOF'
#!/bin/sh
set -eu

SCRIPT_FILE="$1"
TIMEOUT_SECS="${2:-30}"
NODE_OPTS="${3:---max-old-space-size=512}"

# Validate script file exists
if [ ! -f "$SCRIPT_FILE" ]; then
    echo "Error: Script file not found: $SCRIPT_FILE" >&2
    exit 1
fi

# Execute with timeout
echo "Running Node.js script..."
timeout --signal=KILL "$TIMEOUT_SECS" node $NODE_OPTS "$SCRIPT_FILE" 2>&1 || {
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ] || [ $EXIT_CODE -eq 137 ]; then
        echo "Error: Script timed out after ${TIMEOUT_SECS}s" >&2
    fi
    exit $EXIT_CODE
}
EOF

RUN chmod +x /usr/local/bin/run_node.sh

# Switch to non-root user
USER ordlrunner

# Security: Environment variables
ENV HOME=/tmp \
    TMPDIR=/tmp \
    NODE_ENV=production \
    NPM_CONFIG_CACHE=/tmp/.npm \
    npm_config_cache=/tmp/.npm

# Default command
CMD ["node", "--version"]

# Labels
LABEL org.ordl.component="sandbox" \
      org.ordl.language="javascript" \
      org.ordl.version="20" \
      org.ordl.security.level="hardened"
