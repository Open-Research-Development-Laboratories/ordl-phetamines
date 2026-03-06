#!/usr/bin/env python3
"""
ORDL Command Post - Training Pipeline Example
Demonstrates usage of the training pipeline.
"""

import os
import sys

# Handle imports for both module and direct execution
try:
    # Try relative imports (when run as module)
    from .trainer import (
        get_hardware_info,
        ModelTrainer,
        TrainingProgress,
        ProgressTracker,
        create_training_job
    )
    from .config import (
        TrainingConfig,
        LoRAConfig,
        DatasetFormat,
        get_qlora_config,
        get_cpu_fallback_config
    )
    from .dataset_loader import DatasetLoader
    from .model_manager import ModelRegistry, ModelQuantizer
except ImportError:
    # Fallback to absolute imports (when run directly)
    from trainer import (
        get_hardware_info,
        ModelTrainer,
        TrainingProgress,
        ProgressTracker,
        create_training_job
    )
    from config import (
        TrainingConfig,
        LoRAConfig,
        DatasetFormat,
        get_qlora_config,
        get_cpu_fallback_config
    )
    from dataset_loader import DatasetLoader
    from model_manager import ModelRegistry, ModelQuantizer


def example_hardware_detection():
    """Example: Detect hardware capabilities"""
    print("=" * 60)
    print("HARDWARE DETECTION")
    print("=" * 60)
    
    info = get_hardware_info()
    
    print(f"\nCUDA Available: {info['cuda_available']}")
    print(f"CUDA Version: {info['cuda_version']}")
    print(f"Number of GPUs: {info['cuda_devices']}")
    print(f"GPU Names: {info['gpu_names']}")
    print(f"GPU Memory: {info['gpu_memory_gb']} GB")
    print(f"CPU Cores: {info['cpu_count']}")
    print(f"RAM: {info['ram_gb']:.1f} GB")
    print(f"Supports BF16: {info['supports_bf16']}")
    print(f"Supports FP16: {info['supports_fp16']}")
    
    return info


def example_config_creation():
    """Example: Create training configurations"""
    print("\n" + "=" * 60)
    print("CONFIGURATION CREATION")
    print("=" * 60)
    
    # Default config
    print("\n1. Default Config:")
    default_config = TrainingConfig(
        name="default-training",
        base_model="unsloth/Llama-3.2-1B-Instruct",
        dataset_path="yahma/alpaca-cleaned",
        dataset_format=DatasetFormat.ALPACA,
        num_epochs=3,
        batch_size=2
    )
    print(f"   Name: {default_config.name}")
    print(f"   Model: {default_config.base_model}")
    print(f"   Epochs: {default_config.num_epochs}")
    print(f"   Batch Size: {default_config.batch_size}")
    print(f"   LoRA r: {default_config.lora.r}")
    
    # QLoRA config
    print("\n2. QLoRA Config (for low VRAM):")
    qlora_config = get_qlora_config("qlora-training")
    print(f"   Load in 4-bit: {qlora_config.load_in_4bit}")
    print(f"   LoRA r: {qlora_config.lora.r}")
    print(f"   LoRA alpha: {qlora_config.lora.alpha}")
    print(f"   Gradient Accumulation: {qlora_config.gradient_accumulation_steps}")
    
    # CPU config
    print("\n3. CPU Fallback Config:")
    cpu_config = get_cpu_fallback_config("cpu-training")
    print(f"   Device: {cpu_config.device}")
    print(f"   Batch Size: {cpu_config.batch_size}")
    print(f"   Max Seq Length: {cpu_config.max_seq_length}")
    
    return default_config


def example_dataset_loading():
    """Example: Load and prepare datasets"""
    print("\n" + "=" * 60)
    print("DATASET LOADING")
    print("=" * 60)
    
    loader = DatasetLoader()
    
    # Show available sources
    print("\nDataset Sources:")
    print("  - HuggingFace: loader.load_from_huggingface('yahma/alpaca-cleaned')")
    print("  - Local File: loader.load_from_file('./data.json')")
    print("  - URL: loader.load_from_url('https://example.com/dataset.json')")
    
    # Show format conversion
    print("\nFormat Conversion:")
    print("  - Alpaca -> Text")
    print("  - ShareGPT -> Text")
    print("  - Raw -> Text")
    
    return loader


def example_model_management():
    """Example: Model registry and quantization"""
    print("\n" + "=" * 60)
    print("MODEL MANAGEMENT")
    print("=" * 60)
    
    # Registry
    print("\n1. Model Registry:")
    registry = ModelRegistry()
    print("   - Register trained models")
    print("   - Track versions")
    print("   - Store metadata")
    
    # Quantizer
    print("\n2. Model Quantization:")
    quantizer = ModelQuantizer()
    print("   - GGUF (Q4_K_M, Q5_K_M, Q6_K, Q8_0)")
    print("   - AWQ")
    print("   - GPTQ")


def example_training_setup():
    """Example: Setup a training job"""
    print("\n" + "=" * 60)
    print("TRAINING SETUP")
    print("=" * 60)
    
    # Create trainer
    print("\n1. Creating training job:")
    trainer = create_training_job(
        name="example-training",
        base_model="unsloth/Llama-3.2-1B-Instruct",
        dataset_path="yahma/alpaca-cleaned",
        dataset_format="alpaca",
        num_epochs=1,  # Just 1 epoch for demo
        batch_size=1
    )
    print(f"   Job ID: {trainer.progress.job_id}")
    print(f"   Config: {trainer.config.name}")
    
    # Add progress tracking
    print("\n2. Adding progress tracking:")
    tracker = ProgressTracker(trainer.progress, update_interval=10)
    trainer.add_callback(tracker)
    print("   ProgressTracker added")
    
    # Show what would happen
    print("\n3. To start training, run:")
    print("   progress = trainer.train()")
    print("   This will:")
    print("   - Load base model")
    print("   - Apply LoRA adapters")
    print("   - Load dataset")
    print("   - Train for specified epochs")
    print("   - Save final model")
    
    return trainer


def example_api_usage():
    """Example: API integration"""
    print("\n" + "=" * 60)
    print("API INTEGRATION")
    print("=" * 60)
    
    print("\n1. Flask Integration:")
    print("   from services.training.api import register_with_app")
    print("   register_with_app(app)")
    
    print("\n2. Available Endpoints:")
    print("   GET  /api/training/hardware")
    print("   GET  /api/training/jobs")
    print("   POST /api/training/jobs")
    print("   GET  /api/training/jobs/<id>")
    print("   GET  /api/training/jobs/<id>/stream")
    
    print("\n3. Example Request:")
    print("""   curl -X POST http://localhost:5000/api/training/jobs \\
        -H "Content-Type: application/json" \\
        -H "Authorization: Bearer <token>" \\
        -d '{
          "name": "my-training",
          "base_model": "unsloth/Llama-3.2-1B-Instruct",
          "dataset": "yahma/alpaca-cleaned",
          "epochs": 3,
          "batch_size": 2
        }'""")


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 12 + "ORDL TRAINING PIPELINE" + " " * 24 + "║")
    print("║" + " " * 6 + "Unsloth + TRL Integration Demo" + " " * 20 + "║")
    print("╚" + "=" * 58 + "╝")
    
    try:
        # Run examples
        example_hardware_detection()
        example_config_creation()
        example_dataset_loading()
        example_model_management()
        example_training_setup()
        example_api_usage()
        
        print("\n" + "=" * 60)
        print("EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nTo run actual training:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Prepare your dataset")
        print("  3. Create a training config")
        print("  4. Run: trainer = create_training_job(...); trainer.train()")
        print("\n")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
