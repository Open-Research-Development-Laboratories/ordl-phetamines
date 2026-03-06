# ORDL Command Post - Code Sandbox Service

**Classification:** TOP SECRET//NOFORN//SCI  
**Version:** 1.0.0  
**Status:** Production Ready

A military-grade, Docker-based secure code execution environment supporting multiple programming languages with comprehensive security isolation.

---

## Overview

The ORDL Code Sandbox provides isolated execution environments for untrusted code across six programming languages. Each execution runs in a hardened Docker container with strict resource limits, syscall filtering, and network isolation.

## Features

### Supported Languages
- **Python 3.11** - With numpy, pandas, scikit-learn, matplotlib, and common ML packages
- **C23** - GCC 13 with C23 standard support
- **Java 21** - OpenJDK with modern Java features
- **JavaScript** - Node.js 20
- **Rust 1.75** - With Cargo build system
- **Go 1.21** - Full Go toolchain

### Security Features
- **Non-root container execution** - All containers run as unprivileged user
- **Seccomp syscall filtering** - Custom seccomp profile blocks dangerous syscalls
- **Resource limits** - CPU, memory, PID, and timeout constraints
- **Network isolation** - Per-clearance level network access controls
- **Read-only filesystem** - Except for `/tmp` directory
- **No new privileges** - Prevents privilege escalation
- **Capability dropping** - Minimal container capabilities

### Clearance Levels
| Level | Network | Description |
|-------|---------|-------------|
| `unclassified` | Isolated | No network access, restricted execution |
| `confidential` | Limited | DNS, HTTP/HTTPS only |
| `secret` | Standard | Normal network access |
| `top_secret` | Extended | Extended network capabilities |
| `ts_sci` | Full | Full network capabilities |
| `ts_sci_noforn` | Isolated | Reserved for restricted operations |

---

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Build Docker images
python build_images.py

# Verify images are available
python build_images.py --verify-only
```

### Basic Usage

```python
from services.sandbox import SandboxOrchestrator, Language, ClearanceLevel

# Execute code in sandbox
with SandboxOrchestrator() as sandbox:
    result = sandbox.execute(
        source_code='print("Hello, World!")',
        language=Language.PYTHON,
        clearance_level=ClearanceLevel.UNCLASSIFIED,
        timeout=30
    )
    
    print(f"Success: {result.success}")
    print(f"Output: {result.stdout}")
    print(f"Execution time: {result.execution_time:.2f}s")
```

### Convenience Function

```python
from services.sandbox import execute_code

result = execute_code(
    source_code='console.log("Hello from Node.js")',
    language='javascript',
    timeout=10
)
```

---

## API Reference

### SandboxOrchestrator

Main orchestrator for Docker-based code sandbox execution.

#### Constructor

```python
SandboxOrchestrator(
    docker_url: Optional[str] = None,          # Docker daemon URL
    seccomp_profile_path: Optional[str] = None, # Path to seccomp profile
    cleanup_on_exit: bool = True                # Auto-cleanup on exit
)
```

#### Methods

##### `execute()`

Execute source code in a sandboxed Docker container.

```python
result = sandbox.execute(
    source_code: str,                          # Code to execute
    language: Union[str, Language],            # Programming language
    clearance_level: ClearanceLevel = UNCLASSIFIED,
    timeout: Optional[int] = None,             # 1-300 seconds
    memory_limit: Optional[str] = None,        # e.g., "512m", "1g"
    network_isolated: bool = True,
    file_uploads: Optional[Dict[str, bytes]] = None,
    **kwargs                                    # Language-specific options
)
```

**Language-specific kwargs:**

- **C23**: `compiler_flags` - Custom GCC flags
- **Java**: `class_name` - Main class name (default: "Main")
- **Rust**: `build_mode` - "release" or "debug"

##### `health_check()`

Perform a health check on the sandbox system.

```python
health = sandbox.health_check()
# Returns: {'status': 'healthy', 'images_available': {...}, ...}
```

##### `get_container_stats()`

Get statistics about active containers.

```python
stats = sandbox.get_container_stats()
# Returns: {'active_containers': 0, 'container_ids': [], ...}
```

### ExecutionResult

Data class containing execution results.

```python
@dataclass
class ExecutionResult:
    success: bool              # Whether execution succeeded
    exit_code: int             # Process exit code
    stdout: str                # Standard output
    stderr: str                # Standard error
    execution_time: float      # Execution time in seconds
    memory_usage: int          # Memory usage in bytes
    cpu_usage: float           # CPU usage percentage
    container_id: str          # Docker container ID
    error_message: str         # Error message if failed
    timestamp: str             # ISO timestamp
    request_id: str            # Unique request ID
```

---

## Examples

### Python with File Upload

```python
code = '''
import json

with open('/tmp/data.json', 'r') as f:
    data = json.load(f)
    
print(f"Loaded {len(data)} items")
print(f"Sum: {sum(data.values())}")
'''

file_uploads = {
    'data.json': b'{"a": 1, "b": 2, "c": 3}'
}

result = sandbox.execute(
    source_code=code,
    language=Language.PYTHON,
    file_uploads=file_uploads
)
```

### C23 Compilation

```python
c_code = '''
#include <stdio.h>
#include <math.h>

int main() {
    double result = sqrt(2.0);
    printf("Square root of 2: %.10f\\n", result);
    return 0;
}
'''

result = sandbox.execute(
    source_code=c_code,
    language=Language.C23,
    compiler_flags="-std=c23 -O2 -lm"
)
```

### Java Execution

```python
java_code = '''
public class Calculator {
    public static void main(String[] args) {
        int sum = 0;
        for (int i = 1; i <= 100; i++) {
            sum += i;
        }
        System.out.println("Sum 1-100: " + sum);
    }
}
'''

result = sandbox.execute(
    source_code=java_code,
    language=Language.JAVA,
    class_name="Calculator"
)
```

### JavaScript with Timeout

```python
js_code = '''
const data = Array.from({length: 100}, (_, i) => i * i);
const sum = data.reduce((a, b) => a + b, 0);
console.log(`Sum of squares: ${sum}`);
'''

result = sandbox.execute(
    source_code=js_code,
    language=Language.JAVASCRIPT,
    timeout=5
)
```

### Rust Execution

```python
rust_code = '''
fn main() {
    let numbers: Vec<i32> = (1..=100).collect();
    let sum: i32 = numbers.iter().sum();
    println!("Sum 1-100: {}", sum);
    
    let squares: Vec<i32> = numbers.iter().map(|x| x * x).collect();
    println!("First 10 squares: {:?}", &squares[..10]);
}
'''

result = sandbox.execute(
    source_code=rust_code,
    language=Language.RUST,
    build_mode="release"
)
```

### Go Execution

```python
go_code = '''
package main

import "fmt"

func main() {
    sum := 0
    for i := 1; i <= 100; i++ {
        sum += i
    }
    fmt.Printf("Sum 1-100: %d\\n", sum)
}
'''

result = sandbox.execute(
    source_code=go_code,
    language=Language.GO
)
```

---

## Resource Limits

Default resource limits can be customized:

```python
from services.sandbox import ResourceLimits

limits = ResourceLimits(
    cpu_quota=200000,          # 2 CPUs
    mem_limit="1g",            # 1GB RAM
    mem_swap_limit="1g",       # No swap
    pids_limit=128,            # Max 128 processes
    timeout=60,                # 60 second timeout
    max_output_size=2*1024*1024  # 2MB output limit
)

config = SandboxConfig(
    language=Language.PYTHON,
    resource_limits=limits
)
```

---

## Security Configuration

### Custom Seccomp Profile

```python
from services.sandbox import SecurityOptions

security = SecurityOptions(
    cap_drop=['ALL'],
    cap_add=['KILL'],          # Minimal capabilities
    no_new_privileges=True,
    read_only=True,
    seccomp_profile='/path/to/custom-seccomp.json'
)
```

### Network Configuration

```python
# Disable network completely
result = sandbox.execute(
    source_code=code,
    language=Language.PYTHON,
    network_isolated=True
)

# Allow network (based on clearance level)
result = sandbox.execute(
    source_code=code,
    language=Language.PYTHON,
    clearance_level=ClearanceLevel.CONFIDENTIAL,
    network_isolated=False
)
```

---

## Docker Images

### Building Images

```bash
# Build all images
python build_images.py

# Build without cache
python build_images.py --no-cache

# Build in parallel
python build_images.py --parallel

# Verify images exist
python build_images.py --verify-only
```

### Image Details

| Image | Base | Size | Pre-installed |
|-------|------|------|---------------|
| `ordl-sandbox-python:3.11` | python:3.11-slim | ~500MB | numpy, pandas, scikit-learn, matplotlib |
| `ordl-sandbox-c23:gcc-13` | gcc:13-bookworm | ~400MB | GCC 13, libc-dev |
| `ordl-sandbox-java:21` | eclipse-temurin:21-jdk-alpine | ~300MB | OpenJDK 21 |
| `ordl-sandbox-javascript:20` | node:20-alpine | ~150MB | Node.js 20 |
| `ordl-sandbox-rust:1.75` | rust:1.75-slim | ~1GB | Rust toolchain, Cargo |
| `ordl-sandbox-go:1.21` | golang:1.21-alpine | ~300MB | Go toolchain |

---

## Testing

Run the built-in tests:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_python.py -v

# Run with coverage
python -m pytest tests/ --cov=services.sandbox --cov-report=html
```

Manual testing:

```bash
# Test Python execution
python sandbox.py
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    API / CLI Layer                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              SandboxOrchestrator                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Resource   │  │   Security  │  │   Network   │             │
│  │   Limits    │  │   Options   │  │    Config   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Docker Container (per execution)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Non-root User (ordlrunner)                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │   │
│  │  │   /tmp      │  │   Code      │  │   Output    │       │   │
│  │  │  (read-write)│  │  (read-only)│  │  (capture)  │       │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │   │
│  └──────────────────────────────────────────────────────────┘   │
│  Security: seccomp, no-new-privs, cap-drop=ALL                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Docker Connection Issues

```bash
# Check Docker daemon
sudo systemctl status docker

# Test Docker connection
docker version

# Set Docker host explicitly
export DOCKER_HOST=unix:///var/run/docker.sock
```

### Image Not Found

```bash
# Build missing images
python build_images.py

# Check available images
docker images | grep ordl-sandbox
```

### Timeout Issues

```python
# Increase timeout
result = sandbox.execute(
    source_code=code,
    language=Language.PYTHON,
    timeout=120  # Up to 300 seconds
)
```

### Memory Issues

```python
# Increase memory limit
result = sandbox.execute(
    source_code=code,
    language=Language.PYTHON,
    memory_limit="2g"
)
```

---

## Security Considerations

1. **Always use the lowest clearance level** necessary for the task
2. **Enable network isolation** when network access is not required
3. **Set appropriate timeouts** to prevent resource exhaustion
4. **Validate file uploads** - sandbox validates filenames but review content
5. **Monitor active containers** - use `get_container_stats()` for monitoring
6. **Review seccomp profile** - customize if needed for specific use cases

---

## License

**Classification:** TOP SECRET//NOFORN//SCI  
**Distribution:** Authorized personnel only

---

## Contact

ORDL Engineering Team  
Open Research & Development Laboratories
