# ORDL Command Post - Java 21 Sandbox Image
# Hardened container for secure Java code execution

FROM eclipse-temurin:21-jdk-alpine

# Security: Create non-root user
RUN addgroup -g 1000 -S ordlrunner && \
    adduser -u 1000 -S ordlrunner -G ordlrunner -s /sbin/nologin -h /tmp

# Install minimal dependencies
RUN apk add --no-cache \
    bash \
    coreutils

# Set working directory
WORKDIR /tmp

# Security: Set restrictive permissions
RUN chmod 755 /tmp && \
    chown ordlrunner:ordlrunner /tmp

# Create compilation and execution script
RUN cat > /usr/local/bin/compile_and_run.sh << 'EOF'
#!/bin/bash
set -euo pipefail

SOURCE_FILE="$1"
CLASS_NAME="${2:-Main}"
TIMEOUT_SECS="${3:-30}"
JVM_OPTS="${4:--Xmx512m -Xms64m}"

# Security: Validate source file exists
if [[ ! -f "$SOURCE_FILE" ]]; then
    echo "Error: Source file not found: $SOURCE_FILE" >&2
    exit 1
fi

# Security: Validate class name (must be valid Java identifier)
if [[ ! "$CLASS_NAME" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "Error: Invalid class name: $CLASS_NAME" >&2
    exit 1
fi

# Compile with strict warnings
echo "Compiling $SOURCE_FILE..."
javac -Xlint:all -Werror -d /tmp "$SOURCE_FILE" 2>&1

# Check if main class file was created
if [[ ! -f "/tmp/${CLASS_NAME}.class" ]]; then
    echo "Error: Compiled class not found. Ensure public class is named: $CLASS_NAME" >&2
    exit 1
fi

# Execute with timeout and resource limits
echo "Running program..."
timeout --signal=KILL "$TIMEOUT_SECS" java $JVM_OPTS -cp /tmp "$CLASS_NAME" 2>&1 || {
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

# Security: JVM security properties
ENV HOME=/tmp \
    TMPDIR=/tmp \
    JAVA_TOOL_OPTIONS="-Djava.security.egd=file:/dev/urandom"

# Default command
CMD ["java", "--version"]

# Labels
LABEL org.ordl.component="sandbox" \
      org.ordl.language="java" \
      org.ordl.version="21" \
      org.ordl.security.level="hardened"
