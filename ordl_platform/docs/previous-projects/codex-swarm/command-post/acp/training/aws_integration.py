#!/usr/bin/env python3
"""
AWS Training Integration
Utilize AWS credits for cloud training
"""

import asyncio
import boto3
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger('acp.training.aws')


class AWSTrainingIntegration:
    """
    AWS SageMaker integration for distributed training
    
    Features:
    - Spot instance training (70% cost savings)
    - Multi-GPU distributed training
    - Automatic checkpointing
    - Cost tracking
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.s3_bucket = config.get('s3_bucket', 'ordl-training-data')
        self.role_arn = config.get('role_arn', '')
        self.region = config.get('region', 'us-east-1')
        
        try:
            self.sagemaker = boto3.client('sagemaker', region_name=self.region)
            self.s3 = boto3.client('s3', region_name=self.region)
        except Exception as e:
            logger.warning(f"[AWS] boto3 initialization failed: {e}")
            self.sagemaker = None
            self.s3 = None
    
    async def upload_training_data(self, local_path: Path) -> str:
        """
        Upload training data to S3
        
        Returns:
            S3 path for training job
        """
        if not self.s3:
            logger.error("[AWS] S3 client not available")
            return ""
        
        s3_key = f"training-data/{local_path.name}"
        
        try:
            self.s3.upload_file(
                str(local_path),
                self.s3_bucket,
                s3_key
            )
            
            s3_uri = f"s3://{self.s3_bucket}/{s3_key}"
            logger.info(f"[AWS] Uploaded to {s3_uri}")
            return s3_uri
            
        except Exception as e:
            logger.error(f"[AWS] Upload failed: {e}")
            return ""
    
    async def launch_training_job(
        self,
        job_name: str,
        data_path: str,
        hyperparameters: Dict,
        instance_type: str = "ml.g5.xlarge",
        max_run: int = 86400,
        use_spot: bool = True
    ) -> Dict[str, Any]:
        """
        Launch SageMaker training job
        
        Args:
            job_name: Unique job identifier
            data_path: S3 path to training data
            hyperparameters: Training hyperparameters
            instance_type: EC2 instance type
            max_run: Max runtime in seconds
            use_spot: Use spot instances for cost savings
            
        Returns:
            Job details and tracking info
        """
        if not self.sagemaker:
            logger.error("[AWS] SageMaker client not available")
            return {'status': 'failed', 'error': 'aws_not_configured'}
        
        try:
            # Training script
            training_script = self._create_training_script()
            
            # Build training job config
            training_job_config = {
                'TrainingJobName': job_name,
                'RoleArn': self.role_arn,
                'AlgorithmSpecification': {
                    'TrainingImage': '763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-training:2.0-transformers4.28-gpu-py310-cu118-ubuntu20.04',
                    'TrainingInputMode': 'File'
                },
                'InputDataConfig': [
                    {
                        'ChannelName': 'training',
                        'DataSource': {
                            'S3DataSource': {
                                'S3DataType': 'S3Prefix',
                                'S3Uri': data_path,
                                'S3DataDistributionType': 'FullyReplicated'
                            }
                        }
                    }
                ],
                'OutputDataConfig': {
                    'S3OutputPath': f's3://{self.s3_bucket}/output/'
                },
                'ResourceConfig': {
                    'InstanceType': instance_type,
                    'InstanceCount': 1,
                    'VolumeSizeInGB': 100
                },
                'HyperParameters': {k: str(v) for k, v in hyperparameters.items()},
                'StoppingCondition': {
                    'MaxRuntimeInSeconds': max_run
                },
                'EnableManagedSpotTraining': use_spot,
                'CheckpointConfig': {
                    'S3Uri': f's3://{self.s3_bucket}/checkpoints/',
                    'LocalPath': '/opt/ml/checkpoints'
                }
            }
            
            # Add spot config if enabled
            if use_spot:
                training_job_config['StoppingCondition']['MaxWaitTimeInSeconds'] = max_run * 2
            
            # Launch job
            response = self.sagemaker.create_training_job(**training_job_config)
            
            job_arn = response['TrainingJobArn']
            
            # Estimate cost
            instance_costs = {
                'ml.g5.xlarge': 1.006,
                'ml.g5.2xlarge': 2.012,
                'ml.g5.4xlarge': 4.024,
                'ml.g5.8xlarge': 8.048,
                'ml.g5.16xlarge': 16.096
            }
            
            hourly_rate = instance_costs.get(instance_type, 1.0)
            spot_discount = 0.3 if use_spot else 1.0
            estimated_hours = min(max_run / 3600, 24)  # Cap at 24h estimate
            estimated_cost = hourly_rate * estimated_hours * spot_discount
            
            logger.info(f"[AWS] Training job launched: {job_arn}")
            
            return {
                'status': 'submitted',
                'job_arn': job_arn,
                'job_name': job_name,
                'instance': instance_type,
                'use_spot': use_spot,
                'estimated_cost': f"${estimated_cost:.2f}",
                's3_output': f's3://{self.s3_bucket}/output/'
            }
            
        except Exception as e:
            logger.error(f"[AWS] Failed to launch training job: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    async def get_job_status(self, job_name: str) -> Dict:
        """Get training job status"""
        if not self.sagemaker:
            return {'status': 'unknown'}
        
        try:
            response = self.sagemaker.describe_training_job(
                TrainingJobName=job_name
            )
            
            return {
                'status': response['TrainingJobStatus'],
                'secondary_status': response.get('SecondaryStatus', ''),
                'start_time': str(response.get('TrainingStartTime', '')),
                'end_time': str(response.get('TrainingEndTime', '')),
                'instance': response['ResourceConfig']['InstanceType'],
                'billable_time': response.get('BillableTimeInSeconds', 0)
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    async def download_model(self, job_name: str, local_path: Path) -> bool:
        """Download trained model from S3"""
        if not self.s3:
            return False
        
        try:
            s3_prefix = f"output/{job_name}/output/model.tar.gz"
            
            self.s3.download_file(
                self.s3_bucket,
                s3_prefix,
                str(local_path / 'model.tar.gz')
            )
            
            logger.info(f"[AWS] Model downloaded to {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"[AWS] Download failed: {e}")
            return False
    
    def _create_training_script(self) -> str:
        """Create training script for SageMaker"""
        script = '''
import os
import json
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import load_dataset

# Load hyperparameters
with open('/opt/ml/input/config/hyperparameters.json') as f:
    hyperparameters = json.load(f)

# Load model
model_name = hyperparameters.get('base_model', 'meta-llama/Llama-2-7b-hf')
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map='auto'
)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# LoRA config
peft_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=int(hyperparameters.get('lora_r', 16)),
    lora_alpha=int(hyperparameters.get('lora_alpha', 32)),
    lora_dropout=float(hyperparameters.get('lora_dropout', 0.05)),
    target_modules=["q_proj", "v_proj"]
)
model = get_peft_model(model, peft_config)

# Load dataset
dataset = load_dataset('json', data_files='/opt/ml/input/data/training/training.jsonl')

# Training args
args = TrainingArguments(
    output_dir='/opt/ml/model',
    num_train_epochs=int(hyperparameters.get('epochs', 3)),
    per_device_train_batch_size=int(hyperparameters.get('batch_size', 4)),
    learning_rate=float(hyperparameters.get('learning_rate', 2e-4)),
    logging_steps=10,
    save_strategy='epoch'
)

# Train
trainer = Trainer(model=model, args=args, train_dataset=dataset['train'])
trainer.train()

# Save
trainer.save_model()
'''
        return script
