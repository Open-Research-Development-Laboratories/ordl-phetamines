"""
ORDL Command Post - AI Training Pipeline
Main training orchestrator using Unsloth and TRL for efficient fine-tuning.
"""

import os
import sys
import json
import time
import psutil
import signal
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List, Union
from datetime import datetime
from dataclasses import dataclass, field
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Training configuration imports
from .config import (
    TrainingConfig, LoRAConfig, load_config, save_config,
    get_default_config, get_qlora_config, get_cpu_fallback_config,
    QuantizationType, OptimizerType, DatasetFormat
)
from .dataset_loader import DatasetLoader, load_dataset_for_training
from .model_manager import ModelRegistry, ModelQuantizer, upload_to_huggingface

# GPU Detection and Hardware Info
def get_hardware_info() -> Dict[str, Any]:
    """Detect available hardware and capabilities"""
    info = {
        'cuda_available': False,
        'cuda_devices': 0,
        'cuda_version': None,
        'gpu_names': [],
        'gpu_memory_gb': [],
        'cpu_count': psutil.cpu_count(),
        'ram_gb': psutil.virtual_memory().total / (1024**3),
        'supports_bf16': False,
        'supports_fp16': False
    }
    
    try:
        import torch
        info['cuda_available'] = torch.cuda.is_available()
        
        if info['cuda_available']:
            info['cuda_devices'] = torch.cuda.device_count()
            info['cuda_version'] = torch.version.cuda
            
            for i in range(info['cuda_devices']):
                props = torch.cuda.get_device_properties(i)
                info['gpu_names'].append(props.name)
                memory_gb = props.total_memory / (1024**3)
                info['gpu_memory_gb'].append(round(memory_gb, 2))
            
            # Check supported dtypes
            info['supports_fp16'] = True  # Most GPUs support FP16
            
            # BF16 support check
            try:
                if hasattr(torch.cuda, 'is_bf16_supported'):
                    info['supports_bf16'] = torch.cuda.is_bf16_supported()
            except:
                pass
    except ImportError:
        logger.warning("PyTorch not available")
    
    return info


@dataclass
class TrainingProgress:
    """Training progress tracking"""
    job_id: str
    status: str = "initializing"  # initializing, running, completed, failed, cancelled
    current_step: int = 0
    total_steps: int = 0
    current_epoch: int = 0
    total_epochs: int = 0
    loss: float = 0.0
    learning_rate: float = 0.0
    epoch_losses: List[float] = field(default_factory=list)
    step_losses: List[Dict[str, Any]] = field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    estimated_time_remaining: Optional[str] = None
    tokens_per_sec: float = 0.0
    samples_per_sec: float = 0.0
    gpu_memory_mb: Optional[float] = None
    error_message: Optional[str] = None
    checkpoint_path: Optional[str] = None


class TrainingCallback:
    """Callback interface for training events"""
    
    def on_train_begin(self, config: TrainingConfig):
        pass
    
    def on_train_end(self, config: TrainingConfig, progress: TrainingProgress):
        pass
    
    def on_epoch_begin(self, epoch: int, config: TrainingConfig):
        pass
    
    def on_epoch_end(self, epoch: int, loss: float, config: TrainingConfig):
        pass
    
    def on_step_end(self, step: int, loss: float, learning_rate: float, config: TrainingConfig):
        pass
    
    def on_evaluate(self, metrics: Dict[str, float]):
        pass
    
    def on_save(self, checkpoint_path: str):
        pass


class ProgressTracker(TrainingCallback):
    """Tracks and logs training progress"""
    
    def __init__(self, progress: TrainingProgress, update_interval: int = 1):
        self.progress = progress
        self.update_interval = update_interval
        self._last_update = 0
        self._step_times = []
        self._start_time = None
    
    def on_train_begin(self, config: TrainingConfig):
        self.progress.start_time = datetime.utcnow().isoformat()
        self.progress.status = "running"
        self._start_time = time.time()
        logger.info(f"Training started: {config.name}")
    
    def on_train_end(self, config: TrainingConfig, progress: TrainingProgress):
        self.progress.end_time = datetime.utcnow().isoformat()
        duration = time.time() - self._start_time if self._start_time else 0
        logger.info(f"Training completed in {duration:.2f}s")
    
    def on_epoch_begin(self, epoch: int, config: TrainingConfig):
        self.progress.current_epoch = epoch
        logger.info(f"Epoch {epoch + 1}/{config.num_epochs} started")
    
    def on_epoch_end(self, epoch: int, loss: float, config: TrainingConfig):
        self.progress.epoch_losses.append(loss)
        logger.info(f"Epoch {epoch + 1} completed - Loss: {loss:.4f}")
    
    def on_step_end(self, step: int, loss: float, learning_rate: float, config: TrainingConfig):
        self.progress.current_step = step
        self.progress.loss = loss
        self.progress.learning_rate = learning_rate
        
        # Calculate speed
        self._step_times.append(time.time())
        if len(self._step_times) > 10:
            self._step_times.pop(0)
        
        if len(self._step_times) >= 2:
            time_per_step = (self._step_times[-1] - self._step_times[0]) / (len(self._step_times) - 1)
            self.progress.samples_per_sec = config.batch_size / time_per_step if time_per_step > 0 else 0
        
        # Log periodically
        if step % self.update_interval == 0:
            self.progress.step_losses.append({
                'step': step,
                'loss': loss,
                'learning_rate': learning_rate,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Estimate remaining time
            if self._start_time and self.progress.total_steps > 0:
                elapsed = time.time() - self._start_time
                progress_pct = step / self.progress.total_steps
                if progress_pct > 0:
                    total_estimated = elapsed / progress_pct
                    remaining = total_estimated - elapsed
                    self.progress.estimated_time_remaining = f"{int(remaining // 60)}m {int(remaining % 60)}s"
            
            # GPU memory
            if psutil.cuda_available():
                import torch
                self.progress.gpu_memory_mb = torch.cuda.memory_allocated() / (1024**2)
            
            logger.debug(f"Step {step} - Loss: {loss:.4f}, LR: {learning_rate:.2e}")


class ModelTrainer:
    """
    Main training orchestrator using Unsloth and TRL.
    Supports GPU training with automatic CPU fallback.
    """
    
    def __init__(self, config: TrainingConfig, progress: Optional[TrainingProgress] = None):
        self.config = config
        self.hardware = get_hardware_info()
        self.progress = progress or TrainingProgress(job_id=config.job_id or self._generate_job_id())
        self.callbacks: List[TrainingCallback] = []
        self._stop_requested = False
        self._trainer = None
        self._model = None
        self._tokenizer = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _generate_job_id(self) -> str:
        """Generate unique job ID"""
        return f"train-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{os.urandom(4).hex()}"
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received, stopping training...")
        self.stop()
    
    def add_callback(self, callback: TrainingCallback):
        """Add a training callback"""
        self.callbacks.append(callback)
    
    def stop(self):
        """Request training stop"""
        self._stop_requested = True
        self.progress.status = "cancelled"
    
    def _should_stop(self) -> bool:
        """Check if training should stop"""
        return self._stop_requested
    
    def _check_unsloth_available(self) -> bool:
        """Check if Unsloth is available and compatible"""
        try:
            import unsloth
            return True
        except ImportError:
            return False
    
    def _check_trl_available(self) -> bool:
        """Check if TRL is available"""
        try:
            import trl
            return True
        except ImportError:
            return False
    
    def _auto_adjust_config(self):
        """Automatically adjust config based on hardware"""
        if not self.hardware['cuda_available']:
            logger.warning("CUDA not available, switching to CPU configuration")
            self.config = get_cpu_fallback_config(self.config.name)
            return
        
        # Adjust based on available VRAM
        if self.hardware['gpu_memory_gb']:
            min_vram = min(self.hardware['gpu_memory_gb'])
            
            if min_vram < 8:
                logger.info(f"Low VRAM detected ({min_vram}GB), adjusting settings")
                self.config.load_in_4bit = True
                self.config.batch_size = min(self.config.batch_size, 1)
                self.config.gradient_accumulation_steps = max(self.config.gradient_accumulation_steps, 8)
                self.config.lora.r = min(self.config.lora.r, 8)
            elif min_vram < 16:
                logger.info(f"Medium VRAM detected ({min_vram}GB)")
                self.config.load_in_4bit = True
            else:
                logger.info(f"High VRAM detected ({min_vram}GB), can use full precision")
        
        # Use BF16 if supported and requested
        if self.config.dtype == "bfloat16" and not self.hardware['supports_bf16']:
            logger.warning("BF16 not supported, falling back to FP16")
            self.config.dtype = "float16"
    
    def train(self) -> TrainingProgress:
        """
        Main training loop.
        
        Returns:
            TrainingProgress with final results
        """
        try:
            # Auto-adjust configuration
            self._auto_adjust_config()
            
            # Notify callbacks
            for cb in self.callbacks:
                cb.on_train_begin(self.config)
            
            # Choose training method based on hardware
            if self.hardware['cuda_available'] and self._check_unsloth_available():
                return self._train_with_unsloth()
            elif self._check_trl_available():
                return self._train_with_trl()
            else:
                return self._train_cpu_fallback()
                
        except Exception as e:
            logger.error(f"Training failed: {e}")
            logger.error(traceback.format_exc())
            self.progress.status = "failed"
            self.progress.error_message = str(e)
            
            for cb in self.callbacks:
                cb.on_train_end(self.config, self.progress)
            
            return self.progress
    
    def _train_with_unsloth(self) -> TrainingProgress:
        """Training using Unsloth for maximum efficiency"""
        logger.info("Using Unsloth for fast training")
        
        try:
            from unsloth import FastLanguageModel, is_bfloat16_supported
            from trl import SFTTrainer
            from transformers import TrainingArguments
            
            # Load model and tokenizer
            logger.info(f"Loading base model: {self.config.base_model}")
            
            dtype = self.config.dtype
            if dtype == "bfloat16" and not is_bfloat16_supported():
                dtype = "float16"
            
            self._model, self._tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.config.base_model,
                max_seq_length=self.config.max_seq_length,
                dtype=getattr(__import__('torch'), dtype) if hasattr(__import__('torch'), dtype) else None,
                load_in_4bit=self.config.load_in_4bit,
            )
            
            # Add LoRA adapters
            logger.info("Adding LoRA adapters...")
            self._model = FastLanguageModel.get_peft_model(
                self._model,
                r=self.config.lora.r,
                target_modules=self.config.lora.target_modules,
                lora_alpha=self.config.lora.alpha,
                lora_dropout=self.config.lora.dropout,
                bias="none",
                use_gradient_checkpointing=self.config.use_gradient_checkpointing,
                random_state=self.config.seed,
                use_rslora=self.config.lora.use_rslora,
            )
            
            # Load dataset
            logger.info("Loading dataset...")
            dataset_loader = DatasetLoader()
            
            if self.config.dataset_source == "huggingface":
                dataset = dataset_loader.load_from_huggingface(self.config.dataset_path)
            elif self.config.dataset_source == "url":
                dataset = dataset_loader.load_from_url(self.config.dataset_path)
            else:
                dataset = dataset_loader.load_from_file(self.config.dataset_path)
            
            # Convert format
            if self.config.dataset_format.value != "raw":
                dataset = dataset_loader.convert_format(
                    dataset,
                    self.config.dataset_format.value,
                    "text"
                )
            
            # Calculate total steps
            num_samples = len(dataset) if hasattr(dataset, '__len__') else 1000
            steps_per_epoch = num_samples // (self.config.batch_size * self.config.gradient_accumulation_steps)
            total_steps = steps_per_epoch * self.config.num_epochs
            self.progress.total_steps = total_steps
            self.progress.total_epochs = self.config.num_epochs
            
            # Setup training arguments
            training_args = TrainingArguments(
                output_dir=self.config.output_dir,
                num_train_epochs=self.config.num_epochs,
                per_device_train_batch_size=self.config.batch_size,
                gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                warmup_steps=self.config.warmup_steps,
                learning_rate=self.config.learning_rate,
                optim=self.config.optimizer.value,
                weight_decay=self.config.weight_decay,
                lr_scheduler_type=self.config.lr_scheduler_type,
                seed=self.config.seed,
                report_to=self.config.report_to,
                logging_steps=self.config.logging_steps,
                save_strategy="steps",
                save_steps=self.config.save_steps,
                save_total_limit=self.config.save_total_limit,
                fp16=self.config.dtype == "float16",
                bf16=self.config.dtype == "bfloat16",
                max_grad_norm=self.config.max_grad_norm,
                group_by_length=self.config.group_by_length,
            )
            
            # Create custom callback for progress tracking
            class ProgressCallback:
                def __init__(self, trainer_obj):
                    self.trainer = trainer_obj
                
                def on_step_end(self, args, state, control, **kwargs):
                    if self.trainer._should_stop():
                        control.should_training_stop = True
                    
                    # Update progress
                    self.trainer.progress.current_step = state.global_step
                    if state.log_history:
                        latest = state.log_history[-1]
                        if 'loss' in latest:
                            self.trainer.progress.loss = latest['loss']
                            self.trainer.progress.learning_rate = latest.get('learning_rate', 0)
                            
                            for cb in self.trainer.callbacks:
                                cb.on_step_end(
                                    state.global_step,
                                    latest['loss'],
                                    latest.get('learning_rate', 0),
                                    self.trainer.config
                                )
                
                def on_epoch_end(self, args, state, control, **kwargs):
                    epoch = int(state.epoch)
                    if state.log_history:
                        losses = [h['loss'] for h in state.log_history if 'loss' in h and 'epoch' in h and int(h['epoch']) == epoch]
                        if losses:
                            avg_loss = sum(losses) / len(losses)
                            for cb in self.trainer.callbacks:
                                cb.on_epoch_end(epoch, avg_loss, self.trainer.config)
            
            # Create trainer
            self._trainer = SFTTrainer(
                model=self._model,
                tokenizer=self._tokenizer,
                train_dataset=dataset,
                dataset_text_field="text",
                max_seq_length=self.config.max_seq_length,
                args=training_args,
                packing=self.config.packing,
                neftune_noise_alpha=self.config.neftune_noise_alpha,
            )
            
            # Add progress callback
            self._trainer.add_callback(ProgressCallback(self))
            
            # Train
            logger.info("Starting training...")
            self._trainer.train()
            
            # Save final model
            final_path = os.path.join(self.config.output_dir, "final")
            self._trainer.save_model(final_path)
            self._tokenizer.save_pretrained(final_path)
            
            self.progress.checkpoint_path = final_path
            self.progress.status = "completed"
            
            # Register in model registry
            registry = ModelRegistry()
            model_id = registry.register_model(
                model_name=self.config.name,
                base_model=self.config.base_model,
                training_job_id=self.progress.job_id,
                model_path=final_path,
                metrics={
                    'final_loss': self.progress.loss,
                    'epochs': self.config.num_epochs,
                    'steps': self.progress.current_step
                },
                quantization="lora-4bit" if self.config.load_in_4bit else "lora"
            )
            
            logger.info(f"Model saved and registered: {model_id}")
            
        except Exception as e:
            logger.error(f"Unsloth training failed: {e}")
            logger.error(traceback.format_exc())
            raise
        
        finally:
            for cb in self.callbacks:
                cb.on_train_end(self.config, self.progress)
        
        return self.progress
    
    def _train_with_trl(self) -> TrainingProgress:
        """Training using standard TRL (fallback for non-Unsloth)"""
        logger.info("Using TRL for training")
        
        try:
            from trl import SFTTrainer
            from transformers import (
                AutoModelForCausalLM, 
                AutoTokenizer,
                TrainingArguments,
                BitsAndBytesConfig
            )
            from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
            import torch
            
            # Setup quantization config
            quantization_config = None
            if self.config.load_in_4bit:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
            elif self.config.load_in_8bit:
                quantization_config = BitsAndBytesConfig(load_in_8bit=True)
            
            # Load model
            logger.info(f"Loading base model: {self.config.base_model}")
            self._model = AutoModelForCausalLM.from_pretrained(
                self.config.base_model,
                quantization_config=quantization_config,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.config.dtype == "float16" else torch.float32
            )
            
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.config.base_model,
                trust_remote_code=True
            )
            self._tokenizer.pad_token = self._tokenizer.eos_token
            
            # Prepare for training
            if self.config.load_in_4bit or self.config.load_in_8bit:
                self._model = prepare_model_for_kbit_training(self._model)
            
            # Add LoRA
            lora_config = LoraConfig(
                r=self.config.lora.r,
                lora_alpha=self.config.lora.alpha,
                target_modules=self.config.lora.target_modules,
                lora_dropout=self.config.lora.dropout,
                bias="none",
                task_type="CAUSAL_LM"
            )
            self._model = get_peft_model(self._model, lora_config)
            
            # Load dataset
            dataset_loader = DatasetLoader()
            if self.config.dataset_source == "huggingface":
                dataset = dataset_loader.load_from_huggingface(self.config.dataset_path)
            else:
                dataset = dataset_loader.load_from_file(self.config.dataset_path)
            
            # Convert format
            if self.config.dataset_format.value != "raw":
                dataset = dataset_loader.convert_format(
                    dataset,
                    self.config.dataset_format.value,
                    "text"
                )
            
            # Setup training
            training_args = TrainingArguments(
                output_dir=self.config.output_dir,
                num_train_epochs=self.config.num_epochs,
                per_device_train_batch_size=self.config.batch_size,
                gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                learning_rate=self.config.learning_rate,
                warmup_steps=self.config.warmup_steps,
                optim=self.config.optimizer.value,
                logging_steps=self.config.logging_steps,
                save_strategy="steps",
                save_steps=self.config.save_steps,
                fp16=self.config.dtype == "float16" and torch.cuda.is_available(),
            )
            
            self._trainer = SFTTrainer(
                model=self._model,
                args=training_args,
                train_dataset=dataset,
                tokenizer=self._tokenizer,
                dataset_text_field="text",
                max_seq_length=self.config.max_seq_length,
            )
            
            # Train
            self._trainer.train()
            
            # Save
            final_path = os.path.join(self.config.output_dir, "final")
            self._trainer.save_model(final_path)
            
            self.progress.status = "completed"
            self.progress.checkpoint_path = final_path
            
        except Exception as e:
            logger.error(f"TRL training failed: {e}")
            raise
        
        finally:
            for cb in self.callbacks:
                cb.on_train_end(self.config, self.progress)
        
        return self.progress
    
    def _train_cpu_fallback(self) -> TrainingProgress:
        """CPU-based training using transformers and llama.cpp for GGUF"""
        logger.info("Using CPU fallback training")
        
        try:
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                Trainer,
                TrainingArguments,
                DataCollatorForLanguageModeling
            )
            import torch
            
            # Force CPU
            torch.set_default_device("cpu")
            
            # Load smaller model
            logger.info(f"Loading model on CPU: {self.config.base_model}")
            
            self._tokenizer = AutoTokenizer.from_pretrained(self.config.base_model)
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            
            self._model = AutoModelForCausalLM.from_pretrained(
                self.config.base_model,
                torch_dtype=torch.float32,
                device_map="cpu",
                low_cpu_mem_usage=True
            )
            
            # Load and prepare dataset
            dataset_loader = DatasetLoader()
            if self.config.dataset_source == "local" and self.config.dataset_path:
                dataset = dataset_loader.load_from_file(self.config.dataset_path)
            else:
                # Create minimal dummy dataset for testing
                logger.warning("No dataset provided, using dummy data")
                dummy_texts = ["This is example text for training."] * 10
                dataset = [{"text": t} for t in dummy_texts]
            
            # Convert format
            if self.config.dataset_format.value != "raw":
                dataset = dataset_loader.convert_format(
                    dataset,
                    self.config.dataset_format.value,
                    "text"
                )
            
            # Simple tokenization
            def tokenize_function(examples):
                return self._tokenizer(
                    examples["text"],
                    truncation=True,
                    max_length=self.config.max_seq_length,
                    padding="max_length"
                )
            
            if hasattr(dataset, 'map'):
                tokenized_dataset = dataset.map(tokenize_function, batched=True)
            else:
                # Manual tokenization
                tokenized = []
                for item in dataset:
                    tok = self._tokenizer(
                        item["text"],
                        truncation=True,
                        max_length=self.config.max_seq_length,
                        padding="max_length"
                    )
                    tokenized.append({
                        'input_ids': tok['input_ids'],
                        'attention_mask': tok['attention_mask']
                    })
                tokenized_dataset = tokenized
            
            # Setup training arguments
            training_args = TrainingArguments(
                output_dir=self.config.output_dir,
                num_train_epochs=self.config.num_epochs,
                per_device_train_batch_size=self.config.batch_size,
                learning_rate=self.config.learning_rate,
                warmup_steps=self.config.warmup_steps,
                logging_steps=self.config.logging_steps,
                save_steps=self.config.save_steps,
                save_total_limit=1,
            )
            
            # Data collator
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=self._tokenizer,
                mlm=False
            )
            
            # Create trainer
            self._trainer = Trainer(
                model=self._model,
                args=training_args,
                train_dataset=tokenized_dataset,
                data_collator=data_collator,
            )
            
            # Train with progress tracking
            logger.info("Starting CPU training (this may be slow)...")
            self._trainer.train()
            
            # Save
            final_path = os.path.join(self.config.output_dir, "final")
            self._trainer.save_model(final_path)
            self._tokenizer.save_pretrained(final_path)
            
            self.progress.status = "completed"
            self.progress.checkpoint_path = final_path
            
            logger.info("CPU training completed")
            
        except Exception as e:
            logger.error(f"CPU training failed: {e}")
            self.progress.status = "failed"
            self.progress.error_message = str(e)
            raise
        
        finally:
            for cb in self.callbacks:
                cb.on_train_end(self.config, self.progress)
        
        return self.progress
    
    def export_to_gguf(
        self,
        quantization: str = "Q4_K_M",
        output_path: Optional[str] = None
    ) -> str:
        """
        Export trained model to GGUF format.
        
        Args:
            quantization: Quantization type (Q4_K_M, Q5_K_M, Q6_K, Q8_0)
            output_path: Output path (optional)
        
        Returns:
            Path to exported GGUF file
        """
        if not self.progress.checkpoint_path:
            raise ValueError("No trained model available for export")
        
        if output_path is None:
            output_path = os.path.join(self.config.output_dir, f"model-{quantization}.gguf")
        
        logger.info(f"Exporting to GGUF with quantization: {quantization}")
        
        quantizer = ModelQuantizer(os.path.dirname(output_path))
        result = quantizer.quantize_to_gguf(
            self.progress.checkpoint_path,
            output_name=os.path.basename(output_path).replace('.gguf', ''),
            quant_type=quantization
        )
        
        if result.success:
            logger.info(f"Successfully exported to: {result.output_path}")
            return result.output_path
        else:
            raise RuntimeError(f"Export failed: {result.error}")


def create_training_job(
    name: str,
    base_model: str,
    dataset_path: str,
    dataset_format: str = "alpaca",
    **kwargs
) -> ModelTrainer:
    """
    Convenience function to create a training job.
    
    Args:
        name: Job name
        base_model: Base model name/path
        dataset_path: Path to dataset
        dataset_format: Dataset format (alpaca, sharegpt, raw)
        **kwargs: Additional config parameters
    
    Returns:
        ModelTrainer instance
    """
    config = get_default_config(name)
    config.base_model = base_model
    config.dataset_path = dataset_path
    config.dataset_format = DatasetFormat(dataset_format.lower())
    config.dataset_source = kwargs.get('dataset_source', 'local')
    
    # Override with any additional kwargs
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return ModelTrainer(config)


# Example usage
if __name__ == "__main__":
    # Example: Create and run a training job
    print("ORDL Training Pipeline")
    print("======================")
    
    # Show hardware info
    hw = get_hardware_info()
    print(f"\nHardware:")
    print(f"  CUDA Available: {hw['cuda_available']}")
    print(f"  GPU(s): {hw['gpu_names']}")
    print(f"  RAM: {hw['ram_gb']:.1f} GB")
    
    # Example config
    config = get_default_config("example-training")
    print(f"\nConfig:")
    print(f"  Name: {config.name}")
    print(f"  Base Model: {config.base_model}")
    print(f"  Epochs: {config.num_epochs}")
    
    print("\nReady for training!")
