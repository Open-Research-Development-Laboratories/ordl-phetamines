#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - BLUE TEAM REST API
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Classification Level: TS/SCI/NOFORN

Blue Team REST API Endpoints for SOC Operations
================================================================================
"""

import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from functools import wraps

from . import (
    get_blueteam_manager, IOCType, AlertSeverity, IncidentStatus,
    LogSource, DetectionRule
)

logger = logging.getLogger('blueteam.api')

# Blueprint
blueteam_bp = Blueprint('blueteam', __name__, url_prefix='/api/blueteam')

# Global manager instance
bt_manager = None

def init_blueteam_api(manager):
    """Initialize API with manager instance"""
    global bt_manager
    bt_manager = manager
    logger.info("[BLUE TEAM] API initialized")

# ==================== AUTHENTICATION DECORATORS ====================

def require_auth(f):
    """Require valid authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Authentication handled by main app
        return f(*args, **kwargs)
    return decorated

def require_ts_sci(f):
    """Require TS/SCI clearance"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Clearance check handled by main app
        return f(*args, **kwargs)
    return decorated

# ==================== DASHBOARD & STATS ====================

@blueteam_bp.route('/dashboard', methods=['GET'])
@require_auth
def get_dashboard():
    """Get SOC dashboard data"""
    try:
        data = bt_manager.get_dashboard_data()
        return jsonify({
            "status": "success",
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/stats', methods=['GET'])
@require_auth
def get_stats():
    """Get operational statistics"""
    try:
        stats = bt_manager.get_stats()
        return jsonify({
            "status": "success",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/stats/reset', methods=['POST'])
@require_auth
def reset_stats():
    """Reset operational statistics"""
    try:
        bt_manager.reset_stats()
        return jsonify({
            "status": "success",
            "message": "Statistics reset",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Stats reset error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== IOC MANAGEMENT ====================

@blueteam_bp.route('/iocs', methods=['GET'])
@require_auth
def get_iocs():
    """Get IOCs with optional filtering"""
    try:
        ioc_type = request.args.get('type')
        threat_actor = request.args.get('actor')
        
        ioc_type_enum = None
        if ioc_type:
            try:
                ioc_type_enum = IOCType(ioc_type.lower())
            except ValueError:
                return jsonify({"status": "error", "message": f"Invalid IOC type: {ioc_type}"}), 400
        
        iocs = bt_manager.get_iocs(ioc_type=ioc_type_enum, threat_actor=threat_actor)
        
        return jsonify({
            "status": "success",
            "count": len(iocs),
            "iocs": [ioc.to_dict() for ioc in iocs],
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Get IOCs error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/iocs', methods=['POST'])
@require_auth
def add_ioc():
    """Add new Indicator of Compromise"""
    try:
        data = request.get_json()
        
        required = ['type', 'value', 'source', 'confidence', 'severity', 'description']
        for field in required:
            if field not in data:
                return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400
        
        # Validate IOC type
        try:
            ioc_type = IOCType(data['type'].lower())
        except ValueError:
            valid_types = [t.value for t in IOCType]
            return jsonify({"status": "error", "message": f"Invalid type. Valid: {valid_types}"}), 400
        
        # Validate severity
        try:
            severity = AlertSeverity(data['severity'].upper())
        except ValueError:
            valid_sev = [s.value for s in AlertSeverity]
            return jsonify({"status": "error", "message": f"Invalid severity. Valid: {valid_sev}"}), 400
        
        ioc = bt_manager.add_ioc(
            ioc_type=ioc_type,
            value=data['value'],
            source=data['source'],
            confidence=int(data['confidence']),
            severity=severity,
            description=data['description'],
            threat_actor=data.get('threat_actor'),
            campaign=data.get('campaign')
        )
        
        return jsonify({
            "status": "success",
            "ioc": ioc.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }), 201
    except Exception as e:
        logger.error(f"Add IOC error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/iocs/<ioc_id>', methods=['GET'])
@require_auth
def get_ioc(ioc_id):
    """Get specific IOC"""
    try:
        ioc = bt_manager._iocs.get(ioc_id)
        if not ioc:
            return jsonify({"status": "error", "message": "IOC not found"}), 404
        
        return jsonify({
            "status": "success",
            "ioc": ioc.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Get IOC error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/iocs/<ioc_id>', methods=['DELETE'])
@require_auth
def delete_ioc(ioc_id):
    """Delete an IOC"""
    try:
        if bt_manager.delete_ioc(ioc_id):
            return jsonify({
                "status": "success",
                "message": f"IOC {ioc_id} deleted",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({"status": "error", "message": "IOC not found"}), 404
    except Exception as e:
        logger.error(f"Delete IOC error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/iocs/check', methods=['POST'])
@require_auth
def check_ioc():
    """Check if value matches any IOC"""
    try:
        data = request.get_json()
        value = data.get('value')
        
        if not value:
            return jsonify({"status": "error", "message": "Missing 'value' field"}), 400
        
        match = bt_manager.check_ioc(value)
        
        return jsonify({
            "status": "success",
            "matched": match is not None,
            "ioc": match.to_dict() if match else None,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Check IOC error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/iocs/export/<format>', methods=['GET'])
@require_auth
def export_iocs(format):
    """Export IOCs in various formats"""
    try:
        if format not in ['json', 'csv', 'stix']:
            return jsonify({"status": "error", "message": "Format must be json, csv, or stix"}), 400
        
        content = bt_manager.export_iocs(format)
        
        content_type = 'application/json'
        if format == 'csv':
            content_type = 'text/csv'
        
        from flask import Response
        return Response(
            content,
            mimetype=content_type,
            headers={
                'Content-Disposition': f'attachment; filename=ordl_iocs.{format}'
            }
        )
    except Exception as e:
        logger.error(f"Export IOCs error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== LOG INGESTION ====================

@blueteam_bp.route('/logs/ingest', methods=['POST'])
@require_auth
def ingest_log():
    """Ingest log entry for analysis"""
    try:
        data = request.get_json()
        
        required = ['source_type', 'source_host', 'message']
        for field in required:
            if field not in data:
                return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400
        
        # Validate source type
        try:
            source_type = LogSource(data['source_type'].lower())
        except ValueError:
            valid_types = [t.value for t in LogSource]
            return jsonify({"status": "error", "message": f"Invalid type. Valid: {valid_types}"}), 400
        
        # Parse timestamp if provided
        timestamp = None
        if 'timestamp' in data:
            try:
                timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            except:
                pass
        
        entry = bt_manager.ingest_log(
            source_type=source_type,
            source_host=data['source_host'],
            raw_message=data['message'],
            timestamp=timestamp,
            parsed_fields=data.get('parsed_fields', {})
        )
        
        return jsonify({
            "status": "success",
            "entry_id": entry.entry_id,
            "alert_triggered": entry.alert_triggered,
            "timestamp": datetime.utcnow().isoformat()
        }), 201
    except Exception as e:
        logger.error(f"Ingest log error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/logs/batch', methods=['POST'])
@require_auth
def ingest_logs_batch():
    """Ingest multiple log entries"""
    try:
        data = request.get_json()
        logs = data.get('logs', [])
        
        if not isinstance(logs, list):
            return jsonify({"status": "error", "message": "'logs' must be an array"}), 400
        
        results = []
        for log_data in logs:
            try:
                source_type = LogSource(log_data.get('source_type', 'custom').lower())
                entry = bt_manager.ingest_log(
                    source_type=source_type,
                    source_host=log_data.get('source_host', 'unknown'),
                    raw_message=log_data.get('message', ''),
                    parsed_fields=log_data.get('parsed_fields', {})
                )
                results.append({
                    "entry_id": entry.entry_id,
                    "status": "ingested",
                    "alert_triggered": entry.alert_triggered
                })
            except Exception as e:
                results.append({"status": "error", "message": str(e)})
        
        return jsonify({
            "status": "success",
            "processed": len(results),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Batch ingest error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== ALERT MANAGEMENT ====================

@blueteam_bp.route('/alerts', methods=['GET'])
@require_auth
def get_alerts():
    """Get alerts with optional filtering"""
    try:
        severity = request.args.get('severity')
        status = request.args.get('status')
        since_hours = request.args.get('since_hours', type=int)
        
        severity_enum = None
        if severity:
            try:
                severity_enum = AlertSeverity(severity.upper())
            except ValueError:
                valid_sev = [s.value for s in AlertSeverity]
                return jsonify({"status": "error", "message": f"Invalid severity. Valid: {valid_sev}"}), 400
        
        since = None
        if since_hours:
            since = datetime.utcnow() - __import__('datetime').timedelta(hours=since_hours)
        
        alerts = bt_manager.get_alerts(
            severity=severity_enum,
            status=status,
            since=since
        )
        
        return jsonify({
            "status": "success",
            "count": len(alerts),
            "alerts": [alert.to_dict() for alert in alerts],
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/alerts/<alert_id>', methods=['GET'])
@require_auth
def get_alert(alert_id):
    """Get specific alert"""
    try:
        alert = bt_manager.get_alert(alert_id)
        if not alert:
            return jsonify({"status": "error", "message": "Alert not found"}), 404
        
        return jsonify({
            "status": "success",
            "alert": alert.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Get alert error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/alerts/<alert_id>/assign', methods=['POST'])
@require_auth
def assign_alert(alert_id):
    """Assign alert to analyst"""
    try:
        data = request.get_json()
        analyst = data.get('analyst')
        
        if not analyst:
            return jsonify({"status": "error", "message": "Missing 'analyst' field"}), 400
        
        if bt_manager.assign_alert(alert_id, analyst):
            return jsonify({
                "status": "success",
                "message": f"Alert assigned to {analyst}",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({"status": "error", "message": "Alert not found"}), 404
    except Exception as e:
        logger.error(f"Assign alert error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/alerts/<alert_id>/close', methods=['POST'])
@require_auth
def close_alert(alert_id):
    """Close an alert"""
    try:
        data = request.get_json()
        resolution = data.get('resolution', 'Closed by analyst')
        
        if bt_manager.close_alert(alert_id, resolution):
            return jsonify({
                "status": "success",
                "message": "Alert closed",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({"status": "error", "message": "Alert not found"}), 404
    except Exception as e:
        logger.error(f"Close alert error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== INCIDENT MANAGEMENT ====================

@blueteam_bp.route('/incidents', methods=['GET'])
@require_auth
def get_incidents():
    """Get incidents with optional filtering"""
    try:
        status = request.args.get('status')
        severity = request.args.get('severity')
        
        status_enum = None
        if status:
            try:
                status_enum = IncidentStatus(status.upper())
            except ValueError:
                valid_status = [s.value for s in IncidentStatus]
                return jsonify({"status": "error", "message": f"Invalid status. Valid: {valid_status}"}), 400
        
        severity_enum = None
        if severity:
            try:
                severity_enum = AlertSeverity(severity.upper())
            except ValueError:
                valid_sev = [s.value for s in AlertSeverity]
                return jsonify({"status": "error", "message": f"Invalid severity. Valid: {valid_sev}"}), 400
        
        incidents = bt_manager.get_incidents(status=status_enum, severity=severity_enum)
        
        return jsonify({
            "status": "success",
            "count": len(incidents),
            "incidents": [inc.to_dict() for inc in incidents],
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Get incidents error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/incidents', methods=['POST'])
@require_auth
def create_incident():
    """Create new incident case"""
    try:
        data = request.get_json()
        
        required = ['title', 'description', 'severity']
        for field in required:
            if field not in data:
                return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400
        
        # Validate severity
        try:
            severity = AlertSeverity(data['severity'].upper())
        except ValueError:
            valid_sev = [s.value for s in AlertSeverity]
            return jsonify({"status": "error", "message": f"Invalid severity. Valid: {valid_sev}"}), 400
        
        incident = bt_manager.create_incident(
            title=data['title'],
            description=data['description'],
            severity=severity,
            related_alerts=data.get('related_alerts', []),
            lead_analyst=data.get('lead_analyst')
        )
        
        return jsonify({
            "status": "success",
            "incident": incident.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }), 201
    except Exception as e:
        logger.error(f"Create incident error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/incidents/<incident_id>', methods=['GET'])
@require_auth
def get_incident(incident_id):
    """Get specific incident"""
    try:
        incident = bt_manager.get_incident(incident_id)
        if not incident:
            return jsonify({"status": "error", "message": "Incident not found"}), 404
        
        return jsonify({
            "status": "success",
            "incident": incident.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Get incident error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/incidents/<incident_id>/status', methods=['PUT'])
@require_auth
def update_incident_status(incident_id):
    """Update incident status"""
    try:
        data = request.get_json()
        status = data.get('status')
        actor = data.get('actor', request.remote_user or 'system')
        
        if not status:
            return jsonify({"status": "error", "message": "Missing 'status' field"}), 400
        
        try:
            status_enum = IncidentStatus(status.upper())
        except ValueError:
            valid_status = [s.value for s in IncidentStatus]
            return jsonify({"status": "error", "message": f"Invalid status. Valid: {valid_status}"}), 400
        
        if bt_manager.update_incident_status(incident_id, status_enum, actor):
            return jsonify({
                "status": "success",
                "message": f"Incident status updated to {status}",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({"status": "error", "message": "Incident not found"}), 404
    except Exception as e:
        logger.error(f"Update incident status error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/incidents/<incident_id>/containment', methods=['POST'])
@require_auth
def add_containment_action(incident_id):
    """Add containment action to incident"""
    try:
        data = request.get_json()
        action = data.get('action')
        description = data.get('description', '')
        actor = data.get('actor', request.remote_user or 'system')
        
        if not action:
            return jsonify({"status": "error", "message": "Missing 'action' field"}), 400
        
        if bt_manager.add_containment_action(incident_id, action, description, actor):
            return jsonify({
                "status": "success",
                "message": "Containment action added",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({"status": "error", "message": "Incident not found"}), 404
    except Exception as e:
        logger.error(f"Add containment action error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== DETECTION RULES ====================

@blueteam_bp.route('/rules', methods=['GET'])
@require_auth
def get_rules():
    """Get all detection rules"""
    try:
        rules = bt_manager.get_detection_rules()
        
        return jsonify({
            "status": "success",
            "count": len(rules),
            "rules": [rule.to_dict() for rule in rules],
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Get rules error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/rules', methods=['POST'])
@require_auth
def add_rule():
    """Add custom detection rule"""
    try:
        data = request.get_json()
        
        required = ['rule_id', 'name', 'description', 'severity', 'source_types', 'conditions']
        for field in required:
            if field not in data:
                return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400
        
        # Validate severity
        try:
            severity = AlertSeverity(data['severity'].upper())
        except ValueError:
            valid_sev = [s.value for s in AlertSeverity]
            return jsonify({"status": "error", "message": f"Invalid severity. Valid: {valid_sev}"}), 400
        
        # Validate source types
        source_types = []
        for st in data['source_types']:
            try:
                source_types.append(LogSource(st.lower()))
            except ValueError:
                valid_types = [t.value for t in LogSource]
                return jsonify({"status": "error", "message": f"Invalid source_type: {st}. Valid: {valid_types}"}), 400
        
        rule = DetectionRule(
            rule_id=data['rule_id'],
            name=data['name'],
            description=data['description'],
            severity=severity,
            source_types=source_types,
            conditions=data['conditions'],
            mitre_techniques=data.get('mitre_techniques', []),
            enabled=data.get('enabled', True)
        )
        
        bt_manager.add_detection_rule(rule)
        
        return jsonify({
            "status": "success",
            "rule": rule.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }), 201
    except Exception as e:
        logger.error(f"Add rule error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@blueteam_bp.route('/rules/<rule_id>/toggle', methods=['POST'])
@require_auth
def toggle_rule(rule_id):
    """Enable/disable detection rule"""
    try:
        data = request.get_json()
        enabled = data.get('enabled')
        
        if enabled is None:
            return jsonify({"status": "error", "message": "Missing 'enabled' field"}), 400
        
        if bt_manager.toggle_rule(rule_id, enabled):
            return jsonify({
                "status": "success",
                "message": f"Rule {rule_id} {'enabled' if enabled else 'disabled'}",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({"status": "error", "message": "Rule not found"}), 404
    except Exception as e:
        logger.error(f"Toggle rule error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== PURPLE TEAM INTEGRATION ====================

@blueteam_bp.route('/purple/correlate', methods=['POST'])
@require_auth
def correlate_with_redteam():
    """Correlate Blue Team findings with Red Team operations"""
    try:
        data = request.get_json()
        redteam_op_id = data.get('operation_id')
        
        # Get recent alerts and correlate with Red Team activity
        recent_alerts = bt_manager.get_alerts(since=datetime.utcnow() - __import__('datetime').timedelta(hours=24))
        
        # Find Red Team IOCs in alerts
        correlations = []
        for alert in recent_alerts:
            for ioc in alert.ioc_matches:
                if ioc.get('source') == 'redteam':
                    correlations.append({
                        "alert_id": alert.alert_id,
                        "ioc": ioc,
                        "mitre_techniques": alert.mitre_techniques
                    })
        
        return jsonify({
            "status": "success",
            "operation_id": redteam_op_id,
            "correlations_found": len(correlations),
            "correlations": correlations,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Purple team correlate error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== HEALTH CHECK ====================

@blueteam_bp.route('/health', methods=['GET'])
def health_check():
    """Blue Team module health check"""
    if bt_manager:
        stats = bt_manager.get_stats()
        return jsonify({
            "status": "healthy",
            "module": "blueteam",
            "version": "6.0.0",
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Blue Team manager not initialized"
        }), 503
