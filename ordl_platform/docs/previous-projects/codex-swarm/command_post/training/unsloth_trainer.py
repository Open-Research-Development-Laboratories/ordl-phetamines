#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - REAL LLM TRAINING PIPELINE
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Classification Level: TS/SCI/NOFORN

MILITARY-GRADE LLM FINE-TUNING WITH REAL DATA
================================================================================
This module provides ACTUAL LLM training using:
- Unsloth (2x faster, 70% less VRAM)
- Transformers fallback for CPU
- Real dataset loading from HuggingFace/local files
- Actual loss computation from model training
- LoRA/QLoRA for efficient fine-tuning
- GGUF export for production deployment

NO SIMULATIONS. NO FAKE DATA. REAL TRAINING ONLY.

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

import os
import sys
import json
import time
import sqlite3
import logging
import hashlib
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import warnings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("unsloth_trainer")

# Filter warnings
warnings.filterwarnings("ignore", category=UserWarning)


class TrainingStatus(Enum):
    """Training job status"""
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class DatasetFormat(Enum):
    """Supported dataset formats"""
    ALPACA = "alpaca"           # instruction, input, output
    CHAT = "chat"               # messages (OpenAI format)
    TEXT = "text"               # plain text field
    JSONL = "jsonl"             # JSON lines format
    CSV = "csv"                 # CSV with columns


@dataclass
class TrainingConfig:
    """Training configuration with military-grade validation"""
    job_id: str
    name: str
    base_model: str
    output_model: str
    
    # Dataset configuration
    dataset_source: str  # 'huggingface', 'local', 'url'
    dataset_path: str    # dataset name or file path
    dataset_format: str = "alpaca"
    dataset_text_field: str = "text"
    dataset_split: str = "train"
    dataset_subset: Optional[str] = None
    
    # Training hyperparameters
    learning_rate: float = 2e-4
    batch_size: int = 2
    gradient_accumulation_steps: int = 4
    max_steps: int = 1000
    num_epochs: Optional[int] = None
    warmup_steps: int = 100
    warmup_ratio: float = 0.1
    save_steps: int = 500
    eval_steps: int = 500
    logging_steps: int = 10
    max_seq_length: int = 2048
    
    # LoRA configuration
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.0
    lora_target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ])
    use_rslora: bool = False
    use_loftq: bool = False
    
    # Optimization
    load_in_4bit: bool = True
    load_in_8bit: bool = False
    optim: str = "adamw_8bit"
    lr_scheduler_type: str = "linear"
    weight_decay: float = 0.01
    max_grad_norm: float = 0.3
    
    # System
    seed: int = 3407
    fp16: bool = False
    bf16: bool = True
    gradient_checkpointing: bool = True
    group_by_length: bool = True
    packing: bool = True
    
    def __post_init__(self):
        """Validate configuration"""
        if self.lora_r < 1 or self.lora_r > 1024:
            raise ValueError(f"lora_r must be between 1 and 1024, got {self.lora_r}")
        if self.learning_rate < 1e-6 or self.learning_rate > 1e-2:
            raise ValueError(f"learning_rate out of reasonable range: {self.learning_rate}")
        if self.max_steps < 1:
            raise ValueError(f"max_steps must be positive, got {self.max_steps}")


@dataclass
class DatasetInfo:
    """Dataset metadata"""
    name: str
    source: str
    format: str
    num_examples: int
    avg_length: float
    columns: List[str]
    size_mb: float
    hash: str
    loaded_at: str


class DatasetManager:
    """
    Military-grade dataset management
    
    Handles loading, validation, and formatting of training datasets
    from HuggingFace Hub, local files, or URLs.
    """
    
    def __init__(self, cache_dir: str = "/opt/codex-swarm/command-post/datasets"):
        self.cache_dir = cache_dir
        self.loaded_datasets: Dict[str, DatasetInfo] = {}
        os.makedirs(cache_dir, exist_ok=True)
    
    def load_dataset(
        self,
        source: str,
        path: str,
        format: str = "alpaca",
        split: str = "train",
        subset: Optional[str] = None,
        text_field: str = "text"
    ) -> tuple:
        """
        Load dataset from various sources
        
        Returns:
            (dataset, info) tuple
        """
        logger.info(f"Loading dataset from {source}: {path}")
        
        try:
            from datasets import load_dataset as hf_load_dataset
            
            if source == "huggingface":
                dataset = hf_load_dataset(
                    path,
                    subset,
                    split=split,
                    cache_dir=os.path.join(self.cache_dir, "hf_cache")
                )
            elif source == "local":
                if path.endswith('.json') or path.endswith('.jsonl'):
                    dataset = hf_load_dataset(
                        "json",
                        data_files=path,
                        split=split
                    )
                elif path.endswith('.csv'):
                    dataset = hf_load_dataset(
                        "csv",
                        data_files=path,
                        split=split
                    )
                elif path.endswith('.parquet'):
                    dataset = hf_load_dataset(
                        "parquet",
                        data_files=path,
                        split=split
                    )
                elif os.path.isdir(path):
                    dataset = hf_load_dataset(
                        path,
                        split=split
                    )
                else:
                    raise ValueError(f"Unsupported file format: {path}")
            elif source == "url":
                dataset = hf_load_dataset(
                    "json",
                    data_files=path,
                    split=split
                )
            else:
                raise ValueError(f"Unknown dataset source: {source}")
            
            # Format dataset
            formatted_dataset = self._format_dataset(dataset, format, text_field)
            
            # Create dataset info
            info = DatasetInfo(
                name=path.split("/")[-1],
                source=source,
                format=format,
                num_examples=len(formatted_dataset),
                avg_length=self._compute_avg_length(formatted_dataset, text_field),
                columns=list(formatted_dataset.column_names),
                size_mb=0.0,  # Would need actual computation
                hash=self._compute_hash(formatted_dataset),
                loaded_at=datetime.utcnow().isoformat()
            )
            
            self.loaded_datasets[path] = info
            
            logger.info(f"Dataset loaded: {info.num_examples} examples, "
                       f"avg length: {info.avg_length:.1f} chars")
            
            return formatted_dataset, info
            
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise
    
    def _format_dataset(self, dataset, format: str, text_field: str):
        """Format dataset for training based on format type"""
        
        if format == "alpaca":
            # Standard Alpaca format: instruction, input, output
            def format_alpaca(example):
                instruction = example.get("instruction", "")
                input_text = example.get("input", "")
                output = example.get("output", "")
                
                if input_text:
                    text = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
                else:
                    text = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
                
                return {text_field: text}
            
            return dataset.map(format_alpaca)
        
        elif format == "chat":
            # OpenAI chat format: messages list
            def format_chat(example):
                messages = example.get("messages", [])
                text_parts = []
                
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    text_parts.append(f"<|{role}|>\n{content}")
                
                return {text_field: "\n".join(text_parts)}
            
            return dataset.map(format_chat)
        
        elif format == "text":
            # Already in text format, just ensure field exists
            if text_field not in dataset.column_names:
                raise ValueError(f"Text field '{text_field}' not found in dataset. "
                               f"Available: {dataset.column_names}")
            return dataset
        
        else:
            raise ValueError(f"Unknown dataset format: {format}")
    
    def _compute_avg_length(self, dataset, text_field: str) -> float:
        """Compute average text length"""
        total = 0
        count = min(len(dataset), 1000)  # Sample first 1000
        
        for i in range(count):
            text = dataset[i].get(text_field, "")
            total += len(text)
        
        return total / count if count > 0 else 0
    
    def _compute_hash(self, dataset) -> str:
        """Compute dataset hash for verification"""
        # Simple hash based on first few examples
        sample = str(dataset[0]) if len(dataset) > 0 else ""
        return hashlib.sha256(sample.encode()).hexdigest()[:16]
    
    def list_cached_datasets(self) -> List[DatasetInfo]:
        """List all loaded datasets"""
        return list(self.loaded_datasets.values())


class TrainingJob:
    """Represents a training job with full lifecycle management"""
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.status = TrainingStatus.QUEUED
        self.progress = 0
        self.current_step = 0
        self.current_epoch = 0
        self.loss = 0.0
        self.learning_rate = config.learning_rate
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.eta_seconds = 0
        self.checkpoints: List[str] = []
        self.metrics_history: List[Dict] = []
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.error_message: Optional[str] = None
        self.model_output_path: Optional[str] = None
        self.dataset_info: Optional[DatasetInfo] = None
        self.hardware_used: Dict[str, Any] = {}
        
    def to_dict(self) -> Dict:
        return {
            'job_id': self.config.job_id,
            'name': self.config.name,
            'base_model': self.config.base_model,
            'status': self.status.value,
            'progress': self.progress,
            'current_step': self.current_step,
            'current_epoch': self.current_epoch,
            'loss': round(self.loss, 6) if self.loss else 0.0,
            'learning_rate': self.learning_rate,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'eta_seconds': self.eta_seconds,
            'checkpoints': self.checkpoints,
            'model_output_path': self.model_output_path,
            'dataset_info': asdict(self.dataset_info) if self.dataset_info else None,
            'hardware_used': self.hardware_used,
            'error_message': self.error_message
        }
    
    def stop(self):
        """Request job stop"""
        self._stop_event.set()
        if self.status == TrainingStatus.RUNNING:
            self.status = TrainingStatus.STOPPED
        logger.info(f"Job {self.config.job_id}: Stop requested")
    
    def pause(self):
        """Pause job"""
        self._pause_event.set()
        if self.status == TrainingStatus.RUNNING:
            self.status = TrainingStatus.PAUSED
    
    def resume(self):
        """Resume paused job"""
        self._pause_event.clear()
        if self.status == TrainingStatus.PAUSED:
            self.status = TrainingStatus.RUNNING


class UnslothTrainer:
    """
    Military-grade LLM training pipeline
    
    Provides REAL training with:
    - Unsloth for GPU (2x faster, 70% less VRAM)
    - Transformers for CPU/GPU fallback
    - Real dataset loading and formatting
    - Actual loss computation
    - LoRA/QLoRA for efficient fine-tuning
    """
    
    def __init__(self, db_path: str = "/opt/codex-swarm/command-post/data/nexus.db"):
        self.db_path = db_path
        self.jobs: Dict[str, TrainingJob] = {}
        self.models_dir = "/opt/codex-swarm/command-post/models"
        self.datasets_dir = "/opt/codex-swarm/command-post/datasets"
        
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.datasets_dir, exist_ok=True)
        
        # Initialize dataset manager
        self.dataset_manager = DatasetManager(self.datasets_dir)
        
        # Hardware detection
        self._detect_hardware()
        
        # Initialize database
        self._init_db()
        
        logger.info(f"Trainer initialized: GPU={self.has_gpu}, "
                   f"Unsloth={self.unsloth_available}, "
                   f"Transformers={self.transformers_available}")
    
    def _detect_hardware(self):
        """Detect available hardware"""
        try:
            import torch
            self.has_gpu = torch.cuda.is_available()
            self.gpu_count = torch.cuda.device_count() if self.has_gpu else 0
            self.gpu_name = torch.cuda.get_device_name(0) if self.has_gpu else None
            self.torch_version = torch.__version__
            
            if self.has_gpu:
                gpu_props = torch.cuda.get_device_properties(0)
                self.gpu_memory_gb = gpu_props.total_memory / (1024**3)
                logger.info(f"GPU detected: {self.gpu_name} "
                           f"({self.gpu_memory_gb:.1f} GB)")
        except ImportError:
            self.has_gpu = False
            self.gpu_count = 0
            self.torch_version = "not installed"
        
        # Check libraries
        try:
            import unsloth
            self.unsloth_available = True
            self.unsloth_version = unsloth.__version__
        except ImportError:
            self.unsloth_available = False
            self.unsloth_version = None
        
        try:
            import transformers
            self.transformers_available = True
            self.transformers_version = transformers.__version__
        except ImportError:
            self.transformers_available = False
            self.transformers_version = None
        
        try:
            import trl
            self.trl_available = True
        except ImportError:
            self.trl_available = False
    
    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_jobs (
                job_id TEXT PRIMARY KEY,
                name TEXT,
                base_model TEXT,
                output_model TEXT,
                config TEXT,
                status TEXT,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                model_output_path TEXT,
                error_message TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                step INTEGER,
                epoch INTEGER,
                loss REAL,
                learning_rate REAL,
                timestamp TEXT,
                FOREIGN KEY (job_id) REFERENCES training_jobs(job_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_hardware_info(self) -> Dict:
        """Get comprehensive hardware information"""
        info = {
            'cuda_available': self.has_gpu,
            'cuda_device_count': self.gpu_count,
            'cuda_device_name': self.gpu_name,
            'gpu_memory_gb': getattr(self, 'gpu_memory_gb', 0),
            'torch_version': self.torch_version,
            'unsloth_available': self.unsloth_available,
            'unsloth_version': self.unsloth_version,
            'transformers_available': self.transformers_available,
            'transformers_version': self.transformers_version,
            'trl_available': self.trl_available,
            'recommended_backend': self._get_recommended_backend()
        }
        return info
    
    def _get_recommended_backend(self) -> str:
        """Determine best available backend"""
        if self.unsloth_available and self.has_gpu:
            return "unsloth"
        elif self.transformers_available:
            return "transformers"
        else:
            return "none"
    
    def create_job(self, config_dict: Dict) -> TrainingJob:
        """Create a new training job"""
        config = TrainingConfig(**config_dict)
        job = TrainingJob(config)
        self.jobs[config.job_id] = job
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO training_jobs 
            (job_id, name, base_model, output_model, config, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            config.job_id,
            config.name,
            config.base_model,
            config.output_model,
            json.dumps(asdict(config)),
            job.status.value,
            datetime.utcnow().isoformat()
        ))
        conn.commit()
        conn.close()
        
        logger.info(f"Created job {config.job_id}: {config.name}")
        return job
    
    def start_training(self, job_id: str) -> bool:
        """Start training for a job"""
        if job_id not in self.jobs:
            logger.error(f"Job {job_id} not found")
            return False
        
        job = self.jobs[job_id]
        if job.status == TrainingStatus.RUNNING:
            logger.warning(f"Job {job_id} already running")
            return False
        
        job.status = TrainingStatus.STARTING
        
        # Select backend
        backend = self._get_recommended_backend()
        
        if backend == "unsloth":
            target = self._train_with_unsloth
        elif backend == "transformers":
            target = self._train_with_transformers
        else:
            logger.error("No training backend available. Install unsloth or transformers.")
            job.status = TrainingStatus.FAILED
            job.error_message = "No training backend available"
            return False
        
        # Start in background thread
        thread = threading.Thread(target=target, args=(job,), daemon=True)
        job._thread = thread
        thread.start()
        
        logger.info(f"Started job {job_id} using {backend}")
        return True
    
    def _train_with_unsloth(self, job: TrainingJob):
        """Train using Unsloth (GPU optimized, REAL training)"""
        import torch
        from unsloth import FastLanguageModel
        from trl import SFTTrainer
        from transformers import TrainingArguments
        from datasets import Dataset
        
        try:
            job.status = TrainingStatus.RUNNING
            job.started_at = datetime.utcnow().isoformat()
            job.hardware_used = self.get_hardware_info()
            
            cfg = job.config
            output_dir = os.path.join(self.models_dir, cfg.job_id)
            os.makedirs(output_dir, exist_ok=True)
            job.model_output_path = output_dir
            
            logger.info(f"[Job {cfg.job_id}] Loading model: {cfg.base_model}")
            
            # Load model with Unsloth
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=cfg.base_model,
                max_seq_length=cfg.max_seq_length,
                dtype=None,  # Auto-detect
                load_in_4bit=cfg.load_in_4bit,
            )
            
            # Add LoRA adapters
            model = FastLanguageModel.get_peft_model(
                model,
                r=cfg.lora_r,
                target_modules=cfg.lora_target_modules,
                lora_alpha=cfg.lora_alpha,
                lora_dropout=cfg.lora_dropout,
                bias="none",
                use_gradient_checkpointing="unsloth" if cfg.gradient_checkpointing else False,
                random_state=cfg.seed,
                use_rslora=cfg.use_rslora,
            )
            
            # Load REAL dataset
            logger.info(f"[Job {cfg.job_id}] Loading dataset: {cfg.dataset_path}")
            dataset, dataset_info = self.dataset_manager.load_dataset(
                source=cfg.dataset_source,
                path=cfg.dataset_path,
                format=cfg.dataset_format,
                split=cfg.dataset_split,
                subset=cfg.dataset_subset,
                text_field=cfg.dataset_text_field
            )
            job.dataset_info = dataset_info
            
            # Training arguments
            training_args = TrainingArguments(
                output_dir=output_dir,
                per_device_train_batch_size=cfg.batch_size,
                gradient_accumulation_steps=cfg.gradient_accumulation_steps,
                warmup_steps=cfg.warmup_steps,
                warmup_ratio=cfg.warmup_ratio,
                max_steps=cfg.max_steps,
                num_train_epochs=cfg.num_epochs if cfg.num_epochs else 1,
                learning_rate=cfg.learning_rate,
                fp16=cfg.fp16,
                bf16=cfg.bf16,
                logging_steps=cfg.logging_steps,
                optim=cfg.optim,
                weight_decay=cfg.weight_decay,
                lr_scheduler_type=cfg.lr_scheduler_type,
                seed=cfg.seed,
                save_steps=cfg.save_steps,
                save_total_limit=3,
                report_to="none",
                gradient_checkpointing=cfg.gradient_checkpointing,
                group_by_length=cfg.group_by_length,
            )
            
            # Progress tracking callback
            class RealProgressCallback:
                def __init__(self, job_ref, trainer_ref):
                    self.job_ref = job_ref
                    self.trainer_ref = trainer_ref
                    self.start_time = time.time()
                
                def on_step_end(self, args, state, control, **kwargs):
                    if self.job_ref._stop_event.is_set():
                        control.should_training_stop = True
                        return control
                    
                    # Wait if paused
                    while self.job_ref._pause_event.is_set():
                        time.sleep(0.1)
                    
                    self.job_ref.current_step = state.global_step
                    self.job_ref.current_epoch = state.epoch
                    self.job_ref.progress = int((state.global_step / cfg.max_steps) * 100)
                    
                    # Get ACTUAL loss from trainer
                    if hasattr(state, 'log_history') and state.log_history:
                        latest_log = state.log_history[-1]
                        if 'loss' in latest_log:
                            self.job_ref.loss = latest_log['loss']
                        if 'learning_rate' in latest_log:
                            self.job_ref.learning_rate = latest_log['learning_rate']
                    
                    # Calculate ETA
                    elapsed = time.time() - self.start_time
                    if state.global_step > 0:
                        time_per_step = elapsed / state.global_step
                        remaining_steps = cfg.max_steps - state.global_step
                        self.job_ref.eta_seconds = int(remaining_steps * time_per_step)
                    
                    # Save metrics periodically
                    if state.global_step % cfg.logging_steps == 0:
                        self._save_metrics(state.global_step, state.epoch)
                    
                    return control
                
                def _save_metrics(self, step, epoch):
                    try:
                        conn = sqlite3.connect(self.job_ref.config.db_path if hasattr(self.job_ref.config, 'db_path') else "/opt/codex-swarm/command-post/data/nexus.db")
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO training_metrics (job_id, step, epoch, loss, learning_rate, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            self.job_ref.config.job_id,
                            step,
                            epoch,
                            self.job_ref.loss,
                            self.job_ref.learning_rate,
                            datetime.utcnow().isoformat()
                        ))
                        conn.commit()
                        conn.close()
                    except Exception as e:
                        logger.error(f"Failed to save metrics: {e}")
            
            # Create trainer
            trainer = SFTTrainer(
                model=model,
                tokenizer=tokenizer,
                train_dataset=dataset,
                dataset_text_field=cfg.dataset_text_field,
                max_seq_length=cfg.max_seq_length,
                packing=cfg.packing,
                args=training_args,
            )
            
            # Add progress callback
            progress_callback = RealProgressCallback(job, trainer)
            trainer.add_callback(progress_callback)
            
            # TRAIN (REAL training, not simulation)
            logger.info(f"[Job {cfg.job_id}] Starting REAL training...")
            trainer.train()
            
            if not job._stop_event.is_set():
                # Save final model
                final_path = os.path.join(output_dir, "final")
                trainer.save_model(final_path)
                tokenizer.save_pretrained(final_path)
                job.checkpoints.append(final_path)
                
                # Try to save GGUF
                try:
                    gguf_path = os.path.join(output_dir, "model.gguf")
                    model.save_pretrained_gguf(gguf_path, tokenizer, quantization_method="q4_k_m")
                    job.checkpoints.append(gguf_path)
                    logger.info(f"[Job {cfg.job_id}] GGUF saved: {gguf_path}")
                except Exception as e:
                    logger.warning(f"GGUF export failed: {e}")
                
                job.status = TrainingStatus.COMPLETED
                job.completed_at = datetime.utcnow().isoformat()
                job.eta_seconds = 0
                job.progress = 100
                
                logger.info(f"[Job {cfg.job_id}] Training COMPLETED successfully")
            else:
                job.status = TrainingStatus.STOPPED
                logger.info(f"[Job {cfg.job_id}] Training STOPPED by user")
            
            # Update database
            self._update_job_status(job)
            
        except Exception as e:
            logger.error(f"[Job {cfg.job_id}] Training FAILED: {e}")
            job.status = TrainingStatus.FAILED
            job.error_message = str(e)
            self._update_job_status(job)
    
    def _train_with_transformers(self, job: TrainingJob):
        """Train using standard Transformers (CPU/GPU fallback, REAL training)"""
        import torch
        from transformers import (
            AutoModelForCausalLM, AutoTokenizer,
            TrainingArguments, Trainer,
            DataCollatorForLanguageModeling
        )
        
        try:
            job.status = TrainingStatus.RUNNING
            job.started_at = datetime.utcnow().isoformat()
            job.hardware_used = self.get_hardware_info()
            
            cfg = job.config
            output_dir = os.path.join(self.models_dir, cfg.job_id)
            os.makedirs(output_dir, exist_ok=True)
            job.model_output_path = output_dir
            
            logger.info(f"[Job {cfg.job_id}] Loading model with Transformers: {cfg.base_model}")
            
            # Determine device
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Load model
            model = AutoModelForCausalLM.from_pretrained(
                cfg.base_model,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto" if device == "cuda" else None,
                low_cpu_mem_usage=True
            )
            tokenizer = AutoTokenizer.from_pretrained(cfg.base_model)
            tokenizer.pad_token = tokenizer.eos_token
            
            # Load REAL dataset
            logger.info(f"[Job {cfg.job_id}] Loading dataset: {cfg.dataset_path}")
            dataset, dataset_info = self.dataset_manager.load_dataset(
                source=cfg.dataset_source,
                path=cfg.dataset_path,
                format=cfg.dataset_format,
                split=cfg.dataset_split,
                text_field=cfg.dataset_text_field
            )
            job.dataset_info = dataset_info
            
            # Tokenize dataset
            def tokenize(examples):
                return tokenizer(
                    examples[cfg.dataset_text_field],
                    truncation=True,
                    max_length=cfg.max_seq_length,
                    padding="max_length"
                )
            
            tokenized_dataset = dataset.map(tokenize, batched=True)
            
            # Training arguments
            training_args = TrainingArguments(
                output_dir=output_dir,
                per_device_train_batch_size=cfg.batch_size,
                gradient_accumulation_steps=cfg.gradient_accumulation_steps,
                warmup_steps=cfg.warmup_steps,
                max_steps=cfg.max_steps,
                num_train_epochs=cfg.num_epochs if cfg.num_epochs else 1,
                learning_rate=cfg.learning_rate,
                fp16=device == "cuda" and cfg.fp16,
                bf16=device == "cuda" and cfg.bf16,
                logging_steps=cfg.logging_steps,
                optim=cfg.optim if device == "cuda" else "adamw_torch",
                weight_decay=cfg.weight_decay,
                lr_scheduler_type=cfg.lr_scheduler_type,
                seed=cfg.seed,
                save_steps=cfg.save_steps,
                save_total_limit=3,
                report_to="none",
            )
            
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=tokenizer,
                mlm=False
            )
            
            # Custom callback for progress tracking
            from transformers import TrainerCallback
            
            class RealProgressCallbackTransformers(TrainerCallback):
                def __init__(self, job_ref):
                    self.job_ref = job_ref
                    self.start_time = time.time()
                
                def on_step_end(self, args, state, control, **kwargs):
                    if self.job_ref._stop_event.is_set():
                        control.should_training_stop = True
                        return control
                    
                    self.job_ref.current_step = state.global_step
                    self.job_ref.current_epoch = state.epoch
                    self.job_ref.progress = int((state.global_step / cfg.max_steps) * 100)
                    
                    # Get ACTUAL loss
                    if state.log_history:
                        latest = state.log_history[-1]
                        if 'loss' in latest:
                            self.job_ref.loss = latest['loss']
                        if 'learning_rate' in latest:
                            self.job_ref.learning_rate = latest['learning_rate']
                    
                    # Calculate ETA
                    elapsed = time.time() - self.start_time
                    if state.global_step > 0:
                        time_per_step = elapsed / state.global_step
                        remaining = cfg.max_steps - state.global_step
                        self.job_ref.eta_seconds = int(remaining * time_per_step)
                    
                    return control
            
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_dataset,
                data_collator=data_collator,
                callbacks=[RealProgressCallbackTransformers(job)]
            )
            
            # TRAIN (REAL training)
            logger.info(f"[Job {cfg.job_id}] Starting REAL training with Transformers...")
            trainer.train()
            
            if not job._stop_event.is_set():
                # Save final model
                final_path = os.path.join(output_dir, "final")
                trainer.save_model(final_path)
                tokenizer.save_pretrained(final_path)
                job.checkpoints.append(final_path)
                
                job.status = TrainingStatus.COMPLETED
                job.completed_at = datetime.utcnow().isoformat()
                job.eta_seconds = 0
                job.progress = 100
                
                logger.info(f"[Job {cfg.job_id}] Training COMPLETED successfully")
            else:
                job.status = TrainingStatus.STOPPED
                logger.info(f"[Job {cfg.job_id}] Training STOPPED by user")
            
            self._update_job_status(job)
            
        except Exception as e:
            logger.error(f"[Job {cfg.job_id}] Training FAILED: {e}")
            job.status = TrainingStatus.FAILED
            job.error_message = str(e)
            self._update_job_status(job)
    
    def _update_job_status(self, job: TrainingJob):
        """Update job status in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE training_jobs 
                SET status = ?, started_at = ?, completed_at = ?, 
                    model_output_path = ?, error_message = ?
                WHERE job_id = ?
            ''', (
                job.status.value,
                job.started_at,
                job.completed_at,
                job.model_output_path,
                job.error_message,
                job.config.job_id
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
    
    def stop_job(self, job_id: str) -> bool:
        """Stop a running job"""
        if job_id in self.jobs:
            self.jobs[job_id].stop()
            return True
        return False
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job details"""
        if job_id in self.jobs:
            return self.jobs[job_id].to_dict()
        return None
    
    def list_jobs(self) -> List[Dict]:
        """List all jobs"""
        return [job.to_dict() for job in self.jobs.values()]
    
    def get_job_metrics(self, job_id: str, limit: int = 1000) -> List[Dict]:
        """Get training metrics for a job"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT step, epoch, loss, learning_rate, timestamp
                FROM training_metrics
                WHERE job_id = ?
                ORDER BY step DESC
                LIMIT ?
            ''', (job_id, limit))
            metrics = [
                {
                    'step': row[0],
                    'epoch': row[1],
                    'loss': row[2],
                    'lr': row[3],
                    'timestamp': row[4]
                }
                for row in cursor.fetchall()
            ]
            conn.close()
            return metrics
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []
    
    def list_available_models(self) -> List[str]:
        """List models available for fine-tuning"""
        return [
            "unsloth/Llama-3.2-1B-Instruct",
            "unsloth/Llama-3.2-3B-Instruct",
            "unsloth/tinyllama-chat-v1.0",
            "unsloth/phi-4",
            "unsloth/gemma-2-2b-it",
            "unsloth/Qwen2.5-3B-Instruct",
            "unsloth/Qwen2.5-7B-Instruct",
            "unsloth/Mistral-Small-Instruct-2409",
            "unsloth/DeepSeek-R1-Distill-Qwen-1.5B",
            "unsloth/DeepSeek-R1-Distill-Llama-8B",
        ]
    
    def list_popular_datasets(self) -> List[Dict]:
        """List popular datasets for training"""
        return [
            {
                "name": "yahma/alpaca-cleaned",
                "format": "alpaca",
                "description": "Cleaned Alpaca instruction dataset",
                "size": "~52k examples"
            },
            {
                "name": "Open-Orca/OpenOrca",
                "format": "chat",
                "description": "Large-scale instruction dataset",
                "size": "~4M examples"
            },
            {
                "name": "tatsu-lab/alpaca",
                "format": "alpaca",
                "description": "Original Alpaca dataset",
                "size": "~52k examples"
            },
            {
                "name": "HuggingFaceH4/no_robots",
                "format": "chat",
                "description": "Human-written instruction dataset",
                "size": "~10k examples"
            },
            {
                "name": "unsloth/coding-papers",
                "format": "text",
                "description": "Coding papers for technical training",
                "size": "~1k papers"
            },
        ]


# Singleton instance
trainer_instance: Optional[UnslothTrainer] = None

def get_trainer() -> UnslothTrainer:
    """Get singleton trainer instance"""
    global trainer_instance
    if trainer_instance is None:
        trainer_instance = UnslothTrainer()
    return trainer_instance


if __name__ == "__main__":
    # Test the trainer
    trainer = get_trainer()
    print("Hardware Info:", json.dumps(trainer.get_hardware_info(), indent=2))
    
    # Only run test if we have a backend
    if trainer._get_recommended_backend() != "none":
        config = {
            'job_id': 'test-job-001',
            'name': 'Test Training Job',
            'base_model': 'unsloth/tinyllama-chat-v1.0',
            'output_model': 'test-model',
            'dataset_source': 'huggingface',
            'dataset_path': 'yahma/alpaca-cleaned',
            'dataset_format': 'alpaca',
            'max_steps': 10,
            'logging_steps': 1
        }
        
        job = trainer.create_job(config)
        print(f"Created job: {job.to_dict()}")
        
        # Start training
        trainer.start_training(config['job_id'])
        
        # Monitor progress
        while job.status in [TrainingStatus.STARTING, TrainingStatus.RUNNING]:
            print(f"Status: {job.status.value}, Progress: {job.progress}%, Loss: {job.loss:.4f}")
            time.sleep(2)
        
        print(f"Final status: {job.status.value}")
    else:
        print("No training backend available. Install unsloth or transformers.")
