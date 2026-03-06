"""
ORDL Command Post - Training API
Flask-compatible API interface for the training pipeline.
Integrates with the main ORDL backend.
"""

import os
import json
import uuid
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict

# Try to import Flask dependencies
try:
    from flask import Blueprint, request, jsonify, Response, stream_with_context
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# Training pipeline imports
try:
    from .trainer import ModelTrainer, TrainingProgress, ProgressTracker, get_hardware_info, create_training_job
    from .config import TrainingConfig, DatasetFormat, load_config, save_config, LoRAConfig
    from .model_manager import ModelRegistry, ModelQuantizer, ModelDeployer
    from .dataset_loader import DatasetLoader
    TRAINING_AVAILABLE = True
except ImportError as e:
    TRAINING_AVAILABLE = False
    print(f"Training pipeline not available: {e}")


# In-memory storage for active training jobs
_active_jobs: Dict[str, Dict] = {}
_job_callbacks: Dict[str, ProgressTracker] = {}


def create_training_blueprint() -> Optional[Any]:
    """
    Create Flask Blueprint for training API.
    
    Returns:
        Flask Blueprint or None if Flask not available
    """
    if not FLASK_AVAILABLE:
        return None
    
    bp = Blueprint('training', __name__, url_prefix='/api/training')
    
    @bp.route('/hardware', methods=['GET'])
    def get_hardware():
        """Get hardware information"""
        if not TRAINING_AVAILABLE:
            return jsonify({'error': 'Training pipeline not available'}), 503
        
        try:
            info = get_hardware_info()
            return jsonify({
                'success': True,
                'hardware': info,
                'training_supported': info['cuda_available'],
                'recommended_config': 'qlora' if info['cuda_available'] and info.get('gpu_memory_gb', [0])[0] >= 16 else 'qlora-small' if info['cuda_available'] else 'cpu'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/jobs', methods=['GET'])
    def list_jobs():
        """List all training jobs"""
        jobs = []
        for job_id, job_data in _active_jobs.items():
            jobs.append({
                'id': job_id,
                'name': job_data.get('name', 'Unknown'),
                'status': job_data.get('status', 'unknown'),
                'progress': job_data.get('progress', 0),
                'model': job_data.get('model'),
                'dataset': job_data.get('dataset'),
                'started_at': job_data.get('started_at'),
                'completed_at': job_data.get('completed_at')
            })
        
        return jsonify({
            'jobs': jobs,
            'count': len(jobs),
            'running': sum(1 for j in jobs if j['status'] == 'running'),
            'completed': sum(1 for j in jobs if j['status'] == 'completed')
        })
    
    @bp.route('/jobs', methods=['POST'])
    def create_job():
        """Create and start a new training job"""
        if not TRAINING_AVAILABLE:
            return jsonify({'error': 'Training pipeline not available'}), 503
        
        data = request.get_json()
        
        # Generate job ID
        job_id = f"train-{uuid.uuid4().hex[:12]}"
        
        # Create configuration
        try:
            config = TrainingConfig(
                job_id=job_id,
                name=data.get('name', f'training-{job_id}'),
                base_model=data.get('base_model', 'unsloth/Llama-3.2-1B-Instruct'),
                dataset_source=data.get('dataset_source', 'huggingface'),
                dataset_path=data.get('dataset', 'yahma/alpaca-cleaned'),
                dataset_format=DatasetFormat(data.get('dataset_format', 'alpaca').lower()),
                output_dir=os.path.expanduser(f"~/.ordl/models/{job_id}"),
                num_epochs=data.get('epochs', 3),
                learning_rate=data.get('learning_rate', 2e-4),
                batch_size=data.get('batch_size', 2),
                max_seq_length=data.get('max_seq_length', 2048),
                gradient_accumulation_steps=data.get('gradient_accumulation_steps', 4),
                warmup_steps=data.get('warmup_steps', 10),
                save_steps=data.get('save_steps', 50),
                logging_steps=data.get('logging_steps', 1),
                lora__r=data.get('lora_r', 16),
                lora__alpha=data.get('lora_alpha', 16),
                load_in_4bit=data.get('load_in_4bit', True),
            )
            
            # Override LoRA config if provided
            if 'lora' in data:
                from .config import LoRAConfig
                config.lora = LoRAConfig(**data['lora'])
            
        except Exception as e:
            return jsonify({'error': f'Invalid configuration: {str(e)}'}), 400
        
        # Initialize job tracking
        _active_jobs[job_id] = {
            'id': job_id,
            'name': config.name,
            'status': 'initializing',
            'progress': 0,
            'model': config.base_model,
            'dataset': config.dataset_path,
            'started_at': datetime.utcnow().isoformat(),
            'config': data
        }
        
        # Start training in background thread
        def run_training():
            try:
                trainer = ModelTrainer(config)
                
                # Setup progress tracking
                progress_tracker = ProgressTracker(trainer.progress)
                trainer.add_callback(progress_tracker)
                _job_callbacks[job_id] = progress_tracker
                
                # Update status
                _active_jobs[job_id]['status'] = 'running'
                
                # Run training
                result = trainer.train()
                
                # Update final status
                _active_jobs[job_id]['status'] = result.status
                _active_jobs[job_id]['progress'] = 100 if result.status == 'completed' else 0
                _active_jobs[job_id]['completed_at'] = datetime.utcnow().isoformat()
                _active_jobs[job_id]['final_loss'] = result.loss
                _active_jobs[job_id]['checkpoint_path'] = result.checkpoint_path
                
                if result.error_message:
                    _active_jobs[job_id]['error'] = result.error_message
                
            except Exception as e:
                _active_jobs[job_id]['status'] = 'failed'
                _active_jobs[job_id]['error'] = str(e)
                _active_jobs[job_id]['completed_at'] = datetime.utcnow().isoformat()
        
        thread = threading.Thread(target=run_training, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'job': _active_jobs[job_id]
        }), 201
    
    @bp.route('/jobs/<job_id>', methods=['GET'])
    def get_job(job_id: str):
        """Get training job details"""
        if job_id not in _active_jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = _active_jobs[job_id].copy()
        
        # Add real-time progress if available
        if job_id in _job_callbacks:
            tracker = _job_callbacks[job_id]
            progress = tracker.progress
            job['current_step'] = progress.current_step
            job['total_steps'] = progress.total_steps
            job['current_epoch'] = progress.current_epoch
            job['loss'] = progress.loss
            job['learning_rate'] = progress.learning_rate
            job['estimated_time_remaining'] = progress.estimated_time_remaining
            job['step_losses'] = progress.step_losses[-20:]  # Last 20 steps
            
            if progress.gpu_memory_mb:
                job['gpu_memory_mb'] = progress.gpu_memory_mb
        
        return jsonify(job)
    
    @bp.route('/jobs/<job_id>/stream', methods=['GET'])
    def stream_job_progress(job_id: str):
        """Stream job progress via Server-Sent Events"""
        if job_id not in _active_jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        def generate():
            import time
            last_step = -1
            
            while True:
                if job_id not in _active_jobs:
                    yield f"data: {json.dumps({'error': 'Job deleted'})}\n\n"
                    break
                
                job = _active_jobs[job_id]
                
                # Get current progress
                current_step = 0
                if job_id in _job_callbacks:
                    current_step = _job_callbacks[job_id].progress.current_step
                
                # Send update if progress changed
                if current_step != last_step:
                    last_step = current_step
                    
                    data = {
                        'status': job['status'],
                        'progress': job.get('progress', 0),
                        'step': current_step,
                        'loss': job.get('loss', 0),
                        'epoch': job.get('current_epoch', 0)
                    }
                    
                    yield f"data: {json.dumps(data)}\n\n"
                
                # Check if job is complete
                if job['status'] in ['completed', 'failed', 'cancelled']:
                    yield f"data: {json.dumps({'status': job['status'], 'done': True})}\n\n"
                    break
                
                time.sleep(1)
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
    
    @bp.route('/jobs/<job_id>', methods=['DELETE'])
    def cancel_job(job_id: str):
        """Cancel a training job"""
        if job_id not in _active_jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = _active_jobs[job_id]
        
        if job['status'] == 'running' and job_id in _job_callbacks:
            # Signal trainer to stop
            # Note: This requires trainer to be accessible
            pass
        
        job['status'] = 'cancelled'
        job['completed_at'] = datetime.utcnow().isoformat()
        
        return jsonify({'success': True, 'job': job})
    
    @bp.route('/jobs/<job_id>/export', methods=['POST'])
    def export_model(job_id: str):
        """Export trained model to GGUF"""
        if job_id not in _active_jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = _active_jobs[job_id]
        
        if job['status'] != 'completed':
            return jsonify({'error': 'Job not completed'}), 400
        
        if not job.get('checkpoint_path'):
            return jsonify({'error': 'No checkpoint available'}), 400
        
        data = request.get_json()
        quantization = data.get('quantization', 'Q4_K_M')
        
        try:
            quantizer = ModelQuantizer()
            result = quantizer.quantize_to_gguf(
                job['checkpoint_path'],
                output_name=f"{job_id}-{quantization}",
                quant_type=quantization
            )
            
            if result.success:
                return jsonify({
                    'success': True,
                    'output_path': result.output_path,
                    'quantization': quantization,
                    'original_size_mb': round(result.original_size_mb, 2),
                    'quantized_size_mb': round(result.quantized_size_mb, 2),
                    'compression_ratio': round(result.compression_ratio, 2)
                })
            else:
                return jsonify({'error': result.error}), 500
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/models', methods=['GET'])
    def list_models():
        """List registered models"""
        try:
            registry = ModelRegistry()
            models = registry.list_models()
            return jsonify({
                'models': models,
                'count': len(models)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/models/<model_id>', methods=['GET'])
    def get_model(model_id: str):
        """Get model details"""
        try:
            registry = ModelRegistry()
            model = registry.get_model(model_id)
            
            if not model:
                return jsonify({'error': 'Model not found'}), 404
            
            return jsonify(model)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/models/<model_id>/deploy', methods=['POST'])
    def deploy_model(model_id: str):
        """Deploy model to inference endpoint"""
        data = request.get_json()
        port = data.get('port', 8000)
        
        try:
            deployer = ModelDeployer()
            result = deployer.deploy_local(model_id, port=port)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/datasets/validate', methods=['POST'])
    def validate_dataset():
        """Validate dataset format and content"""
        data = request.get_json()
        dataset_path = data.get('path')
        dataset_format = data.get('format', 'alpaca')
        
        if not dataset_path:
            return jsonify({'error': 'Dataset path required'}), 400
        
        try:
            loader = DatasetLoader()
            
            # Try to load
            if dataset_path.startswith('http'):
                dataset = loader.load_from_url(dataset_path)
            else:
                dataset = loader.load_from_file(dataset_path)
            
            info = loader.get_dataset_info(dataset)
            
            # Try format conversion
            sample_text = None
            if dataset_format != 'raw':
                try:
                    converted = loader.convert_format(dataset, dataset_format, 'text')
                    if hasattr(converted, '__getitem__'):
                        sample = converted[0] if hasattr(converted, '__len__') else next(iter(converted))
                        sample_text = sample.get('text', str(sample))[:200]
                except Exception as e:
                    return jsonify({
                        'valid': False,
                        'error': f'Format conversion failed: {str(e)}',
                        'info': asdict(info) if hasattr(info, '__dataclass_fields__') else vars(info)
                    }), 400
            
            return jsonify({
                'valid': True,
                'info': {
                    'name': info.name,
                    'format': info.format,
                    'num_samples': info.num_samples,
                    'columns': info.columns
                },
                'sample_text': sample_text
            })
            
        except Exception as e:
            return jsonify({
                'valid': False,
                'error': str(e)
            }), 400
    
    @bp.route('/configs/presets', methods=['GET'])
    def get_config_presets():
        """Get configuration presets"""
        presets = {
            'qlora': {
                'name': 'QLoRA (GPU)',
                'description': 'Optimized for GPUs with limited VRAM',
                'config': {
                    'load_in_4bit': True,
                    'batch_size': 1,
                    'gradient_accumulation_steps': 8,
                    'lora_r': 64,
                    'lora_alpha': 128,
                    'max_seq_length': 4096,
                    'learning_rate': 2e-4
                }
            },
            'lora': {
                'name': 'LoRA (GPU)',
                'description': 'Standard LoRA for GPUs with 16GB+ VRAM',
                'config': {
                    'load_in_4bit': False,
                    'batch_size': 4,
                    'gradient_accumulation_steps': 2,
                    'lora_r': 16,
                    'lora_alpha': 16,
                    'max_seq_length': 2048,
                    'learning_rate': 2e-4
                }
            },
            'cpu': {
                'name': 'CPU Training',
                'description': 'Optimized for CPU-only training (slow)',
                'config': {
                    'load_in_4bit': False,
                    'batch_size': 1,
                    'gradient_accumulation_steps': 1,
                    'lora_r': 8,
                    'lora_alpha': 16,
                    'max_seq_length': 512,
                    'learning_rate': 5e-5,
                    'num_epochs': 1
                }
            }
        }
        
        return jsonify({'presets': presets})
    
    return bp


def register_with_app(app: Any):
    """
    Register training API with Flask app.
    
    Args:
        app: Flask application instance
    """
    bp = create_training_blueprint()
    if bp:
        app.register_blueprint(bp)
        print("Training API registered at /api/training")
    else:
        print("Warning: Flask not available, training API not registered")


# Example standalone usage
if __name__ == "__main__":
    print("Training API module - Import this in your Flask app")
    print("Usage: from services.training.api import register_with_app")
