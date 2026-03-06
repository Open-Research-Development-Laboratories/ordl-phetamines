"""
ORDL Command Post - Training Service
Real AI training pipeline using Unsloth and TRL.
"""

__version__ = "1.0.0"
__author__ = "ORDL Command Post"

# Main exports
from .config import (
    TrainingConfig,
    LoRAConfig,
    DatasetFormat,
    ModelType,
    QuantizationType,
    OptimizerType,
    load_config,
    save_config,
    get_default_config,
    get_qlora_config,
    get_cpu_fallback_config
)

from .trainer import (
    ModelTrainer,
    TrainingProgress,
    TrainingCallback,
    ProgressTracker,
    get_hardware_info,
    create_training_job
)

from .dataset_loader import (
    DatasetLoader,
    DatasetInfo,
    load_dataset_for_training
)

from .model_manager import (
    ModelRegistry,
    ModelQuantizer,
    ModelDeployer,
    ModelVersion,
    QuantizationResult,
    upload_to_huggingface
)

__all__ = [
    # Config
    'TrainingConfig',
    'LoRAConfig',
    'DatasetFormat',
    'ModelType',
    'QuantizationType',
    'OptimizerType',
    'load_config',
    'save_config',
    'get_default_config',
    'get_qlora_config',
    'get_cpu_fallback_config',
    
    # Trainer
    'ModelTrainer',
    'TrainingProgress',
    'TrainingCallback',
    'ProgressTracker',
    'get_hardware_info',
    'create_training_job',
    
    # Dataset
    'DatasetLoader',
    'DatasetInfo',
    'load_dataset_for_training',
    
    # Model Manager
    'ModelRegistry',
    'ModelQuantizer',
    'ModelDeployer',
    'ModelVersion',
    'QuantizationResult',
    'upload_to_huggingface',
]
