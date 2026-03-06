#!/usr/bin/env python3
"""
ORDL Flask Control Plane Application
"""

from flask import Flask, render_template, jsonify, request
import os

# Create Flask application
app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['JSON_SORT_KEYS'] = False


# Context Processors
@app.context_processor
def inject_globals():
    """Inject global variables into all templates"""
    return {
        'app_name': 'ORDL Control Platform',
        'version': '2.5.0',
        'current_user': 'JD',
        'current_user_name': 'John Doe',
        'current_user_role': 'Admin'
    }


# Dashboard Routes
@app.route('/')
def index():
    """Root redirect to dashboard"""
    return render_template('control/dashboard.html', active_nav='dashboard')


@app.route('/app/dashboard')
def dashboard():
    """Main dashboard view"""
    return render_template('control/dashboard.html', active_nav='dashboard')


# Topology Routes
@app.route('/app/topology')
def topology():
    """Network topology visualization"""
    return render_template('control/topology.html', active_nav='topology')


# Fleet Operations Routes
@app.route('/app/fleet/operations')
def fleet_operations():
    """Fleet operations management"""
    return render_template('control/fleet_operations.html', active_nav='fleet_operations')


# Deployment Routes
@app.route('/app/deployments')
def deployments():
    """Deployment management"""
    return render_template('control/deployments.html', active_nav='deployments')


# Command Center Routes
@app.route('/app/command-center')
def command_center():
    """Command center for batch operations"""
    return render_template('control/command_center.html', active_nav='command_center')


# Messages Rework Routes
@app.route('/app/messages/rework')
def messages_rework():
    """Message lifecycle board"""
    return render_template('control/messages_rework.html', active_nav='messages_rework')


# API Routes
@app.route('/api/health')
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '2.5.0',
        'timestamp': '2024-03-06T14:32:18Z'
    })


@app.route('/api/nodes')
def api_nodes():
    """Get all nodes"""
    nodes = [
        {'id': 'node-001', 'status': 'online', 'role': 'coordinator', 'region': 'us-east-1'},
        {'id': 'node-002', 'status': 'online', 'role': 'worker', 'region': 'us-east-1'},
        {'id': 'node-003', 'status': 'online', 'role': 'gateway', 'region': 'us-west-2'},
        {'id': 'node-004', 'status': 'cordoned', 'role': 'worker', 'region': 'eu-west-1'},
        {'id': 'node-005', 'status': 'offline', 'role': 'worker', 'region': 'ap-southeast-1'},
    ]
    return jsonify({'nodes': nodes, 'total': len(nodes)})


@app.route('/api/nodes/<node_id>/reconnect', methods=['POST'])
def api_node_reconnect(node_id):
    """Reconnect a node"""
    return jsonify({
        'success': True,
        'message': f'Node {node_id} reconnection initiated',
        'operation_id': f'op-{node_id}-001'
    })


@app.route('/api/nodes/<node_id>/cordon', methods=['POST'])
def api_node_cordon(node_id):
    """Cordon a node"""
    return jsonify({
        'success': True,
        'message': f'Node {node_id} cordoned',
        'operation_id': f'op-{node_id}-002'
    })


@app.route('/api/nodes/<node_id>/drain', methods=['POST'])
def api_node_drain(node_id):
    """Drain a node"""
    return jsonify({
        'success': True,
        'message': f'Node {node_id} draining initiated',
        'operation_id': f'op-{node_id}-003'
    })


@app.route('/api/deployments')
def api_deployments():
    """Get all deployments"""
    deployments = [
        {
            'id': 'dep-2k9x4n',
            'version': 'v2.5.0',
            'status': 'rolling',
            'environment': 'production',
            'progress': 65,
            'created_at': '2024-03-06T14:32:18Z'
        },
        {
            'id': 'dep-2k9x3m',
            'version': 'v2.4.1',
            'status': 'deployed',
            'environment': 'production',
            'progress': 100,
            'created_at': '2024-03-04T09:15:42Z'
        }
    ]
    return jsonify({'deployments': deployments, 'total': len(deployments)})


@app.route('/api/deployments/<deployment_id>/rollback', methods=['POST'])
def api_deployment_rollback(deployment_id):
    """Rollback a deployment"""
    data = request.get_json() or {}
    target_version = data.get('version', 'v2.4.0')
    
    return jsonify({
        'success': True,
        'message': f'Deployment {deployment_id} rollback to {target_version} initiated',
        'rollback_id': f'rb-{deployment_id}'
    })


@app.route('/api/command/dispatch', methods=['POST'])
def api_command_dispatch():
    """Dispatch a command to targets"""
    data = request.get_json() or {}
    command = data.get('command')
    targets = data.get('targets', [])
    options = data.get('options', {})
    
    return jsonify({
        'success': True,
        'command': command,
        'targets': targets,
        'dispatch_id': 'dsp-001',
        'status': 'queued',
        'estimated_duration': '30s'
    })


@app.route('/api/messages')
def api_messages():
    """Get all messages"""
    messages = [
        {
            'id': 'msg-001',
            'title': 'Restart node-042 in us-east-1',
            'status': 'draft',
            'priority': 'high',
            'author': 'sarah.chen',
            'created_at': '2024-03-06T14:32:18Z'
        },
        {
            'id': 'msg-004',
            'title': 'Emergency stop on prod cluster',
            'status': 'review',
            'priority': 'high',
            'author': 'james.wilson',
            'created_at': '2024-03-06T14:30:00Z'
        }
    ]
    return jsonify({'messages': messages, 'total': len(messages)})


@app.route('/api/messages/<message_id>/status', methods=['PUT'])
def api_message_update_status(message_id):
    """Update message status"""
    data = request.get_json() or {}
    new_status = data.get('status')
    
    return jsonify({
        'success': True,
        'message': f'Message {message_id} status updated to {new_status}',
        'message_id': message_id,
        'status': new_status
    })


@app.route('/api/topology')
def api_topology():
    """Get topology data"""
    nodes = [
        {'id': 'coord-0', 'role': 'coordinator', 'status': 'active', 'x': 400, 'y': 300},
        {'id': 'coord-1', 'role': 'coordinator', 'status': 'active', 'x': 600, 'y': 300},
        {'id': 'gw-0', 'role': 'gateway', 'status': 'active', 'x': 200, 'y': 150},
        {'id': 'gw-1', 'role': 'gateway', 'status': 'active', 'x': 600, 'y': 150},
        {'id': 'worker-0', 'role': 'worker', 'status': 'active', 'x': 100, 'y': 100},
        {'id': 'worker-1', 'role': 'worker', 'status': 'active', 'x': 300, 'y': 100},
    ]
    
    links = [
        {'source': 'coord-0', 'target': 'gw-0'},
        {'source': 'coord-0', 'target': 'gw-1'},
        {'source': 'coord-1', 'target': 'gw-0'},
        {'source': 'coord-1', 'target': 'gw-1'},
        {'source': 'gw-0', 'target': 'worker-0'},
        {'source': 'gw-1', 'target': 'worker-1'},
    ]
    
    return jsonify({'nodes': nodes, 'links': links})


# Error Handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource was not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500


if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
