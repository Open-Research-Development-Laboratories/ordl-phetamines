# ORDL Command Post - Go 1.21 Sandbox Image
# Hardened container for secure Go code execution

FROM golang:1.21-alpine

# Security: Create non-root user
RUN addgroup -g 1000 -S ordlrunner && \
    adduser -u 1000 -S ordlrunner -G ordlrunner -s /sbin/nologin -h /tmp

# Install minimal dependencies
RUN apk add --no-cache \
    git \
    coreutils \
    time

# Set working directory
WORKDIR /tmp

# Initialize Go module for sandbox
RUN go mod init ordl/sandbox 2>/dev/null || true

# Pre-download commonly used packages
RUN go get -d \
    golang.org/x/exp/slices \
    golang.org/x/exp/maps 2>/dev/null || true

# Create compilation and execution script
RUN cat > /usr/local/bin/compile_and_run.sh << 'EOF'
#!/bin/sh
set -eu

SOURCE_FILE="$1"
OUTPUT_NAME="${2:-program}"
TIMEOUT_SECS="${3:-30}"
BUILD_FLAGS="${4:-}"

# Validate source file exists
if [ ! -f "$SOURCE_FILE" ]; then
    echo "Error: Source file not found: $SOURCE_FILE" >&2
    exit 1
fi

# Security: Validate output name
if echo "$OUTPUT_NAME" | grep -qE '[/.\\]'; then
    echo "Error: Invalid output name" >&2
    exit 1
fi

# Copy source to build directory
mkdir -p /tmp/build
cp "$SOURCE_FILE" /tmp/build/main.go

# Initialize module if needed
if [ ! -f /tmp/build/go.mod ]; then
    cd /tmp/build && go mod init sandbox 2>/dev/null || true
fi

cd /tmp/build

# Build with security flags
echo "Building Go program..."
go build -o "/tmp/$OUTPUT_NAME" \
    -ldflags="-s -w" \
    -trimpath \
    $BUILD_FLAGS \
    main.go 2>&1

echo "Running program..."
timeout --signal=KILL "$TIMEOUT_SECS" "/tmp/$OUTPUT_NAME" 2>&1 || {
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ] || [ $EXIT_CODE -eq 137 ]; then
        echo "Error: Program timed out after ${TIMEOUT_SECS}s" >&2
    fi
    exit $EXIT_CODE
}
EOF

RUN chmod +x /usr/local/bin/compile_and_run.sh

# Security: Set restrictive permissions
RUN chmod 755 /tmp && \
    chown -R ordlrunner:ordlrunner /tmp

# Switch to non-root user
USER ordlrunner

# Security: Environment variables
ENV HOME=/tmp \
    TMPDIR=/tmp \
    GOPATH=/tmp/go \
    GOCACHE=/tmp/.cache/go-build \
    GOMODCACHE=/tmp/go/pkg/mod \
    GOFLAGS="-buildvcs=false"

# Default command
CMD ["go", "version"]

# Labels
LABEL org.ordl.component="sandbox" \
      org.ordl.language="go" \
      org.ordl.version="1.21" \
      org.ordl.security.level="hardened"
