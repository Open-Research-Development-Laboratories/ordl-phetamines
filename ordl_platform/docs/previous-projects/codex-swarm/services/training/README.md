# ORDL Command Post - AI Training Pipeline

Real AI training pipeline using **Unsloth** and **TRL** for efficient fine-tuning of Large Language Models.

## Features

- 🚀 **Unsloth Integration**: 2-5x faster training with 80% less memory
- 🎯 **TRL Support**: State-of-the-art supervised fine-tuning
- 💾 **QLoRA**: 4-bit quantization for training large models on consumer GPUs
- 🔄 **CPU Fallback**: Automatic fallback to CPU training when GPU unavailable
- 📊 **Real Progress Tracking**: Live loss curves and training metrics
- 🗂️ **Model Registry**: Persistent storage of trained models
- 📦 **Multiple Export Formats**: GGUF, AWQ, GPTQ quantization
- 🌐 **REST API**: Flask-compatible API for integration

## Installation

### Prerequisites

- Python 3.9+
- CUDA 11.8+ (for GPU training)
- 8GB+ RAM (16GB+ recommended)

### Install Dependencies

```bash
cd /opt/codex-swarm/services/training
pip install -r requirements.txt
```

### Hardware Detection

```python
from services.training import get_hardware_info

info = get_hardware_info()
print(f"CUDA Available: {info['cuda_available']}")
print(f"GPUs: {info['gpu_names']}")
print(f"GPU Memory: {info['gpu_memory_gb']} GB")
```

## Quick Start

### 1. Simple Training Job

```python
from services.training import create_training_job

# Create trainer
trainer = create_training_job(
    name="my-first-model",
    base_model="unsloth/Llama-3.2-1B-Instruct",
    dataset_path="yahma/alpaca-cleaned",
    dataset_format="alpaca",
    num_epochs=3,
    batch_size=2
)

# Run training
progress = trainer.train()
print(f"Training completed: {progress.status}")
print(f"Final loss: {progress.loss}")
```

### 2. Advanced Configuration

```python
from services.training import (
    TrainingConfig, LoRAConfig, DatasetFormat,
    ModelTrainer, ProgressTracker
)

# Create custom config
config = TrainingConfig(
    name="advanced-training",
    base_model="unsloth/Llama-3.2-3B-Instruct",
    dataset_path="path/to/dataset.json",
    dataset_format=DatasetFormat.ALPACA,
    num_epochs=5,
    learning_rate=2e-4,
    batch_size=1,
    gradient_accumulation_steps=8,
    max_seq_length=4096,
    lora=LoRAConfig(
        r=64,
        alpha=128,
        dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
    ),
    load_in_4bit=True,
    output_dir="./my_model"
)

# Create trainer with progress tracking
trainer = ModelTrainer(config)
tracker = ProgressTracker(trainer.progress, update_interval=10)
trainer.add_callback(tracker)

# Train
progress = trainer.train()
```

### 3. Dataset Loading

```python
from services.training import DatasetLoader

loader = DatasetLoader()

# From HuggingFace
dataset = loader.load_from_huggingface("yahma/alpaca-cleaned")

# From local file
dataset = loader.load_from_file("./data/training.jsonl", format="jsonl")

# From URL
dataset = loader.load_from_url("https://example.com/dataset.json")

# Convert format
converted = loader.convert_format(dataset, "alpaca", "text")
```

### 4. Model Management

```python
from services.training import ModelRegistry, ModelQuantizer

# Register a model
registry = ModelRegistry()
model_id = registry.register_model(
    model_name="my-model",
    base_model="llama-3.2-1B",
    training_job_id="train-123",
    model_path="./outputs/final",
    metrics={'final_loss': 0.5}
)

# List models
models = registry.list_models()

# Quantize to GGUF
quantizer = ModelQuantizer()
result = quantizer.quantize_to_gguf(
    model_path="./outputs/final",
    quant_type="Q4_K_M"
)
print(f"Quantized: {result.quantized_size_mb} MB")
```

### 5. Export to GGUF

```python
# After training
output_path = trainer.export_to_gguf(
    quantization="Q4_K_M",
    output_path="./model-q4.gguf"
)
```

## API Integration

### Flask Blueprint

```python
from flask import Flask
from services.training.api import register_with_app

app = Flask(__name__)
register_with_app(app)

# Training endpoints now available at:
# GET  /api/training/hardware
# GET  /api/training/jobs
# POST /api/training/jobs
# GET  /api/training/jobs/<id>
# GET  /api/training/jobs/<id>/stream
# DELETE /api/training/jobs/<id>
```

### API Endpoints

#### Get Hardware Info
```bash
GET /api/training/hardware
```

#### Create Training Job
```bash
POST /api/training/jobs
Content-Type: application/json

{
  "name": "my-training",
  "base_model": "unsloth/Llama-3.2-1B-Instruct",
  "dataset": "yahma/alpaca-cleaned",
  "dataset_format": "alpaca",
  "epochs": 3,
  "batch_size": 2
}
```

#### Stream Progress
```bash
GET /api/training/jobs/<job_id>/stream
# Server-Sent Events stream
```

## Configuration Presets

### QLoRA (Low VRAM)
```python
from services.training import get_qlora_config

config = get_qlora_config("qlora-training")
# 4-bit quantization, small batches, good for 8GB GPUs
```

### CPU Training
```python
from services.training import get_cpu_fallback_config

config = get_cpu_fallback_config("cpu-training")
# Optimized for CPU-only machines
```

## Dataset Formats

### Alpaca Format
```json
{
  "instruction": "What is the capital of France?",
  "input": "",
  "output": "The capital of France is Paris."
}
```

### ShareGPT Format
```json
{
  "conversations": [
    {"from": "human", "value": "Hello!"},
    {"from": "gpt", "value": "Hi there!"}
  ]
}
```

### Raw Format
```json
{
  "text": "Any text content here..."
}
```

## Monitoring

### Progress Callback
```python
class MyCallback(TrainingCallback):
    def on_step_end(self, step, loss, learning_rate, config):
        print(f"Step {step}: loss={loss:.4f}, lr={learning_rate:.2e}")
    
    def on_epoch_end(self, epoch, loss, config):
        print(f"Epoch {epoch} completed: loss={loss:.4f}")

trainer.add_callback(MyCallback())
```

### TensorBoard
```python
config = TrainingConfig(
    report_to=["tensorboard"],
    logging_steps=10
)
```

## Troubleshooting

### Out of Memory
```python
config = TrainingConfig(
    load_in_4bit=True,           # Use 4-bit quantization
    batch_size=1,                # Reduce batch size
    gradient_accumulation_steps=8,  # Accumulate gradients
    max_seq_length=1024          # Reduce sequence length
)
```

### Slow Training on CPU
- Use smaller models (1B parameters)
- Reduce `max_seq_length` to 512
- Use fewer epochs

### CUDA Errors
```bash
# Check CUDA installation
python -c "import torch; print(torch.cuda.is_available())"

# Clear CUDA cache
python -c "import torch; torch.cuda.empty_cache()"
```

## File Structure

```
services/training/
├── __init__.py          # Package exports
├── config.py            # Configuration schemas
├── trainer.py           # Main training orchestrator
├── dataset_loader.py    # Dataset ingestion
├── model_manager.py     # Model registry & quantization
├── api.py               # Flask API integration
├── requirements.txt     # Dependencies
└── README.md            # This file
```

## Supported Models

- Llama 2/3 (7B, 13B, 70B)
- Mistral (7B)
- Qwen (7B, 14B)
- Phi-3 (3.8B, 7B)
- Gemma (2B, 7B)
- Any HuggingFace causal LM

## License

Part of the ORDL Command Post system.
