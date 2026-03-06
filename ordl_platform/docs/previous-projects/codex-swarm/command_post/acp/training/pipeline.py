#!/usr/bin/env python3
"""
Flagship Model Training Pipeline
"""

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger('acp.training')


class FlagshipTrainingPipeline:
    """
    Complete training pipeline for ORDL Flagship Model
    
    Phases:
    1. Data Collection - Gather from skills, agents, conversations
    2. Local Training - Unsloth QLoRA on your hardware
    3. Cloud Training - AWS SageMaker with your credits
    4. Deployment - Ollama for free inference
    """
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.data_dir = Path(self.config.get('data_dir', '/opt/codex-swarm/data/training'))
        self.models_dir = Path(self.config.get('models_dir', '/opt/codex-swarm/models'))
        self.checkpoints_dir = Path(self.config.get('checkpoints_dir', '/opt/codex-swarm/checkpoints'))
        
        # Ensure directories exist
        for d in [self.data_dir, self.models_dir, self.checkpoints_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        self.current_run = None
        
        logger.info("[TRAINING] Pipeline initialized")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load training configuration"""
        default_config = {
            'data_dir': '/opt/codex-swarm/data/training',
            'models_dir': '/opt/codex-swarm/models',
            'checkpoints_dir': '/opt/codex-swarm/checkpoints',
            'base_model': 'meta-llama/Llama-2-7b-hf',
            'training': {
                'epochs': 3,
                'batch_size': 4,
                'learning_rate': 2e-4,
                'max_seq_length': 2048,
                'lora_r': 16,
                'lora_alpha': 32,
                'lora_dropout': 0.05
            },
            'aws': {
                'instance_type': 'ml.g5.xlarge',
                'max_run': 86400,
                'spot_training': True
            }
        }
        
        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                loaded = json.load(f)
                default_config.update(loaded)
        
        return default_config
    
    async def run_full_pipeline(self) -> Dict[str, Any]:
        """
        Execute complete training pipeline
        
        Returns:
            Pipeline execution results
        """
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_run = run_id
        
        logger.info(f"[TRAINING] Starting full pipeline: {run_id}")
        
        results = {
            'run_id': run_id,
            'status': 'running',
            'phases': {}
        }
        
        try:
            # Phase 1: Data Collection
            logger.info("[TRAINING] Phase 1: Data Collection")
            results['phases']['data_collection'] = await self._collect_training_data()
            
            # Phase 2: Local Training (Unsloth)
            logger.info("[TRAINING] Phase 2: Local Training")
            results['phases']['local_training'] = await self._train_local()
            
            # Phase 3: AWS Cloud Training
            logger.info("[TRAINING] Phase 3: AWS Training")
            results['phases']['aws_training'] = await self._train_aws()
            
            # Phase 4: Deployment
            logger.info("[TRAINING] Phase 4: Deployment")
            results['phases']['deployment'] = await self._deploy_model()
            
            results['status'] = 'completed'
            logger.info(f"[TRAINING] Pipeline completed: {run_id}")
            
        except Exception as e:
            results['status'] = 'failed'
            results['error'] = str(e)
            logger.error(f"[TRAINING] Pipeline failed: {e}")
        
        return results
    
    async def _collect_training_data(self) -> Dict:
        """
        Collect training data from all system components
        
        Sources:
        - Skill execution traces
        - Agent conversations
        - Blue team detections
        - Red team operations
        """
        from .data_collector import TrainingDataCollector
        
        collector = TrainingDataCollector(self.data_dir)
        
        data_sources = {
            'skill_traces': await collector.collect_skill_traces(),
            'agent_conversations': await collector.collect_conversations(),
            'detection_outcomes': await collector.collect_detections(),
            'tool_usage': await collector.collect_tool_usage(),
        }
        
        # Combine into training dataset
        dataset_path = await collector.create_training_dataset(data_sources)
        
        return {
            'status': 'completed',
            'dataset_path': str(dataset_path),
            'samples': sum(len(s) for s in data_sources.values()),
            'sources': {k: len(v) for k, v in data_sources.items()}
        }
    
    async def _train_local(self) -> Dict:
        """
        Local training with Unsloth (QLoRA)
        
        Uses your hardware for initial training
        """
        try:
            import unsloth
            from unsloth import FastLanguageModel
            from transformers import TrainingArguments
            from trl import SFTTrainer
            
            logger.info("[TRAINING] Loading base model with Unsloth...")
            
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.config['base_model'],
                max_seq_length=self.config['training']['max_seq_length'],
                dtype=None,
                load_in_4bit=True,
            )
            
            # Add LoRA adapters
            model = FastLanguageModel.get_peft_model(
                model,
                r=self.config['training']['lora_r'],
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                               "gate_proj", "up_proj", "down_proj"],
                lora_alpha=self.config['training']['lora_alpha'],
                lora_dropout=self.config['training']['lora_dropout'],
                bias="none",
                use_gradient_checkpointing=True,
            )
            
            # Training arguments
            training_args = TrainingArguments(
                output_dir=str(self.checkpoints_dir / self.current_run),
                num_train_epochs=self.config['training']['epochs'],
                per_device_train_batch_size=self.config['training']['batch_size'],
                learning_rate=self.config['training']['learning_rate'],
                logging_steps=10,
                save_steps=100,
                save_total_limit=3,
            )
            
            # Initialize trainer
            trainer = SFTTrainer(
                model=model,
                tokenizer=tokenizer,
                train_dataset=self._load_dataset(),
                dataset_text_field="text",
                max_seq_length=self.config['training']['max_seq_length'],
                args=training_args,
            )
            
            logger.info("[TRAINING] Starting local training...")
            trainer.train()
            
            # Save checkpoint
            checkpoint_path = self.checkpoints_dir / self.current_run / "final"
            trainer.save_model(str(checkpoint_path))
            
            return {
                'status': 'completed',
                'checkpoint': str(checkpoint_path),
                'epochs': self.config['training']['epochs'],
                'final_loss': trainer.state.log_history[-1].get('loss', 0)
            }
            
        except ImportError:
            logger.warning("[TRAINING] Unsloth not available, skipping local training")
            return {'status': 'skipped', 'reason': 'unsloth_not_installed'}
        
        except Exception as e:
            logger.error(f"[TRAINING] Local training failed: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    async def _train_aws(self) -> Dict:
        """
        AWS SageMaker training with your credits
        
        Distributed training on GPU instances
        """
        from .aws_integration import AWSTrainingIntegration
        
        aws = AWSTrainingIntegration(self.config.get('aws', {}))
        
        # Upload data to S3
        s3_data_path = await aws.upload_training_data(
            self.data_dir / 'training_dataset.jsonl'
        )
        
        # Launch training job
        job_name = f"ordl-flagship-{self.current_run}"
        
        training_job = await aws.launch_training_job(
            job_name=job_name,
            data_path=s3_data_path,
            hyperparameters=self.config['training'],
            instance_type=self.config['aws']['instance_type'],
            max_run=self.config['aws']['max_run'],
            use_spot=self.config['aws']['spot_training']
        )
        
        return {
            'status': 'submitted',
            'job_name': job_name,
            'instance': self.config['aws']['instance_type'],
            'estimated_cost': training_job.get('estimated_cost', 'unknown')
        }
    
    async def _deploy_model(self) -> Dict:
        """
        Deploy trained model to Ollama
        
        Free local inference
        """
        try:
            model_name = f"ordl-flagship-{self.current_run}"
            
            # Convert to GGUF
            gguf_path = await self._convert_to_gguf(
                self.checkpoints_dir / self.current_run / "final",
                self.models_dir / f"{model_name}.gguf"
            )
            
            # Create Ollama Modelfile
            modelfile_content = f"""FROM {gguf_path}
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
SYSTEM You are ORDL Flagship, an advanced AI security assistant specializing in penetration testing, blue team operations, and threat intelligence.
"""
            
            modelfile_path = self.models_dir / f"Modelfile.{model_name}"
            with open(modelfile_path, 'w') as f:
                f.write(modelfile_content)
            
            # Create Ollama model
            subprocess.run([
                'ollama', 'create', model_name,
                '-f', str(modelfile_path)
            ], check=True, capture_output=True)
            
            return {
                'status': 'deployed',
                'model_name': model_name,
                'gguf_path': str(gguf_path),
                'modelfile': str(modelfile_path)
            }
            
        except Exception as e:
            logger.error(f"[TRAINING] Deployment failed: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    async def _convert_to_gguf(self, checkpoint_path: Path, output_path: Path) -> Path:
        """Convert model checkpoint to GGUF format"""
        # Use llama.cpp for conversion
        convert_script = Path.home() / "llama.cpp/convert.py"
        
        if convert_script.exists():
            subprocess.run([
                'python3', str(convert_script),
                str(checkpoint_path),
                '--outfile', str(output_path),
                '--outtype', 'q4_K_M'
            ], check=True)
        else:
            logger.warning("[TRAINING] llama.cpp not found, using checkpoint directly")
            # Fallback: copy checkpoint
            import shutil
            shutil.copytree(checkpoint_path, output_path.parent / output_path.stem)
        
        return output_path
    
    def _load_dataset(self):
        """Load training dataset"""
        from datasets import load_dataset
        
        dataset_path = self.data_dir / 'training_dataset.jsonl'
        
        if dataset_path.exists():
            return load_dataset('json', data_files=str(dataset_path))['train']
        else:
            # Return dummy dataset for testing
            return load_dataset('yahma/alpaca-cleaned', split='train[:1000]')
    
    def get_status(self) -> Dict:
        """Get current training status"""
        return {
            'current_run': self.current_run,
            'data_dir': str(self.data_dir),
            'models_dir': str(self.models_dir),
            'config': self.config
        }
