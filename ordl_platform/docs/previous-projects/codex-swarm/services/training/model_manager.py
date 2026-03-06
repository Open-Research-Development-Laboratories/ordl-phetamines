"""
ORDL Command Post - Model Manager
Handles trained model management, versioning, quantization, and deployment.
"""

import os
import json
import shutil
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import logging
import subprocess
import threading

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


try:
    from huggingface_hub import HfApi, create_repo, upload_folder
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    logger.warning("HuggingFace Hub not available. Model sharing features disabled.")


try:
    from unsloth import FastLanguageModel
    UNSLOTH_AVAILABLE = True
except ImportError:
    UNSLOTH_AVAILABLE = False
    logger.warning("Unsloth not available. Some features will be limited.")


@dataclass
class ModelVersion:
    """Model version metadata"""
    version_id: str
    model_name: str
    base_model: str
    training_job_id: str
    created_at: str
    metrics: Dict[str, Any]
    quantization: str
    file_size_mb: float
    checksum: str
    path: str
    is_deployed: bool = False


@dataclass
class QuantizationResult:
    """Quantization operation result"""
    success: bool
    output_path: str
    quant_type: str
    original_size_mb: float
    quantized_size_mb: float
    compression_ratio: float
    error: Optional[str] = None


class ModelRegistry:
    """
    Central registry for managing trained models.
    Uses SQLite for persistence.
    """
    
    def __init__(self, db_path: Optional[str] = None, models_dir: Optional[str] = None):
        self.db_path = db_path or os.path.expanduser("~/.ordl/model_registry.db")
        self.models_dir = models_dir or os.path.expanduser("~/.ordl/models")
        
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                base_model TEXT,
                training_job_id TEXT,
                created_at TEXT,
                metrics TEXT,
                quantization TEXT,
                file_size_mb REAL,
                checksum TEXT,
                path TEXT,
                is_deployed INTEGER DEFAULT 0,
                deployment_endpoint TEXT,
                tags TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_versions (
                id TEXT PRIMARY KEY,
                model_id TEXT,
                version TEXT,
                path TEXT,
                metrics TEXT,
                created_at TEXT,
                FOREIGN KEY (model_id) REFERENCES models(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_model(
        self,
        model_name: str,
        base_model: str,
        training_job_id: str,
        model_path: str,
        metrics: Optional[Dict] = None,
        quantization: str = "none",
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Register a new model in the registry.
        
        Returns:
            model_id: Unique identifier for the model
        """
        model_id = f"model-{hashlib.md5(f'{model_name}-{datetime.now()}'.encode()).hexdigest()[:12]}"
        
        # Calculate file size
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(model_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        
        file_size_mb = total_size / (1024 * 1024)
        
        # Calculate checksum
        checksum = self._calculate_checksum(model_path)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO models (id, name, base_model, training_job_id, created_at,
                              metrics, quantization, file_size_mb, checksum, path, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            model_id, model_name, base_model, training_job_id,
            datetime.utcnow().isoformat(),
            json.dumps(metrics or {}),
            quantization,
            file_size_mb,
            checksum,
            model_path,
            json.dumps(tags or [])
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Registered model: {model_id} ({model_name})")
        return model_id
    
    def _calculate_checksum(self, path: str) -> str:
        """Calculate MD5 checksum of model files"""
        hash_md5 = hashlib.md5()
        
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for filename in sorted(files):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, "rb") as f:
                            for chunk in iter(lambda: f.read(4096), b""):
                                hash_md5.update(chunk)
                    except Exception as e:
                        logger.warning(f"Could not hash {filepath}: {e}")
        else:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    def get_model(self, model_id: str) -> Optional[Dict]:
        """Get model information by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM models WHERE id = ?', (model_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_dict(row)
    
    def list_models(
        self,
        deployed_only: bool = False,
        base_model: Optional[str] = None
    ) -> List[Dict]:
        """List all registered models"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM models WHERE 1=1'
        params = []
        
        if deployed_only:
            query += ' AND is_deployed = 1'
        
        if base_model:
            query += ' AND base_model = ?'
            params.append(base_model)
        
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row) for row in rows]
    
    def _row_to_dict(self, row: tuple) -> Dict:
        """Convert database row to dictionary"""
        return {
            'id': row[0],
            'name': row[1],
            'base_model': row[2],
            'training_job_id': row[3],
            'created_at': row[4],
            'metrics': json.loads(row[5]) if row[5] else {},
            'quantization': row[6],
            'file_size_mb': row[7],
            'checksum': row[8],
            'path': row[9],
            'is_deployed': bool(row[10]),
            'deployment_endpoint': row[11],
            'tags': json.loads(row[12]) if row[12] else []
        }
    
    def update_deployment_status(
        self,
        model_id: str,
        is_deployed: bool,
        endpoint: Optional[str] = None
    ):
        """Update deployment status of a model"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE models 
            SET is_deployed = ?, deployment_endpoint = ?
            WHERE id = ?
        ''', (int(is_deployed), endpoint, model_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated deployment status for {model_id}: deployed={is_deployed}")
    
    def delete_model(self, model_id: str, delete_files: bool = False) -> bool:
        """Delete a model from registry"""
        model = self.get_model(model_id)
        if not model:
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM models WHERE id = ?', (model_id,))
        cursor.execute('DELETE FROM model_versions WHERE model_id = ?', (model_id,))
        
        conn.commit()
        conn.close()
        
        if delete_files and model['path'] and os.path.exists(model['path']):
            shutil.rmtree(model['path'], ignore_errors=True)
            logger.info(f"Deleted model files: {model['path']}")
        
        logger.info(f"Deleted model from registry: {model_id}")
        return True


class ModelQuantizer:
    """
    Handles model quantization for deployment.
    Supports GGUF, AWQ, and GPTQ formats.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.expanduser("~/.ordl/quantized")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def quantize_to_gguf(
        self,
        model_path: str,
        output_name: Optional[str] = None,
        quant_type: str = "Q4_K_M",
        context_length: int = 4096
    ) -> QuantizationResult:
        """
        Quantize model to GGUF format using llama.cpp.
        
        Args:
            model_path: Path to the model directory
            output_name: Output filename (without extension)
            quant_type: Quantization type (Q4_K_M, Q5_K_M, Q6_K, Q8_0)
            context_length: Context length for the model
        
        Returns:
            QuantizationResult with paths and metrics
        """
        if output_name is None:
            output_name = f"model-{quant_type.lower()}"
        
        output_path = os.path.join(self.output_dir, f"{output_name}.gguf")
        
        try:
            # Get original size
            original_size = self._get_dir_size(model_path)
            
            # Try using llama.cpp's convert script
            # First, try to find llama.cpp installation
            llama_cpp_path = self._find_llama_cpp()
            
            if not llama_cpp_path:
                # Try using unsloth's save_to_gguf
                if UNSLOTH_AVAILABLE:
                    return self._quantize_with_unsloth(model_path, output_path, quant_type, context_length)
                else:
                    raise RuntimeError("llama.cpp not found and unsloth not available")
            
            # Use llama.cpp for quantization
            convert_script = os.path.join(llama_cpp_path, "convert.py")
            quantize_binary = os.path.join(llama_cpp_path, "quantize")
            
            # Convert to f16 first
            f16_path = output_path.replace('.gguf', '-f16.gguf')
            
            subprocess.run([
                "python", convert_script,
                model_path,
                "--outfile", f16_path,
                "--outtype", "f16"
            ], check=True, capture_output=True)
            
            # Quantize
            subprocess.run([
                quantize_binary,
                f16_path,
                output_path,
                quant_type
            ], check=True, capture_output=True)
            
            # Cleanup f16
            os.remove(f16_path)
            
            quantized_size = os.path.getsize(output_path) / (1024 * 1024)
            
            return QuantizationResult(
                success=True,
                output_path=output_path,
                quant_type=quant_type,
                original_size_mb=original_size / (1024 * 1024),
                quantized_size_mb=quantized_size,
                compression_ratio=original_size / (1024 * 1024) / quantized_size
            )
            
        except Exception as e:
            logger.error(f"Quantization failed: {e}")
            return QuantizationResult(
                success=False,
                output_path="",
                quant_type=quant_type,
                original_size_mb=0,
                quantized_size_mb=0,
                compression_ratio=0,
                error=str(e)
            )
    
    def _quantize_with_unsloth(
        self,
        model_path: str,
        output_path: str,
        quant_type: str,
        context_length: int
    ) -> QuantizationResult:
        """Quantize using Unsloth's built-in GGUF support"""
        try:
            from unsloth import FastLanguageModel
            
            original_size = self._get_dir_size(model_path)
            
            # Load model
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=model_path,
                max_seq_length=context_length,
                dtype=None,
                load_in_4bit=False,
            )
            
            # Save to GGUF
            model.save_pretrained_gguf(
                output_path.replace('.gguf', ''),
                tokenizer,
                quantization_method=quant_type
            )
            
            quantized_size = os.path.getsize(output_path) / (1024 * 1024)
            
            return QuantizationResult(
                success=True,
                output_path=output_path,
                quant_type=quant_type,
                original_size_mb=original_size / (1024 * 1024),
                quantized_size_mb=quantized_size,
                compression_ratio=(original_size / (1024 * 1024)) / quantized_size
            )
            
        except Exception as e:
            return QuantizationResult(
                success=False,
                output_path="",
                quant_type=quant_type,
                original_size_mb=0,
                quantized_size_mb=0,
                compression_ratio=0,
                error=str(e)
            )
    
    def quantize_to_awq(
        self,
        model_path: str,
        output_name: Optional[str] = None,
        bits: int = 4,
        group_size: int = 128
    ) -> QuantizationResult:
        """Quantize model to AWQ format"""
        # AWQ quantization requires auto-awq library
        try:
            from awq import AutoAWQForCausalLM
            from transformers import AutoTokenizer
            
            if output_name is None:
                output_name = f"model-awq-{bits}bit"
            
            output_path = os.path.join(self.output_dir, output_name)
            os.makedirs(output_path, exist_ok=True)
            
            original_size = self._get_dir_size(model_path)
            
            # Load model
            model = AutoAWQForCausalLM.from_pretrained(model_path)
            tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            
            # Quantize
            model.quantize(tokenizer, quant_config={"zero_point": True, "q_group_size": group_size, "w_bit": bits})
            
            # Save
            model.save_quantized(output_path)
            tokenizer.save_pretrained(output_path)
            
            quantized_size = self._get_dir_size(output_path)
            
            return QuantizationResult(
                success=True,
                output_path=output_path,
                quant_type=f"AWQ-{bits}bit",
                original_size_mb=original_size / (1024 * 1024),
                quantized_size_mb=quantized_size / (1024 * 1024),
                compression_ratio=original_size / quantized_size
            )
            
        except ImportError:
            return QuantizationResult(
                success=False,
                output_path="",
                quant_type="AWQ",
                original_size_mb=0,
                quantized_size_mb=0,
                compression_ratio=0,
                error="auto-awq library not installed. Install with: pip install autoawq"
            )
        except Exception as e:
            return QuantizationResult(
                success=False,
                output_path="",
                quant_type="AWQ",
                original_size_mb=0,
                quantized_size_mb=0,
                compression_ratio=0,
                error=str(e)
            )
    
    def _find_llama_cpp(self) -> Optional[str]:
        """Find llama.cpp installation directory"""
        # Check common locations
        possible_paths = [
            "/usr/local/llama.cpp",
            "/opt/llama.cpp",
            os.path.expanduser("~/llama.cpp"),
            os.path.expanduser("~/.local/llama.cpp"),
        ]
        
        for path in possible_paths:
            if os.path.exists(os.path.join(path, "quantize")):
                return path
        
        # Check PATH
        try:
            result = subprocess.run(["which", "quantize"], capture_output=True, text=True)
            if result.returncode == 0:
                return os.path.dirname(result.stdout.strip())
        except:
            pass
        
        return None
    
    def _get_dir_size(self, path: str) -> int:
        """Get total size of directory in bytes"""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
        return total


class ModelDeployer:
    """
    Handles model deployment to inference endpoints.
    Supports local deployment and vLLM/TGI integration.
    """
    
    def __init__(self, registry: Optional[ModelRegistry] = None):
        self.registry = registry or ModelRegistry()
        self.active_deployments: Dict[str, Any] = {}
    
    def deploy_local(
        self,
        model_id: str,
        port: int = 8000,
        max_model_len: int = 4096,
        gpu_memory_utilization: float = 0.9
    ) -> Dict:
        """
        Deploy model locally using vLLM.
        
        Args:
            model_id: Model ID from registry
            port: Port to serve on
            max_model_len: Maximum sequence length
            gpu_memory_utilization: GPU memory fraction to use
        
        Returns:
            Deployment information
        """
        model = self.registry.get_model(model_id)
        if not model:
            raise ValueError(f"Model not found: {model_id}")
        
        try:
            import vllm
            VLLM_AVAILABLE = True
        except ImportError:
            VLLM_AVAILABLE = False
        
        if not VLLM_AVAILABLE:
            # Fall back to simple Flask server
            return self._deploy_simple(model, port)
        
        # Deploy with vLLM
        deployment_id = f"deploy-{model_id}"
        
        def run_vllm():
            try:
                from vllm import LLMEngine, EngineArgs, SamplingParams
                
                engine_args = EngineArgs(
                    model=model['path'],
                    max_model_len=max_model_len,
                    gpu_memory_utilization=gpu_memory_utilization
                )
                
                engine = LLMEngine.from_engine_args(engine_args)
                
                self.active_deployments[deployment_id] = {
                    'engine': engine,
                    'port': port,
                    'status': 'running'
                }
                
            except Exception as e:
                logger.error(f"vLLM deployment failed: {e}")
                self.active_deployments[deployment_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        thread = threading.Thread(target=run_vllm, daemon=True)
        thread.start()
        
        # Update registry
        endpoint = f"http://localhost:{port}"
        self.registry.update_deployment_status(model_id, True, endpoint)
        
        return {
            'deployment_id': deployment_id,
            'model_id': model_id,
            'endpoint': endpoint,
            'status': 'starting',
            'port': port
        }
    
    def _deploy_simple(self, model: Dict, port: int) -> Dict:
        """Simple deployment using transformers pipeline"""
        deployment_id = f"deploy-{model['id']}"
        
        try:
            from transformers import pipeline
            
            # Load pipeline
            pipe = pipeline(
                "text-generation",
                model=model['path'],
                device_map="auto"
            )
            
            self.active_deployments[deployment_id] = {
                'pipeline': pipe,
                'status': 'running'
            }
            
            endpoint = f"http://localhost:{port}"
            self.registry.update_deployment_status(model['id'], True, endpoint)
            
            return {
                'deployment_id': deployment_id,
                'model_id': model['id'],
                'endpoint': endpoint,
                'status': 'running',
                'type': 'simple'
            }
            
        except Exception as e:
            return {
                'deployment_id': deployment_id,
                'model_id': model['id'],
                'status': 'error',
                'error': str(e)
            }
    
    def undeploy(self, deployment_id: str) -> bool:
        """Stop a deployment"""
        if deployment_id not in self.active_deployments:
            return False
        
        deployment = self.active_deployments[deployment_id]
        
        # Cleanup
        if 'engine' in deployment:
            del deployment['engine']
        if 'pipeline' in deployment:
            del deployment['pipeline']
        
        deployment['status'] = 'stopped'
        
        # Update registry
        model_id = deployment_id.replace('deploy-', '')
        self.registry.update_deployment_status(model_id, False)
        
        return True
    
    def list_deployments(self) -> List[Dict]:
        """List all active deployments"""
        return [
            {
                'deployment_id': k,
                'status': v['status'],
                'port': v.get('port'),
                'type': v.get('type', 'vllm')
            }
            for k, v in self.active_deployments.items()
        ]


def upload_to_huggingface(
    model_path: str,
    repo_id: str,
    token: Optional[str] = None,
    private: bool = False
) -> bool:
    """
    Upload model to HuggingFace Hub.
    
    Args:
        model_path: Path to model directory
        repo_id: HuggingFace repo ID (username/repo-name)
        token: HuggingFace API token
        private: Whether to create private repo
    
    Returns:
        Success status
    """
    if not HF_AVAILABLE:
        logger.error("HuggingFace Hub not available. Install with: pip install huggingface-hub")
        return False
    
    try:
        # Create repo if doesn't exist
        try:
            create_repo(repo_id, token=token, private=private, exist_ok=True)
        except Exception as e:
            logger.warning(f"Repo creation warning (may already exist): {e}")
        
        # Upload
        upload_folder(
            folder_path=model_path,
            repo_id=repo_id,
            token=token
        )
        
        logger.info(f"Successfully uploaded to {repo_id}")
        return True
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return False


# Example usage
if __name__ == "__main__":
    registry = ModelRegistry()
    quantizer = ModelQuantizer()
    deployer = ModelDeployer(registry)
    
    print("ModelManager initialized successfully")
