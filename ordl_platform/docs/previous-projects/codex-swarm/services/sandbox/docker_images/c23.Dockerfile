# ORDL Command Post - C23 Sandbox Image
# Hardened container for secure C code execution with C23 standard

FROM gcc:13-bookworm

# Security: Create non-root user
RUN groupadd -r ordlrunner -g 1000 && \
    useradd -r -g ordlrunner -u 1000 -s /sbin/nologin -d /tmp ordlrunner

# Install minimal dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libc6-dev \
    make \
    time \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /tmp

# Security: Set restrictive permissions
RUN chmod 755 /tmp && \
    chown ordlrunner:ordlrunner /tmp

# Create compilation script
RUN cat > /usr/local/bin/compile_and_run.sh << 'EOF'
#!/bin/bash
set -euo pipefail

SOURCE_FILE="$1"
OUTPUT_NAME="${2:-program}"
COMPILER_FLAGS="${3:--std=c23 -O2 -Wall -Wextra -Werror}"
TIMEOUT_SECS="${4:-30}"

# Security: Validate source file exists
if [[ ! -f "$SOURCE_FILE" ]]; then
    echo "Error: Source file not found: $SOURCE_FILE" >&2
    exit 1
fi

# Security: Validate output name (prevent directory traversal)
if [[ "$OUTPUT_NAME" =~ [/.\] ]]; then
    echo "Error: Invalid output name" >&2
    exit 1
fi

# Compile with C23 standard and security flags
echo "Compiling with flags: $COMPILER_FLAGS"
gcc $COMPILER_FLAGS \
    -D_FORTIFY_SOURCE=2 \
    -fstack-protector-strong \
    -fPIE \
    -Wl,-z,relro,-z,now \
    -o "/tmp/$OUTPUT_NAME" "$SOURCE_FILE" 2>&1

# Execute with timeout and resource limits
echo "Running program..."
timeout --signal=KILL "$TIMEOUT_SECS" "/tmp/$OUTPUT_NAME" 2>&1 || {
    EXIT_CODE=$?
    if [[ $EXIT_CODE -eq 124 || $EXIT_CODE -eq 137 ]]; then
        echo "Error: Program timed out after ${TIMEOUT_SECS}s" >&2
    fi
    exit $EXIT_CODE
}
EOF

RUN chmod +x /usr/local/bin/compile_and_run.sh

# Switch to non-root user
USER ordlrunner

# Security: Environment variables
ENV HOME=/tmp \
    TMPDIR=/tmp \
    GCC_COLORS=''

# Default command
CMD ["gcc", "--version"]

# Labels
LABEL org.ordl.component="sandbox" \
      org.ordl.language="c23" \
      org.ordl.version="gcc-13" \
      org.ordl.security.level="hardened"
