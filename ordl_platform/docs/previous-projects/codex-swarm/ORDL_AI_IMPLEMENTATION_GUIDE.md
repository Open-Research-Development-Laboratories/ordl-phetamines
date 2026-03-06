# ORDL AI Implementation Guide
## Technical Execution Plan for Dell R720 + AWS Hybrid Training

**Classification:** ORDL-OPERATIONAL  
**Date:** March 2, 2026  
**Version:** 1.0.0

---

## TABLE OF CONTENTS

1. [Dell R720 Setup](#1-dell-r720-setup)
2. [AWS Configuration](#2-aws-configuration)
3. [Model Training Pipeline](#3-model-training-pipeline)
4. [Hybrid Training Orchestration](#4-hybrid-training-orchestration)
5. [Monitoring & Optimization](#5-monitoring--optimization)

---

## 1. DELL R720 SETUP

### 1.1 Hardware Optimization Checklist

```bash
# Verify current hardware configuration
dmidecode -t processor | grep -E "Socket Designation|Version|Core Count|Thread Count"
dmidecode -t memory | grep -E "Size|Type|Speed" | head -30
lsblk -o NAME,SIZE,TYPE,MODEL

# Target Configuration:
# - 2x Intel Xeon E5-2697 v2 (12-core, 2.7GHz)
# - 256-512GB DDR3 ECC RAM
# - 4x SSD (RAID 10) + 4x HDD (RAID 5)
```

### 1.2 Operating System Installation

```bash
# Download Ubuntu 22.04 LTS Server
# Create bootable USB
# Install with RAID configuration

# Post-installation optimization
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    build-essential \
    git \
    wget \
    curl \
    htop \
    tmux \
    vim \
    docker.io \
    docker-compose \
    nfs-common \
    mdadm \
    smartmontools

# Configure RAID (if not done during install)
sudo mdadm --create /dev/md0 --level=10 --raid-devices=4 /dev/sd[b,c,d,e]
sudo mdadm --create /dev/md1 --level=5 --raid-devices=4 /dev/sd[f,g,h,i]

# Format and mount
sudo mkfs.ext4 /dev/md0
sudo mkfs.ext4 /dev/md1
sudo mkdir -p /data/{fast,slow}
sudo mount /dev/md0 /data/fast
sudo mount /dev/md1 /data/slow
```

### 1.3 ML Environment Setup

```bash
# Install Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3
source ~/.bashrc

# Create ML environment
conda create -n ordl-ai python=3.11 -y
conda activate ordl-ai

# Install PyTorch (CPU optimized for Intel)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install Transformers and training libraries
pip install transformers datasets accelerate deepspeed
pip install bitsandbytes peft trl unsloth

# Install monitoring and experiment tracking
pip install wandb tensorboard mlflow

# Install security-focused libraries
pip install cryptography pycryptodome

# Verify installation
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import transformers; print(f'Transformers: {transformers.__version__}')"
```

### 1.4 Intel Optimization (MKL-DNN)

```bash
# Set Intel MKL environment variables
echo 'export MKL_NUM_THREADS=24' >> ~/.bashrc
echo 'export OMP_NUM_THREADS=24' >> ~/.bashrc
echo 'export KMP_AFFINITY=granularity=fine,compact,1,0' >> ~/.bashrc
source ~/.bashrc

# Verify Intel optimizations
python -c "
import torch
print(f'Intel MKL enabled: {torch.backends.mkldnn.is_available()}')
print(f'Number of threads: {torch.get_num_threads()}')
"
```

---

## 2. AWS CONFIGURATION

### 2.1 Account Setup

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS credentials
aws configure
# Enter your Access Key ID, Secret Access Key, region (us-east-1)

# Verify configuration
aws sts get-caller-identity
```

### 2.2 SageMaker Setup

```python
# sagemaker_setup.py
import boto3
import sagemaker
from sagemaker import get_execution_role

# Initialize SageMaker session
session = sagemaker.Session()
role = get_execution_role()
region = session.boto_region_name

print(f"SageMaker Role: {role}")
print(f"Region: {region}")
print(f"Default Bucket: {session.default_bucket()}")

# Create custom VPC (optional but recommended)
ec2 = boto3.client('ec2')

# Get default VPC
response = ec2.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['true']}])
default_vpc_id = response['Vpcs'][0]['VpcId']
print(f"Default VPC: {default_vpc_id}")
```

### 2.3 Cost Optimization Configuration

```python
# aws_cost_optimization.py
import boto3

# Set up billing alerts
client = boto3.client('budgets')

# Create monthly budget
client.create_budget(
    AccountId=boto3.client('sts').get_caller_identity()['Account'],
    Budget={
        'BudgetName': 'ORDL-AI-Monthly-Budget',
        'BudgetLimit': {
            'Amount': '100',
            'Unit': 'USD'
        },
        'TimeUnit': 'MONTHLY',
        'BudgetType': 'COST',
        'CostFilters': {},
    },
    NotificationsWithSubscribers=[
        {
            'Notification': {
                'NotificationType': 'ACTUAL',
                'ComparisonOperator': 'GREATER_THAN',
                'Threshold': 80
            },
            'Subscribers': [
                {
                    'SubscriptionType': 'EMAIL',
                    'Address': 'your-email@ordl.io'
                }
            ]
        }
    ]
)

# Enable Spot instance tracking
ec2 = boto3.client('ec2')
```

---

## 3. MODEL TRAINING PIPELINE

### 3.1 Data Preprocessing

```python
# data_preprocessing.py
import json
import pandas as pd
from datasets import Dataset, DatasetDict
from transformers import AutoTokenizer
import re

class SecurityDataProcessor:
    def __init__(self, model_name="meta-llama/Llama-3.1-8B"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.tokenizer.pad_token = self.tokenizer.eos_token
    
    def clean_security_text(self, text):
        """Clean and normalize security-related text"""
        # Remove PII patterns
        text = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP_ADDRESS]', text)
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # Normalize CVE references
        text = re.sub(r'CVE-\d{4}-\d{4,}', '[CVE_REFERENCE]', text)
        
        return text.strip()
    
    def create_instruction_dataset(self, raw_data):
        """Convert raw security data to instruction format"""
        instructions = []
        
        for item in raw_data:
            instruction = {
                "instruction": item.get('task', 'Analyze the following security event'),
                "input": self.clean_security_text(item.get('input', '')),
                "output": item.get('output', ''),
                "context": item.get('context', {})
            }
            instructions.append(instruction)
        
        return Dataset.from_pandas(pd.DataFrame(instructions))
    
    def tokenize_dataset(self, dataset, max_length=2048):
        """Tokenize dataset for training"""
        def tokenize_function(examples):
            # Format as instruction-following
            texts = []
            for i in range(len(examples['instruction'])):
                text = f"### Instruction:\n{examples['instruction'][i]}\n\n### Input:\n{examples['input'][i]}\n\n### Response:\n{examples['output'][i]}"
                texts.append(text)
            
            return self.tokenizer(
                texts,
                truncation=True,
                max_length=max_length,
                padding='max_length',
                return_tensors=None
            )
        
        return dataset.map(tokenize_function, batched=True, remove_columns=dataset.column_names)

# Usage
processor = SecurityDataProcessor()
```

### 3.2 Training Script (R720-Optimized)

```python
# train_security_model.py
import torch
import torch.distributed as dist
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from datasets import load_from_disk
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import deepspeed
import os

# Configuration
MODEL_NAME = "meta-llama/Llama-3.1-8B"
OUTPUT_DIR = "/data/fast/security-model-v1"
DATA_PATH = "/data/slow/processed_security_dataset"

# Training hyperparameters (optimized for R720)
TRAINING_CONFIG = {
    "batch_size": 2,  # Small for CPU training
    "gradient_accumulation_steps": 8,
    "learning_rate": 2e-4,
    "num_epochs": 3,
    "max_length": 2048,
    "warmup_steps": 100,
    "save_steps": 500,
    "eval_steps": 500,
    "logging_steps": 10,
}

# LoRA configuration (parameter-efficient fine-tuning)
LORA_CONFIG = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

def setup_model():
    """Initialize model with optimizations"""
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.pad_token = tokenizer.eos_token
    
    # Load model (CPU-optimized, 4-bit quantization)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float32,  # Use float32 for CPU
        device_map="cpu",
        low_cpu_mem_usage=True,
    )
    
    # Apply LoRA
    model = get_peft_model(model, LORA_CONFIG)
    model.print_trainable_parameters()
    
    return model, tokenizer

def setup_training_args():
    """Configure training arguments for R720"""
    
    return TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=TRAINING_CONFIG["num_epochs"],
        per_device_train_batch_size=TRAINING_CONFIG["batch_size"],
        per_device_eval_batch_size=TRAINING_CONFIG["batch_size"],
        gradient_accumulation_steps=TRAINING_CONFIG["gradient_accumulation_steps"],
        learning_rate=TRAINING_CONFIG["learning_rate"],
        warmup_steps=TRAINING_CONFIG["warmup_steps"],
        logging_steps=TRAINING_CONFIG["logging_steps"],
        save_steps=TRAINING_CONFIG["save_steps"],
        eval_steps=TRAINING_CONFIG["eval_steps"],
        evaluation_strategy="steps",
        save_strategy="steps",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        # CPU optimizations
        dataloader_num_workers=4,
        dataloader_pin_memory=True,
        # Memory optimization
        gradient_checkpointing=True,
        fp16=False,  # Not supported on CPU
        optim="adamw_torch",
        # Reporting
        report_to=["tensorboard", "wandb"],
        logging_dir=f"{OUTPUT_DIR}/logs",
    )

def main():
    # Load dataset
    dataset = load_from_disk(DATA_PATH)
    
    # Setup model
    model, tokenizer = setup_model()
    
    # Setup training
    training_args = setup_training_args()
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False
    )
    
    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        data_collator=data_collator,
    )
    
    # Train
    trainer.train()
    
    # Save final model
    trainer.save_model(f"{OUTPUT_DIR}/final")
    tokenizer.save_pretrained(f"{OUTPUT_DIR}/final")
    
    print(f"Training complete! Model saved to {OUTPUT_DIR}/final")

if __name__ == "__main__":
    main()
```

### 3.3 AWS SageMaker Training Job

```python
# sagemaker_training.py
import sagemaker
from sagemaker.pytorch import PyTorch
from sagemaker import get_execution_role

# Configuration
role = get_execution_role()
session = sagemaker.Session()
bucket = session.default_bucket()

# Upload data to S3
input_data = session.upload_data(
    path='/data/slow/processed_security_dataset',
    bucket=bucket,
    key_prefix='security-training-data'
)

# Define estimator (using spot instances for 70% savings)
estimator = PyTorch(
    entry_point='train_security_model.py',
    source_dir='./src',
    role=role,
    framework_version='2.1.0',
    py_version='py310',
    instance_count=1,
    instance_type='ml.m5.2xlarge',  # CPU instance for cost savings
    use_spot_instances=True,
    max_wait=7200,  # 2 hours max wait
    max_run=3600,   # 1 hour max run
    checkpoint_s3_uri=f's3://{bucket}/checkpoints',
    debugger_hook_config=False,
    hyperparameters={
        'epochs': 3,
        'batch-size': 4,
        'learning-rate': 2e-4,
    }
)

# Start training
estimator.fit({'training': input_data})

# Deploy endpoint (for inference)
predictor = estimator.deploy(
    initial_instance_count=1,
    instance_type='ml.m5.large'
)
```

---

## 4. HYBRID TRAINING ORCHESTRATION

### 4.1 Training Coordinator

```python
# hybrid_orchestrator.py
import subprocess
import json
import boto3
import time
from datetime import datetime

class HybridTrainingOrchestrator:
    def __init__(self):
        self.sagemaker = boto3.client('sagemaker')
        self.local_job_id = None
        self.aws_job_name = None
        
    def start_local_training(self, config):
        """Start training on Dell R720"""
        print(f"[{datetime.now()}] Starting local training on R720...")
        
        # Run training in tmux session for persistence
        cmd = [
            'tmux', 'new-session', '-d', '-s', 'ordl-training',
            f'cd /opt/codex-swarm && conda activate ordl-ai && python train_security_model.py --config {config}'
        ]
        
        subprocess.run(cmd)
        self.local_job_id = f"local-{int(time.time())}"
        
        print(f"[{datetime.now()}] Local training started: {self.local_job_id}")
        return self.local_job_id
    
    def start_aws_training(self, job_config):
        """Start training on AWS SageMaker"""
        print(f"[{datetime.now()}] Starting AWS training...")
        
        job_name = f"ordl-training-{int(time.time())}"
        
        response = self.sagemaker.create_training_job(
            TrainingJobName=job_name,
            AlgorithmSpecification={
                'TrainingImage': job_config['image'],
                'TrainingInputMode': 'File'
            },
            RoleArn=job_config['role'],
            InputDataConfig=[{
                'ChannelName': 'training',
                'DataSource': {
                    'S3DataSource': {
                        'S3DataType': 'S3Prefix',
                        'S3Uri': job_config['data_uri'],
                        'S3DataDistributionType': 'FullyReplicated'
                    }
                }
            }],
            OutputDataConfig={
                'S3OutputPath': job_config['output_uri']
            },
            ResourceConfig={
                'InstanceType': job_config['instance_type'],
                'InstanceCount': 1,
                'VolumeSizeInGB': 100
            },
            StoppingCondition={
                'MaxRuntimeInSeconds': job_config.get('max_runtime', 3600)
            },
            CheckpointConfig={
                'S3Uri': job_config['checkpoint_uri'],
                'LocalPath': '/opt/ml/checkpoints'
            },
            EnableManagedSpotTraining=job_config.get('use_spot', True),
            StoppingCondition={
                'MaxRuntimeInSeconds': job_config.get('max_runtime', 3600),
                'MaxWaitTimeInSeconds': job_config.get('max_wait', 7200)
            } if job_config.get('use_spot') else {
                'MaxRuntimeInSeconds': job_config.get('max_runtime', 3600)
            }
        )
        
        self.aws_job_name = job_name
        print(f"[{datetime.now()}] AWS training started: {job_name}")
        return job_name
    
    def check_local_status(self):
        """Check status of local training job"""
        result = subprocess.run(
            ['tmux', 'has-session', '-t', 'ordl-training'],
            capture_output=True
        )
        return 'running' if result.returncode == 0 else 'stopped'
    
    def check_aws_status(self):
        """Check status of AWS training job"""
        if not self.aws_job_name:
            return 'not_started'
        
        response = self.sagemaker.describe_training_job(
            TrainingJobName=self.aws_job_name
        )
        return response['TrainingJobStatus']
    
    def sync_checkpoints_to_s3(self, local_path, s3_uri):
        """Sync local checkpoints to S3 for AWS continuation"""
        print(f"[{datetime.now()}] Syncing checkpoints to {s3_uri}...")
        cmd = ['aws', 's3', 'sync', local_path, s3_uri]
        subprocess.run(cmd)
        print(f"[{datetime.now()}] Checkpoint sync complete")
    
    def sync_checkpoints_from_s3(self, s3_uri, local_path):
        """Sync AWS checkpoints to local"""
        print(f"[{datetime.now()}] Syncing checkpoints from {s3_uri}...")
        cmd = ['aws', 's3', 'sync', s3_uri, local_path]
        subprocess.run(cmd)
        print(f"[{datetime.now()}] Checkpoint sync complete")

# Usage example
orchestrator = HybridTrainingOrchestrator()
```

### 4.2 Checkpoint Management

```python
# checkpoint_manager.py
import torch
import os
import json
from pathlib import Path

class CheckpointManager:
    def __init__(self, checkpoint_dir):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.checkpoint_dir / 'manifest.json'
    
    def save_checkpoint(self, model, optimizer, epoch, step, metrics, is_best=False):
        """Save training checkpoint"""
        checkpoint = {
            'epoch': epoch,
            'step': step,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'metrics': metrics,
            'timestamp': time.time()
        }
        
        # Save checkpoint
        checkpoint_path = self.checkpoint_dir / f'checkpoint-epoch{epoch}-step{step}.pt'
        torch.save(checkpoint, checkpoint_path)
        
        # Update manifest
        manifest = self.load_manifest()
        manifest['checkpoints'].append({
            'path': str(checkpoint_path),
            'epoch': epoch,
            'step': step,
            'metrics': metrics,
            'is_best': is_best
        })
        self.save_manifest(manifest)
        
        # Save best model separately
        if is_best:
            best_path = self.checkpoint_dir / 'best_model.pt'
            torch.save(checkpoint, best_path)
        
        # Cleanup old checkpoints (keep last 5)
        self.cleanup_old_checkpoints(keep=5)
        
        return checkpoint_path
    
    def load_checkpoint(self, checkpoint_path, model, optimizer=None):
        """Load training checkpoint"""
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        
        model.load_state_dict(checkpoint['model_state_dict'])
        
        if optimizer and 'optimizer_state_dict' in checkpoint:
            optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        
        return checkpoint['epoch'], checkpoint['step'], checkpoint.get('metrics', {})
    
    def load_manifest(self):
        """Load checkpoint manifest"""
        if self.manifest_file.exists():
            with open(self.manifest_file) as f:
                return json.load(f)
        return {'checkpoints': []}
    
    def save_manifest(self, manifest):
        """Save checkpoint manifest"""
        with open(self.manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
    
    def cleanup_old_checkpoints(self, keep=5):
        """Remove old checkpoints, keeping only the most recent"""
        manifest = self.load_manifest()
        checkpoints = sorted(
            manifest['checkpoints'],
            key=lambda x: x['step'],
            reverse=True
        )
        
        to_remove = checkpoints[keep:]
        for ckpt in to_remove:
            path = Path(ckpt['path'])
            if path.exists():
                path.unlink()
        
        manifest['checkpoints'] = checkpoints[:keep]
        self.save_manifest(manifest)
```

---

## 5. MONITORING & OPTIMIZATION

### 5.1 Resource Monitoring

```python
# resource_monitor.py
import psutil
import GPUtil
import time
import json
from datetime import datetime

class ResourceMonitor:
    def __init__(self, log_file='/var/log/ordl/resource_usage.json'):
        self.log_file = log_file
        self.metrics = []
        
    def get_cpu_metrics(self):
        """Get CPU usage metrics"""
        return {
            'percent': psutil.cpu_percent(interval=1, percpu=True),
            'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            'count': psutil.cpu_count(),
            'load_avg': psutil.getloadavg()
        }
    
    def get_memory_metrics(self):
        """Get memory usage metrics"""
        mem = psutil.virtual_memory()
        return {
            'total_gb': mem.total / (1024**3),
            'available_gb': mem.available / (1024**3),
            'percent': mem.percent,
            'used_gb': mem.used / (1024**3)
        }
    
    def get_disk_metrics(self):
        """Get disk usage metrics"""
        disk = psutil.disk_usage('/data')
        return {
            'total_gb': disk.total / (1024**3),
            'used_gb': disk.used / (1024**3),
            'free_gb': disk.free / (1024**3),
            'percent': disk.percent
        }
    
    def get_network_metrics(self):
        """Get network I/O metrics"""
        net = psutil.net_io_counters()
        return {
            'bytes_sent': net.bytes_sent,
            'bytes_recv': net.bytes_recv,
            'packets_sent': net.packets_sent,
            'packets_recv': net.packets_recv
        }
    
    def log_metrics(self):
        """Log current metrics"""
        metric = {
            'timestamp': datetime.now().isoformat(),
            'cpu': self.get_cpu_metrics(),
            'memory': self.get_memory_metrics(),
            'disk': self.get_disk_metrics(),
            'network': self.get_network_metrics()
        }
        
        self.metrics.append(metric)
        
        # Write to file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(metric) + '\n')
        
        return metric
    
    def monitor_loop(self, interval=60):
        """Continuous monitoring loop"""
        print(f"Starting resource monitoring (interval: {interval}s)...")
        
        while True:
            metric = self.log_metrics()
            
            # Print summary
            print(f"[{metric['timestamp']}] "
                  f"CPU: {sum(metric['cpu']['percent'])/len(metric['cpu']['percent']):.1f}%, "
                  f"RAM: {metric['memory']['percent']:.1f}%, "
                  f"Disk: {metric['disk']['percent']:.1f}%")
            
            time.sleep(interval)

# Run monitoring
if __name__ == "__main__":
    monitor = ResourceMonitor()
    monitor.monitor_loop()
```

### 5.2 Training Optimization Checklist

```bash
#!/bin/bash
# optimize_training.sh

echo "=== ORDL AI Training Optimization ==="

# 1. CPU Optimization
echo "Setting CPU governor to performance..."
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance | sudo tee $cpu
done

# 2. Memory Optimization
echo "Configuring swappiness..."
sudo sysctl vm.swappiness=10

# 3. Disk Optimization
echo "Optimizing disk I/O scheduler..."
echo 'noop' | sudo tee /sys/block/sda/queue/scheduler

# 4. Network Optimization (if using NFS)
echo "Optimizing network buffers..."
sudo sysctl -w net.core.rmem_max=134217728
sudo sysctl -w net.core.wmem_max=134217728

# 5. Enable huge pages for better memory performance
echo "Configuring huge pages..."
sudo sysctl vm.nr_hugepages=128

# 6. Set process priority for training
echo "Setting process priorities..."
sudo nice -n -10 $$

echo "=== Optimization Complete ==="
echo "Run 'python train_security_model.py' to start training"
```

### 5.3 Automated Backup Script

```bash
#!/bin/bash
# backup_training.sh

BACKUP_DIR="/data/slow/backups"
CHECKPOINT_DIR="/data/fast/security-model-v1"
S3_BUCKET="s3://ordl-ai-backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create local backup
echo "Creating local backup..."
tar -czf "$BACKUP_DIR/checkpoints_$DATE.tar.gz" -C "$CHECKPOINT_DIR" .

# Sync to S3
echo "Syncing to S3..."
aws s3 sync "$CHECKPOINT_DIR" "$S3_BUCKET/checkpoints/$DATE/"

# Cleanup old local backups (keep last 7)
echo "Cleaning up old backups..."
ls -t $BACKUP_DIR/checkpoints_*.tar.gz | tail -n +8 | xargs -r rm

echo "Backup complete: $DATE"
```

---

## APPENDIX A: TROUBLESHOOTING

### A.1 Out of Memory Errors

```python
# Reduce batch size
TRAINING_CONFIG["batch_size"] = 1
TRAINING_CONFIG["gradient_accumulation_steps"] = 16

# Enable gradient checkpointing
training_args.gradient_checkpointing = True

# Use 4-bit quantization
from transformers import BitsAndBytesConfig

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)
```

### A.2 Slow Training on CPU

```bash
# Check Intel MKL is enabled
python -c "import torch; print(torch.backends.mkldnn.is_available())"

# Set thread affinity
export KMP_AFFINITY=granularity=fine,compact,1,0
export OMP_NUM_THREADS=24
export MKL_NUM_THREADS=24

# Use DeepSpeed for CPU optimization
deepspeed --num_gpus=0 train_security_model.py --deepspeed ds_config.json
```

### A.3 AWS Training Job Failures

```python
# Check CloudWatch logs
import boto3

logs = boto3.client('logs')

response = logs.get_log_events(
    logGroupName='/aws/sagemaker/TrainingJobs',
    logStreamName='your-job-name',
    limit=100
)

for event in response['events']:
    print(event['message'])
```

---

## APPENDIX B: USEFUL COMMANDS

```bash
# Monitor training in tmux
tmux attach -t ordl-training

# View logs in real-time
tail -f /data/fast/security-model-v1/logs/training.log

# Check GPU/CPU usage
htop
watch -n 1 nvidia-smi  # If GPU available

# Sync data to/from AWS
aws s3 sync /data/slow/processed_security_dataset s3://your-bucket/data/
aws s3 sync s3://your-bucket/checkpoints /data/fast/checkpoints

# Compress dataset for transfer
tar -czf security_data.tar.gz /data/slow/processed_security_dataset

# Estimate training time
# Based on: 1B tokens, 7B model, 24 CPU cores
# Roughly 1-2 weeks for 3 epochs
```

---

**END OF IMPLEMENTATION GUIDE**

For support, refer to the ORDL AI Strategic Roadmap or consult the AGENTS.md framework documentation.
