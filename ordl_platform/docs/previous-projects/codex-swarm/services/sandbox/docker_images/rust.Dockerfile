# ORDL Command Post - Rust 1.75 Sandbox Image
# Hardened container for secure Rust code execution

FROM rust:1.75-slim-bookworm

# Security: Create non-root user
RUN groupadd -r ordlrunner -g 1000 && \
    useradd -r -g ordlrunner -u 1000 -s /sbin/nologin -d /tmp ordlrunner

# Install minimal dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    libssl-dev \
    ca-certificates \
    time \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /tmp

# Create Cargo project structure for sandbox
RUN mkdir -p /tmp/rust_sandbox/src

RUN cat > /tmp/rust_sandbox/Cargo.toml << 'EOF'
[package]
name = "sandbox"
version = "1.0.0"
edition = "2021"

[profile.release]
opt-level = 2
lto = true
codegen-units = 1
strip = true

[profile.dev]
opt-level = 0
debug = false
EOF

RUN echo 'fn main() {}' > /tmp/rust_sandbox/src/main.rs

# Pre-download common crates for faster compilation
RUN cd /tmp/rust_sandbox && \
    cargo fetch 2>/dev/null || true

# Create compilation and execution script
RUN cat > /usr/local/bin/compile_and_run.sh << 'EOF'
#!/bin/bash
set -euo pipefail

SOURCE_FILE="$1"
TIMEOUT_SECS="${2:-60}"
BUILD_MODE="${3:-release}"

# Validate source file exists
if [[ ! -f "$SOURCE_FILE" ]]; then
    echo "Error: Source file not found: $SOURCE_FILE" >&2
    exit 1
fi

# Copy source to project
mkdir -p /tmp/build/src
cp "$SOURCE_FILE" /tmp/build/src/main.rs

# Copy Cargo files if not exists
if [[ ! -f /tmp/build/Cargo.toml ]]; then
    cp /tmp/rust_sandbox/Cargo.toml /tmp/build/
fi

cd /tmp/build

# Build with timeout
echo "Compiling Rust program (mode: $BUILD_MODE)..."
if [[ "$BUILD_MODE" == "release" ]]; then
    timeout --signal=KILL 120 cargo build --release 2>&1
    BINARY="/tmp/build/target/release/sandbox"
else
    timeout --signal=KILL 120 cargo build 2>&1
    BINARY="/tmp/build/target/debug/sandbox"
fi

echo "Running program..."
timeout --signal=KILL "$TIMEOUT_SECS" "$BINARY" 2>&1 || {
    EXIT_CODE=$?
    if [[ $EXIT_CODE -eq 124 || $EXIT_CODE -eq 137 ]]; then
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
    CARGO_HOME=/tmp/.cargo \
    RUSTUP_HOME=/tmp/.rustup \
    CARGO_TARGET_DIR=/tmp/build/target \
    RUST_BACKTRACE=0

# Default command
CMD ["rustc", "--version"]

# Labels
LABEL org.ordl.component="sandbox" \
      org.ordl.language="rust" \
      org.ordl.version="1.75" \
      org.ordl.security.level="hardened"
