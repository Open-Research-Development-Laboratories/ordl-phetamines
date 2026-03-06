"""
ORDL Command Post - Training Configuration Schemas
Defines configuration classes for model training with Pydantic validation.
"""

import os
import json
from typing import List, Optional, Dict, Any, Literal, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

# Try to import pydantic, fall back to dataclasses if not available
try:
    from pydantic import BaseModel, Field, validator
    USE_PYDANTIC = True
except ImportError:
    USE_PYDANTIC = False


class DatasetFormat(str, Enum):
    """Supported dataset formats"""
    ALPACA = "alpaca"
    SHAREGPT = "sharegpt"
    RAW = "raw"
    OPENAI = "openai"
    CONVERSATION = "conversation"


class ModelType(str, Enum):
    """Supported model types for training"""
    LLAMA = "llama"
    MISTRAL = "mistral"
    PHI = "phi"
    GEMMA = "gemma"
    QWEN = "qwen"
    MIXTRAL = "mixtral"


class QuantizationType(str, Enum):
    """Quantization methods"""
    Q4_K_M = "q4_k_m"      # 4-bit, medium quality
    Q5_K_M = "q5_k_m"      # 5-bit, good quality
    Q6_K = "q6_k"          # 6-bit, high quality
    Q8_0 = "q8_0"          # 8-bit, best quality
    AWQ = "awq"            # Activation-aware weight quantization
    GPTQ = "gptq"          # GPTQ quantization
    BF16 = "bf16"          # Brain float 16
    FP16 = "fp16"          # Float 16


class OptimizerType(str, Enum):
    """Supported optimizers"""
    ADAMW = "adamw_torch"
    ADAMW_8BIT = "adamw_8bit"
    ADAMW_BNB = "adamw_bnb_8bit"
    ADAMW_HF = "adamw_hf"
    SGD = "sgd"
    ADAFACTOR = "adafactor"


if USE_PYDANTIC:
    class LoRAConfig(BaseModel):
        """LoRA/QLoRA configuration"""
        r: int = Field(default=16, ge=1, le=256, description="LoRA rank")
        alpha: int = Field(default=16, ge=1, le=512, description="LoRA alpha (scaling factor)")
        dropout: float = Field(default=0.0, ge=0.0, le=1.0, description="Dropout probability")
        target_modules: List[str] = Field(
            default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj", 
                                     "gate_proj", "up_proj", "down_proj"],
            description="Modules to apply LoRA to"
        )
        use_rslora: bool = Field(default=False, description="Use rank-stabilized LoRA")
        use_dora: bool = Field(default=False, description="Use weight-decomposed LoRA")
        init_lora_weights: str = Field(default="gaussian", description="Initialization method")
        
        @validator('target_modules')
        def validate_target_modules(cls, v):
            valid_modules = ["q_proj", "k_proj", "v_proj", "o_proj", 
                           "gate_proj", "up_proj", "down_proj",
                           "lm_head", "embed_tokens", "self_attn", "mlp"]
            for module in v:
                if module not in valid_modules:
                    raise ValueError(f"Invalid target module: {module}")
            return v

    class TrainingConfig(BaseModel):
        """Main training configuration"""
        # Job identification
        job_id: Optional[str] = None
        name: str = Field(default="training-job", description="Job name")
        output_dir: str = Field(default="./outputs", description="Output directory")
        
        # Base model
        base_model: str = Field(default="unsloth/Llama-3.2-1B-Instruct", description="Base model name/path")
        model_type: ModelType = Field(default=ModelType.LLAMA, description="Model architecture type")
        
        # Dataset
        dataset_source: str = Field(default="local", description="Dataset source: huggingface, local, url")
        dataset_path: str = Field(default="", description="Dataset path or URL")
        dataset_format: DatasetFormat = Field(default=DatasetFormat.ALPACA, description="Dataset format")
        text_column: str = Field(default="text", description="Text column name for raw format")
        
        # LoRA configuration
        lora: LoRAConfig = Field(default_factory=LoRAConfig, description="LoRA configuration")
        
        # Training hyperparameters
        learning_rate: float = Field(default=2e-4, ge=1e-6, le=1e-1, description="Learning rate")
        num_epochs: int = Field(default=3, ge=1, le=100, description="Number of training epochs")
        batch_size: int = Field(default=2, ge=1, le=256, description="Per-device batch size")
        gradient_accumulation_steps: int = Field(default=4, ge=1, le=1024, description="Gradient accumulation steps")
        warmup_steps: int = Field(default=5, ge=0, description="Number of warmup steps")
        max_seq_length: int = Field(default=2048, ge=32, le=65536, description="Maximum sequence length")
        
        # Optimization
        optimizer: OptimizerType = Field(default=OptimizerType.ADAMW_8BIT, description="Optimizer type")
        weight_decay: float = Field(default=0.01, ge=0.0, le=1.0, description="Weight decay")
        max_grad_norm: float = Field(default=0.3, ge=0.0, le=10.0, description="Max gradient norm for clipping")
        lr_scheduler_type: str = Field(default="linear", description="Learning rate scheduler")
        
        # Memory optimization
        use_gradient_checkpointing: bool = Field(default=True, description="Use gradient checkpointing")
        max_grad_norm_value: Optional[float] = Field(default=0.3, description="Gradient clipping value")
        group_by_length: bool = Field(default=True, description="Group sequences by length for efficiency")
        
        # Precision
        dtype: str = Field(default="float16", description="Data type: float16, bfloat16, float32")
        load_in_4bit: bool = Field(default=True, description="Load model in 4-bit precision")
        load_in_8bit: bool = Field(default=False, description="Load model in 8-bit precision")
        
        # Checkpointing
        save_steps: int = Field(default=50, ge=1, description="Save checkpoint every N steps")
        save_total_limit: int = Field(default=2, ge=1, description="Maximum number of checkpoints to keep")
        
        # Logging
        logging_steps: int = Field(default=1, ge=1, description="Log every N steps")
        report_to: List[str] = Field(default_factory=lambda: ["tensorboard"], description="Reporting integrations")
        
        # Hardware
        device: str = Field(default="auto", description="Device: auto, cuda, cpu")
        num_gpus: Optional[int] = Field(default=None, description="Number of GPUs to use")
        
        # Quantization for export
        quantization: QuantizationType = Field(default=QuantizationType.Q4_K_M, description="Export quantization type")
        
        # Advanced options
        seed: int = Field(default=42, description="Random seed")
        packing: bool = Field(default=False, description="Use sequence packing")
        neftune_noise_alpha: Optional[float] = Field(default=None, description="NEFTune noise alpha")
        
        class Config:
            json_schema_extra = {
                "example": {
                    "name": "llama-finetune",
                    "base_model": "unsloth/Llama-3.2-1B-Instruct",
                    "dataset_path": "yahma/alpaca-cleaned",
                    "dataset_format": "alpaca",
                    "learning_rate": 2e-4,
                    "num_epochs": 3,
                    "batch_size": 2
                }
            }

else:
    # Fallback dataclass implementations
    @dataclass
    class LoRAConfig:
        """LoRA/QLoRA configuration"""
        r: int = 16
        alpha: int = 16
        dropout: float = 0.0
        target_modules: List[str] = field(default_factory=lambda: [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ])
        use_rslora: bool = False
        use_dora: bool = False
        init_lora_weights: str = "gaussian"

    @dataclass
    class TrainingConfig:
        """Main training configuration"""
        job_id: Optional[str] = None
        name: str = "training-job"
        output_dir: str = "./outputs"
        base_model: str = "unsloth/Llama-3.2-1B-Instruct"
        model_type: ModelType = ModelType.LLAMA
        dataset_source: str = "local"
        dataset_path: str = ""
        dataset_format: DatasetFormat = DatasetFormat.ALPACA
        text_column: str = "text"
        lora: LoRAConfig = field(default_factory=LoRAConfig)
        learning_rate: float = 2e-4
        num_epochs: int = 3
        batch_size: int = 2
        gradient_accumulation_steps: int = 4
        warmup_steps: int = 5
        max_seq_length: int = 2048
        optimizer: OptimizerType = OptimizerType.ADAMW_8BIT
        weight_decay: float = 0.01
        max_grad_norm: float = 0.3
        lr_scheduler_type: str = "linear"
        use_gradient_checkpointing: bool = True
        group_by_length: bool = True
        dtype: str = "float16"
        load_in_4bit: bool = True
        load_in_8bit: bool = False
        save_steps: int = 50
        save_total_limit: int = 2
        logging_steps: int = 1
        report_to: List[str] = field(default_factory=lambda: ["tensorboard"])
        device: str = "auto"
        num_gpus: Optional[int] = None
        quantization: QuantizationType = QuantizationType.Q4_K_M
        seed: int = 42
        packing: bool = False
        neftune_noise_alpha: Optional[float] = None


def load_config(config_path: Union[str, Path]) -> TrainingConfig:
    """Load configuration from JSON file"""
    with open(config_path, 'r') as f:
        data = json.load(f)
    
    # Convert string enums
    if 'dataset_format' in data and isinstance(data['dataset_format'], str):
        data['dataset_format'] = DatasetFormat(data['dataset_format'].lower())
    if 'model_type' in data and isinstance(data['model_type'], str):
        data['model_type'] = ModelType(data['model_type'].lower())
    if 'quantization' in data and isinstance(data['quantization'], str):
        data['quantization'] = QuantizationType(data['quantization'].lower())
    if 'optimizer' in data and isinstance(data['optimizer'], str):
        data['optimizer'] = OptimizerType(data['optimizer'].lower())
    
    # Parse LoRA config if present
    if 'lora' in data and isinstance(data['lora'], dict):
        data['lora'] = LoRAConfig(**data['lora'])
    
    return TrainingConfig(**data)


def save_config(config: TrainingConfig, config_path: Union[str, Path]) -> None:
    """Save configuration to JSON file"""
    if USE_PYDANTIC:
        data = config.model_dump()
    else:
        data = asdict(config)
    
    # Convert enums to strings
    for key, value in data.items():
        if isinstance(value, Enum):
            data[key] = value.value
        elif isinstance(value, list) and value and isinstance(value[0], Enum):
            data[key] = [v.value for v in value]
    
    with open(config_path, 'w') as f:
        json.dump(data, f, indent=2)


def get_default_config(name: str = "training-job") -> TrainingConfig:
    """Get default training configuration"""
    return TrainingConfig(
        name=name,
        base_model="unsloth/Llama-3.2-1B-Instruct",
        dataset_path="",
        learning_rate=2e-4,
        num_epochs=3,
        batch_size=2,
        max_seq_length=2048,
        lora=LoRAConfig(r=16, alpha=16, dropout=0.0)
    )


def get_qlora_config(name: str = "qlora-training") -> TrainingConfig:
    """Get QLoRA optimized configuration"""
    return TrainingConfig(
        name=name,
        base_model="unsloth/Llama-3.2-3B-Instruct",
        dataset_path="",
        learning_rate=2e-4,
        num_epochs=3,
        batch_size=1,
        gradient_accumulation_steps=8,
        max_seq_length=4096,
        load_in_4bit=True,
        lora=LoRAConfig(r=64, alpha=128, dropout=0.05),
        optimizer=OptimizerType.ADAMW_8BIT
    )


def get_cpu_fallback_config(name: str = "cpu-training") -> TrainingConfig:
    """Get CPU-optimized configuration"""
    return TrainingConfig(
        name=name,
        base_model="unsloth/Llama-3.2-1B-Instruct",
        dataset_path="",
        learning_rate=5e-5,
        num_epochs=1,
        batch_size=1,
        max_seq_length=512,
        load_in_4bit=False,
        load_in_8bit=False,
        dtype="float32",
        device="cpu",
        gradient_accumulation_steps=1,
        lora=LoRAConfig(r=8, alpha=16, dropout=0.0),
        optimizer=OptimizerType.ADAMW
    )
