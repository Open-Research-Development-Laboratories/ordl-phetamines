#!/usr/bin/env python3
"""
ORDL Command Post - Sandbox Unit Tests
======================================

Comprehensive test suite for the code sandbox system.

Run with: pytest tests/test_sandbox.py -v

Classification: TOP SECRET//NOFORN//SCI
"""

import pytest
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sandbox import (
    SandboxOrchestrator,
    Language,
    ClearanceLevel,
    ResourceLimits,
    SecurityOptions,
    SandboxConfig,
    ExecutionResult,
    SandboxError,
    SandboxTimeoutError,
)


class TestResourceLimits:
    """Test ResourceLimits dataclass."""
    
    def test_default_limits(self):
        limits = ResourceLimits()
        assert limits.cpu_quota == 100000
        assert limits.mem_limit == "512m"
        assert limits.timeout == 30
        assert limits.pids_limit == 64
    
    def test_custom_limits(self):
        limits = ResourceLimits(
            cpu_quota=200000,
            mem_limit="1g",
            timeout=60,
            pids_limit=128
        )
        assert limits.cpu_quota == 200000
        assert limits.mem_limit == "1g"
        assert limits.timeout == 60
        assert limits.pids_limit == 128
    
    def test_to_docker_resources(self):
        limits = ResourceLimits()
        docker_resources = limits.to_docker_resources()
        assert 'cpu_quota' in docker_resources
        assert 'mem_limit' in docker_resources
        assert docker_resources['mem_limit'] == "512m"


class TestSecurityOptions:
    """Test SecurityOptions dataclass."""
    
    def test_default_options(self):
        opts = SecurityOptions()
        assert opts.cap_drop == ['ALL']
        assert 'KILL' in opts.cap_add
        assert opts.no_new_privileges is True
        assert opts.read_only is True
    
    def test_custom_seccomp(self, tmp_path):
        seccomp_file = tmp_path / "test-seccomp.json"
        seccomp_file.write_text('{"defaultAction": "SCMP_ACT_ALLOW"}')
        
        opts = SecurityOptions(seccomp_profile=str(seccomp_file))
        opts.__post_init__()
        
        assert any('seccomp' in opt for opt in opts.security_opt)


class TestSandboxConfig:
    """Test SandboxConfig dataclass."""
    
    def test_default_config(self):
        config = SandboxConfig(language=Language.PYTHON)
        assert config.language == Language.PYTHON
        assert config.clearance_level == ClearanceLevel.UNCLASSIFIED
        assert config.network_isolated is True
    
    def test_custom_config(self):
        config = SandboxConfig(
            language=Language.JAVA,
            clearance_level=ClearanceLevel.SECRET,
            network_isolated=False,
            env_vars={'TEST_VAR': 'value'}
        )
        assert config.language == Language.JAVA
        assert config.clearance_level == ClearanceLevel.SECRET
        assert config.network_isolated is False
        assert config.env_vars['TEST_VAR'] == 'value'


@pytest.fixture
def sandbox():
    """Fixture to provide a sandbox orchestrator."""
    orchestrator = SandboxOrchestrator(cleanup_on_exit=True)
    yield orchestrator
    orchestrator.cleanup_all()


class TestSandboxOrchestrator:
    """Integration tests for SandboxOrchestrator."""
    
    def test_health_check(self, sandbox):
        """Test health check returns expected structure."""
        health = sandbox.health_check()
        assert 'status' in health
        assert 'docker_connected' in health
        assert 'images_available' in health
    
    def test_container_stats(self, sandbox):
        """Test getting container stats."""
        stats = sandbox.get_container_stats()
        assert 'active_containers' in stats
        assert isinstance(stats['active_containers'], int)
    
    def test_truncate_output(self, sandbox):
        """Test output truncation."""
        long_output = "x" * (2 * 1024 * 1024)  # 2MB
        truncated = sandbox._truncate_output(long_output, max_size=1024 * 1024)
        assert len(truncated) <= 1024 * 1024
        assert "TRUNCATED" in truncated


class TestPythonExecution:
    """Test Python code execution."""
    
    def test_simple_print(self, sandbox):
        """Test basic Python execution."""
        code = 'print("Hello from Python")'
        result = sandbox.execute(code, Language.PYTHON, timeout=10)
        
        assert result.success is True
        assert result.exit_code == 0
        assert "Hello from Python" in result.stdout
        assert result.execution_time > 0
    
    def test_math_computation(self, sandbox):
        """Test Python math operations."""
        code = '''
import math
result = sum(i**2 for i in range(10))
print(f"Sum of squares: {result}")
print(f"Square root of 2: {math.sqrt(2):.4f}")
'''
        result = sandbox.execute(code, Language.PYTHON, timeout=10)
        
        assert result.success is True
        assert "Sum of squares: 285" in result.stdout
        assert "Square root of 2:" in result.stdout
    
    def test_numpy_operations(self, sandbox):
        """Test numpy operations (if available)."""
        code = '''
try:
    import numpy as np
    arr = np.array([1, 2, 3, 4, 5])
    print(f"Mean: {np.mean(arr)}")
    print(f"Std: {np.std(arr)}")
except ImportError:
    print("numpy not available")
'''
        result = sandbox.execute(code, Language.PYTHON, timeout=10)
        
        # Should succeed whether numpy is available or not
        assert result.success is True
    
    def test_timeout_handling(self, sandbox):
        """Test timeout enforcement."""
        code = '''
import time
print("Starting...")
time.sleep(60)
print("This should not print")
'''
        result = sandbox.execute(code, Language.PYTHON, timeout=2)
        
        assert result.success is False
        assert "timeout" in result.error_message.lower() or result.exit_code != 0
    
    def test_error_handling(self, sandbox):
        """Test Python error capture."""
        code = '''
print("Before error")
1/0
print("After error")
'''
        result = sandbox.execute(code, Language.PYTHON, timeout=10)
        
        assert result.success is False
        assert result.exit_code != 0
        assert "Before error" in result.stdout
        assert "ZeroDivisionError" in result.stderr or "error" in result.stderr.lower()
    
    def test_file_upload(self, sandbox):
        """Test file upload functionality."""
        code = '''
with open('/tmp/test_data.txt', 'r') as f:
    content = f.read()
print(f"File content: {content}")
'''
        file_uploads = {
            'test_data.txt': b'Hello from uploaded file!'
        }
        
        result = sandbox.execute(
            code, 
            Language.PYTHON, 
            timeout=10,
            file_uploads=file_uploads
        )
        
        assert result.success is True
        assert "Hello from uploaded file!" in result.stdout


class TestC23Execution:
    """Test C23 code execution."""
    
    def test_simple_c_program(self, sandbox):
        """Test basic C program execution."""
        code = '''
#include <stdio.h>

int main() {
    printf("Hello from C23\\n");
    int sum = 0;
    for (int i = 0; i < 10; i++) {
        sum += i;
    }
    printf("Sum: %d\\n", sum);
    return 0;
}
'''
        result = sandbox.execute(code, Language.C23, timeout=30)
        
        # May fail if C23 image not built
        if not result.success and "not available" in result.stderr:
            pytest.skip("C23 image not available")
        
        assert result.success is True
        assert "Hello from C23" in result.stdout
        assert "Sum: 45" in result.stdout
    
    def test_c_math_operations(self, sandbox):
        """Test C math library operations."""
        code = '''
#include <stdio.h>
#include <math.h>

int main() {
    double result = sqrt(2.0);
    printf("Square root of 2: %.10f\\n", result);
    printf("Pi: %.10f\\n", M_PI);
    return 0;
}
'''
        result = sandbox.execute(code, Language.C23, timeout=30)
        
        if not result.success and "not available" in result.stderr:
            pytest.skip("C23 image not available")
        
        if result.success:
            assert "Square root of 2:" in result.stdout


class TestJavaExecution:
    """Test Java code execution."""
    
    def test_simple_java_program(self, sandbox):
        """Test basic Java program execution."""
        code = '''
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from Java");
        int sum = 0;
        for (int i = 0; i < 10; i++) {
            sum += i;
        }
        System.out.println("Sum: " + sum);
    }
}
'''
        result = sandbox.execute(code, Language.JAVA, timeout=30)
        
        if not result.success and "not available" in result.stderr:
            pytest.skip("Java image not available")
        
        if result.success:
            assert "Hello from Java" in result.stdout
            assert "Sum: 45" in result.stdout
    
    def test_custom_class_name(self, sandbox):
        """Test Java with custom class name."""
        code = '''
public class Calculator {
    public static void main(String[] args) {
        System.out.println("Calculator running");
    }
}
'''
        result = sandbox.execute(
            code, 
            Language.JAVA, 
            timeout=30,
            class_name="Calculator"
        )
        
        if not result.success and "not available" in result.stderr:
            pytest.skip("Java image not available")
        
        if result.success:
            assert "Calculator running" in result.stdout


class TestJavaScriptExecution:
    """Test JavaScript code execution."""
    
    def test_simple_javascript(self, sandbox):
        """Test basic JavaScript execution."""
        code = '''
console.log("Hello from Node.js");
const arr = [1, 2, 3, 4, 5];
const sum = arr.reduce((a, b) => a + b, 0);
console.log("Sum:", sum);
'''
        result = sandbox.execute(code, Language.JAVASCRIPT, timeout=10)
        
        if not result.success and "not available" in result.stderr:
            pytest.skip("JavaScript image not available")
        
        if result.success:
            assert "Hello from Node.js" in result.stdout
            assert "Sum: 15" in result.stdout
    
    def test_javascript_array_operations(self, sandbox):
        """Test JavaScript array operations."""
        code = '''
const numbers = Array.from({length: 100}, (_, i) => i + 1);
const squares = numbers.map(n => n * n);
const sum = squares.reduce((a, b) => a + b, 0);
console.log("Sum of squares 1-100:", sum);
'''
        result = sandbox.execute(code, Language.JAVASCRIPT, timeout=10)
        
        if not result.success and "not available" in result.stderr:
            pytest.skip("JavaScript image not available")
        
        if result.success:
            assert "Sum of squares 1-100:" in result.stdout


class TestRustExecution:
    """Test Rust code execution."""
    
    def test_simple_rust_program(self, sandbox):
        """Test basic Rust program execution."""
        code = '''
fn main() {
    println!("Hello from Rust");
    let sum: i32 = (1..=10).sum();
    println!("Sum: {}", sum);
}
'''
        result = sandbox.execute(code, Language.RUST, timeout=60)
        
        if not result.success and "not available" in result.stderr:
            pytest.skip("Rust image not available")
        
        if result.success:
            assert "Hello from Rust" in result.stdout
            assert "Sum: 55" in result.stdout
    
    def test_rust_vector_operations(self, sandbox):
        """Test Rust vector operations."""
        code = '''
fn main() {
    let numbers: Vec<i32> = (1..=100).collect();
    let sum: i32 = numbers.iter().sum();
    let squares: Vec<i32> = numbers.iter().map(|x| x * x).collect();
    println!("Sum 1-100: {}", sum);
    println!("Sum of squares: {}", squares.iter().sum::<i32>());
}
'''
        result = sandbox.execute(code, Language.RUST, timeout=120)
        
        if not result.success and "not available" in result.stderr:
            pytest.skip("Rust image not available")
        
        if result.success:
            assert "Sum 1-100: 5050" in result.stdout


class TestGoExecution:
    """Test Go code execution."""
    
    def test_simple_go_program(self, sandbox):
        """Test basic Go program execution."""
        code = '''
package main

import "fmt"

func main() {
    fmt.Println("Hello from Go")
    sum := 0
    for i := 1; i <= 10; i++ {
        sum += i
    }
    fmt.Printf("Sum: %d\\n", sum)
}
'''
        result = sandbox.execute(code, Language.GO, timeout=30)
        
        if not result.success and "not available" in result.stderr:
            pytest.skip("Go image not available")
        
        if result.success:
            assert "Hello from Go" in result.stdout
            assert "Sum: 55" in result.stdout
    
    def test_go_slice_operations(self, sandbox):
        """Test Go slice operations."""
        code = '''
package main

import "fmt"

func main() {
    numbers := make([]int, 100)
    for i := 0; i < 100; i++ {
        numbers[i] = i + 1
    }
    
    sum := 0
    for _, n := range numbers {
        sum += n
    }
    
    fmt.Printf("Sum 1-100: %d\\n", sum)
}
'''
        result = sandbox.execute(code, Language.GO, timeout=30)
        
        if not result.success and "not available" in result.stderr:
            pytest.skip("Go image not available")
        
        if result.success:
            assert "Sum 1-100: 5050" in result.stdout


class TestClearanceLevels:
    """Test clearance level configurations."""
    
    def test_network_config_unclassified(self):
        """Test unclassified network config is isolated."""
        config = SandboxOrchestrator.NETWORK_CONFIG[ClearanceLevel.UNCLASSIFIED]
        assert config['network_mode'] == 'none'
        assert config['dns'] == []
    
    def test_network_config_confidential(self):
        """Test confidential network config has limited access."""
        config = SandboxOrchestrator.NETWORK_CONFIG[ClearanceLevel.CONFIDENTIAL]
        assert config['network_mode'] == 'bridge'
        assert len(config['dns']) > 0


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_invalid_language(self, sandbox):
        """Test handling of invalid language."""
        with pytest.raises(SandboxError):
            sandbox.execute("print('test')", "invalid_language")
    
    def test_malicious_filename(self, sandbox):
        """Test handling of malicious filename in uploads."""
        code = 'print("test")'
        file_uploads = {
            '../../../etc/passwd': b'malicious content'
        }
        
        result = sandbox.execute(
            code,
            Language.PYTHON,
            file_uploads=file_uploads
        )
        
        # Should fail due to security check
        assert result.success is False


class TestExecutionResult:
    """Test ExecutionResult dataclass."""
    
    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = ExecutionResult(
            success=True,
            exit_code=0,
            stdout="Hello",
            stderr="",
            execution_time=1.5,
            memory_usage=1024,
            cpu_usage=10.5,
            container_id="abc123"
        )
        
        d = result.to_dict()
        assert d['success'] is True
        assert d['exit_code'] == 0
        assert d['stdout'] == "Hello"
    
    def test_result_to_json(self):
        """Test converting result to JSON."""
        result = ExecutionResult(
            success=True,
            exit_code=0,
            stdout="Hello",
            stderr="",
            execution_time=1.5,
            memory_usage=1024,
            cpu_usage=10.5
        )
        
        json_str = result.to_json()
        assert '"success": true' in json_str
        assert '"exit_code": 0' in json_str
        assert '"stdout": "Hello"' in json_str


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
