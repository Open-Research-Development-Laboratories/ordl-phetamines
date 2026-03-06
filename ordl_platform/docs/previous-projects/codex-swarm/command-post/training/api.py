#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - TRAINING REST API
================================================================================
Classification: TOP SECRET//SCI//NOFORN

LLM Training REST API Endpoints
================================================================================
"""

import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from functools import wraps

from . import get_trainer

logger = logging.getLogger('training.api')

# Blueprint
training_bp = Blueprint('training', __name__, url_prefix='/api/training')

# Global trainer instance
trainer = None

def init_training_api(trainer_instance):
    """Initialize API with trainer instance"""
    global trainer
    trainer = trainer_instance
    logger.info("[TRAINING] API initialized")

# ==================== HARDWARE INFO ====================

@training_bp.route('/hardware', methods=['GET'])
def get_hardware():
    """Get hardware capabilities"""
    try:
        info = trainer.get_hardware_info()
        return jsonify({
            "status": "success",
            "hardware": info,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Hardware info error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== JOBS ====================

@training_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List all training jobs"""
    try:
        jobs = trainer.list_jobs()
        return jsonify({
            "status": "success",
            "count": len(jobs),
            "jobs": jobs,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"List jobs error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@training_bp.route('/jobs', methods=['POST'])
def create_job():
    """Create a new training job"""
    try:
        data = request.get_json()
        
        required = ['job_id', 'name', 'base_model', 'output_model', 
                   'dataset_source', 'dataset_path']
        for field in required:
            if field not in data:
                return jsonify({
                    "status": "error",
                    "message": f"Missing required field: {field}"
                }), 400
        
        job = trainer.create_job(data)
        
        return jsonify({
            "status": "success",
            "job": job.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }), 201
    except Exception as e:
        logger.error(f"Create job error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@training_bp.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get job details"""
    try:
        job = trainer.get_job(job_id)
        if not job:
            return jsonify({
                "status": "error",
                "message": "Job not found"
            }), 404
        
        return jsonify({
            "status": "success",
            "job": job,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Get job error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@training_bp.route('/jobs/<job_id>/start', methods=['POST'])
def start_job(job_id):
    """Start training job"""
    try:
        if trainer.start_training(job_id):
            return jsonify({
                "status": "success",
                "message": f"Job {job_id} started",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to start job"
            }), 400
    except Exception as e:
        logger.error(f"Start job error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@training_bp.route('/jobs/<job_id>/stop', methods=['POST'])
def stop_job(job_id):
    """Stop training job"""
    try:
        if trainer.stop_job(job_id):
            return jsonify({
                "status": "success",
                "message": f"Job {job_id} stop requested",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Job not found"
            }), 404
    except Exception as e:
        logger.error(f"Stop job error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@training_bp.route('/jobs/<job_id>/metrics', methods=['GET'])
def get_job_metrics(job_id):
    """Get job training metrics"""
    try:
        limit = request.args.get('limit', 1000, type=int)
        metrics = trainer.get_job_metrics(job_id, limit)
        
        return jsonify({
            "status": "success",
            "job_id": job_id,
            "count": len(metrics),
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Get metrics error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== MODELS & DATASETS ====================

@training_bp.route('/models', methods=['GET'])
def list_models():
    """List available base models"""
    try:
        models = trainer.list_available_models()
        return jsonify({
            "status": "success",
            "count": len(models),
            "models": models,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"List models error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@training_bp.route('/datasets', methods=['GET'])
def list_datasets():
    """List popular datasets"""
    try:
        datasets = trainer.list_popular_datasets()
        return jsonify({
            "status": "success",
            "count": len(datasets),
            "datasets": datasets,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"List datasets error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== HEALTH ====================

@training_bp.route('/health', methods=['GET'])
def health_check():
    """Training module health check"""
    try:
        if trainer:
            info = trainer.get_hardware_info()
            return jsonify({
                "status": "healthy",
                "module": "training",
                "backend": info.get('recommended_backend'),
                "cuda_available": info.get('cuda_available'),
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Trainer not initialized"
            }), 503
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
