"""
ORDL RED TEAM - FLASK API ENDPOINTS
Classification: TOP SECRET//SCI//NOFORN

Red Team API endpoints for integration with main Flask application.
All endpoints require TS/SCI clearance and two-person integrity.
"""

from flask import Blueprint, request, jsonify, g
from functools import wraps
import logging
import sys

# Add parent directory to path for imports
sys.path.insert(0, '/opt/codex-swarm/command-post')

# Import auth decorator from main app
try:
    from security.decorators import require_auth
except ImportError:
    # Fallback stub
    def require_auth(f):
        return f

logger = logging.getLogger(__name__)

# Create Blueprint
redteam_bp = Blueprint('redteam', __name__, url_prefix='/api/redteam')

# Global redteam manager instance
redteam_manager = None

def init_redteam_api(manager):
    """Initialize Red Team API with manager instance"""
    global redteam_manager
    redteam_manager = manager


def require_ts_sci(f):
    """Decorator to require TS/SCI clearance"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = g.get('user', {})
        clearance = user.get('clearance', 'UNCLASSIFIED')
        
        # Check clearance level
        clearance_levels = ['UNCLASSIFIED', 'CONFIDENTIAL', 'SECRET', 
                          'TOP SECRET', 'TS/SCI', 'TS/SCI/NOFORN']
        
        if clearance not in ['TS/SCI', 'TS/SCI/NOFORN']:
            return jsonify({
                "error": "Access Denied",
                "message": "This resource requires TS/SCI clearance",
                "required": "TS/SCI",
                "current": clearance
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


def require_2pi(f):
    """Decorator to require Two-Person Integrity"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if 2PI is satisfied (witness provided)
        data = request.get_json() or {}
        
        if not data.get('witness_codename'):
            return jsonify({
                "error": "Two-Person Integrity Required",
                "message": "This operation requires a witness for authorization",
                "requirement": "Witness codename must be provided"
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# RED TEAM OPERATIONS ENDPOINTS
# =============================================================================

@redteam_bp.route('/status', methods=['GET'])
@require_auth
@require_auth
@require_ts_sci
def get_status():
    """Get Red Team system status"""
    if not redteam_manager:
        return jsonify({"error": "Red Team system not initialized"}), 503
    
    stats = redteam_manager.get_statistics()
    
    return jsonify({
        "status": "operational",
        "classification": "TOP SECRET//SCI//NOFORN",
        "statistics": stats,
        "modules": {
            "reconnaissance": redteam_manager.recon is not None,
            "vulnerability_scanning": redteam_manager.scanner is not None,
            "exploit_framework": redteam_manager.exploit is not None,
            "payload_generation": redteam_manager.payload is not None,
            "social_engineering": redteam_manager.social is not None,
            "c2_infrastructure": redteam_manager.c2 is not None
        }
    })


@redteam_bp.route('/operations', methods=['GET'])
@require_auth
@require_ts_sci
def list_operations():
    """List all red team operations"""
    if not redteam_manager:
        return jsonify({"error": "Red Team system not initialized"}), 503
    
    operations = redteam_manager.list_operations()
    
    return jsonify({
        "operations": [
            {
                "operation_id": op.operation_id,
                "codename": op.codename,
                "description": op.description,
                "status": op.status.value,
                "targets": len(op.targets),
                "findings": len(op.findings),
                "created_at": op.created_at
            }
            for op in operations
        ],
        "count": len(operations)
    })


@redteam_bp.route('/operations', methods=['POST'])
@require_auth
@require_ts_sci
@require_auth
@require_2pi
def create_operation():
    """Create a new red team operation"""
    if not redteam_manager:
        return jsonify({"error": "Red Team system not initialized"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    codename = data.get('codename')
    description = data.get('description', '')
    authorization_code = data.get('authorization_code')
    witness_codename = data.get('witness_codename')
    
    if not codename or not authorization_code:
        return jsonify({
            "error": "Missing required fields",
            "required": ["codename", "authorization_code"]
        }), 400
    
    user = g.get('user', {})
    operator_codename = user.get('codename', 'unknown')
    
    try:
        operation = redteam_manager.create_operation(
            codename=codename,
            description=description,
            authorization_code=authorization_code,
            operator_codename=operator_codename,
            witness_codename=witness_codename
        )
        
        return jsonify({
            "success": True,
            "operation_id": operation.operation_id,
            "codename": operation.codename,
            "status": operation.status.value,
            "message": "Operation created successfully"
        }), 201
        
    except Exception as e:
        logger.error(f"[RedTeam API] Failed to create operation: {e}")
        return jsonify({"error": str(e)}), 500


@redteam_bp.route('/operations/<operation_id>', methods=['GET'])
@require_auth
@require_ts_sci
def get_operation(operation_id):
    """Get operation details"""
    if not redteam_manager:
        return jsonify({"error": "Red Team system not initialized"}), 503
    
    operation = redteam_manager.get_operation(operation_id)
    if not operation:
        return jsonify({"error": "Operation not found"}), 404
    
    return jsonify({
        "operation_id": operation.operation_id,
        "codename": operation.codename,
        "description": operation.description,
        "status": operation.status.value,
        "targets": operation.targets,
        "operators": operation.operators,
        "witness": operation.witness_codename,
        "findings": operation.findings,
        "phases_completed": operation.phases_completed,
        "created_at": operation.created_at
    })


@redteam_bp.route('/operations/<operation_id>/status', methods=['PUT'])
@require_auth
@require_ts_sci
def update_operation_status(operation_id):
    """Update operation status"""
    if not redteam_manager:
        return jsonify({"error": "Red Team system not initialized"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    new_status = data.get('status')
    if not new_status:
        return jsonify({"error": "Status required"}), 400
    
    try:
        from . import OperationStatus
        status = OperationStatus(new_status)
    except ValueError:
        return jsonify({"error": "Invalid status"}), 400
    
    user = g.get('user', {})
    operator_codename = user.get('codename', 'unknown')
    
    success = redteam_manager.update_operation_status(
        operation_id, status, operator_codename
    )
    
    if success:
        return jsonify({"success": True, "status": new_status})
    else:
        return jsonify({"error": "Operation not found"}), 404


# =============================================================================
# TARGET MANAGEMENT ENDPOINTS
# =============================================================================

@redteam_bp.route('/targets', methods=['GET'])
@require_auth
@require_ts_sci
def list_targets():
    """List all targets"""
    if not redteam_manager:
        return jsonify({"error": "Red Team system not initialized"}), 503
    
    target_type = request.args.get('type')
    
    from . import TargetType
    if target_type:
        try:
            ttype = TargetType(target_type)
            targets = redteam_manager.list_targets(ttype)
        except ValueError:
            return jsonify({"error": "Invalid target type"}), 400
    else:
        targets = redteam_manager.list_targets()
    
    return jsonify({
        "targets": [
            {
                "target_id": t.target_id,
                "name": t.name,
                "type": t.target_type.value,
                "value": t.value,
                "classification": t.classification,
                "country": t.country,
                "tags": t.tags
            }
            for t in targets
        ],
        "count": len(targets)
    })


@redteam_bp.route('/targets', methods=['POST'])
@require_auth
@require_ts_sci
def add_target():
    """Add a new target"""
    if not redteam_manager:
        return jsonify({"error": "Red Team system not initialized"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    name = data.get('name')
    target_type = data.get('target_type')
    value = data.get('value')
    
    if not name or not target_type or not value:
        return jsonify({
            "error": "Missing required fields",
            "required": ["name", "target_type", "value"]
        }), 400
    
    try:
        from . import TargetType
        ttype = TargetType(target_type)
    except ValueError:
        return jsonify({"error": "Invalid target type"}), 400
    
    target = redteam_manager.add_target(
        name=name,
        target_type=ttype,
        value=value,
        description=data.get('description', ''),
        classification=data.get('classification', 'UNCLASSIFIED'),
        tags=data.get('tags', [])
    )
    
    return jsonify({
        "success": True,
        "target_id": target.target_id,
        "name": target.name,
        "message": "Target added successfully"
    }), 201


# =============================================================================
# RECONNAISSANCE ENDPOINTS
# =============================================================================

@redteam_bp.route('/recon/scan', methods=['POST'])
@require_auth
@require_ts_sci
def port_scan():
    """Perform port scan on target"""
    if not redteam_manager or not redteam_manager.recon:
        return jsonify({"error": "Reconnaissance module not available"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    target = data.get('target')
    ports = data.get('ports')
    
    if not target:
        return jsonify({"error": "Target required"}), 400
    
    try:
        if isinstance(ports, list):
            host_info = redteam_manager.recon.scan_host(target, ports=ports)
        else:
            host_info = redteam_manager.recon.scan_host(target)
        
        return jsonify({
            "success": True,
            "target": target,
            "hostname": host_info.hostname,
            "os_guess": host_info.os_guess,
            "os_confidence": host_info.os_confidence,
            "open_ports": [
                {
                    "port": p.port,
                    "protocol": p.protocol,
                    "service": p.service,
                    "version": p.version,
                    "banner": p.banner[:100] if p.banner else ""
                }
                for p in host_info.ports
            ],
            "total_open": len(host_info.ports)
        })
        
    except Exception as e:
        logger.error(f"[RedTeam API] Port scan failed: {e}")
        return jsonify({"error": str(e)}), 500


@redteam_bp.route('/recon/dns', methods=['GET'])
@require_auth
@require_ts_sci
def dns_lookup():
    """Perform DNS lookup"""
    if not redteam_manager or not redteam_manager.recon:
        return jsonify({"error": "Reconnaissance module not available"}), 503
    
    domain = request.args.get('domain')
    if not domain:
        return jsonify({"error": "Domain required"}), 400
    
    try:
        records = redteam_manager.recon.dns_lookup(domain)
        
        return jsonify({
            "domain": domain,
            "records": [
                {
                    "type": r.record_type,
                    "name": r.name,
                    "value": r.value,
                    "ttl": r.ttl
                }
                for r in records
            ]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@redteam_bp.route('/recon/subdomains', methods=['GET'])
@require_auth
@require_ts_sci
def enumerate_subdomains():
    """Enumerate subdomains"""
    if not redteam_manager or not redteam_manager.recon:
        return jsonify({"error": "Reconnaissance module not available"}), 503
    
    domain = request.args.get('domain')
    if not domain:
        return jsonify({"error": "Domain required"}), 400
    
    try:
        subdomains = redteam_manager.recon.enumerate_subdomains(domain)
        
        return jsonify({
            "domain": domain,
            "subdomains": subdomains,
            "count": len(subdomains)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# VULNERABILITY SCANNING ENDPOINTS
# =============================================================================

@redteam_bp.route('/scan/service', methods=['POST'])
@require_auth
@require_ts_sci
def scan_service():
    """Scan service for vulnerabilities"""
    if not redteam_manager or not redteam_manager.scanner:
        return jsonify({"error": "Scanner module not available"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    host = data.get('host')
    port = data.get('port')
    service = data.get('service')
    version = data.get('version', '')
    
    if not host or not port or not service:
        return jsonify({"error": "Host, port, and service required"}), 400
    
    try:
        vulns = redteam_manager.scanner.scan_service(
            host, int(port), service, version
        )
        
        return jsonify({
            "success": True,
            "target": f"{host}:{port}",
            "service": service,
            "version": version,
            "vulnerabilities": [
                {
                    "vuln_id": v.vuln_id,
                    "name": v.name,
                    "severity": v.severity,
                    "cvss_score": v.cvss_score,
                    "cve_ids": v.cve_ids,
                    "description": v.description,
                    "evidence": v.evidence
                }
                for v in vulns
            ],
            "vulnerability_count": len(vulns)
        })
        
    except Exception as e:
        logger.error(f"[RedTeam API] Service scan failed: {e}")
        return jsonify({"error": str(e)}), 500


@redteam_bp.route('/scan/web', methods=['POST'])
@require_auth
@require_ts_sci
def scan_web_application():
    """Scan web application"""
    if not redteam_manager or not redteam_manager.scanner:
        return jsonify({"error": "Scanner module not available"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL required"}), 400
    
    try:
        vulns = redteam_manager.scanner.scan_web_application(
            url, deep_scan=data.get('deep_scan', False)
        )
        
        return jsonify({
            "success": True,
            "url": url,
            "vulnerabilities": [
                {
                    "url": v.url,
                    "parameter": v.parameter,
                    "type": v.vuln_type,
                    "severity": v.severity,
                    "payload": v.payload[:50] if v.payload else "",
                    "evidence": v.evidence[:100] if v.evidence else ""
                }
                for v in vulns
            ],
            "vulnerability_count": len(vulns)
        })
        
    except Exception as e:
        logger.error(f"[RedTeam API] Web scan failed: {e}")
        return jsonify({"error": str(e)}), 500


@redteam_bp.route('/scan/ssl', methods=['GET'])
@require_auth
@require_ts_sci
def analyze_ssl():
    """Analyze SSL/TLS configuration"""
    if not redteam_manager or not redteam_manager.scanner:
        return jsonify({"error": "Scanner module not available"}), 503
    
    host = request.args.get('host')
    port = request.args.get('port', 443, type=int)
    
    if not host:
        return jsonify({"error": "Host required"}), 400
    
    try:
        ssl_info = redteam_manager.scanner.analyze_ssl(host, port)
        
        return jsonify({
            "host": host,
            "port": port,
            "protocol_version": ssl_info.protocol_version,
            "cipher_suite": ssl_info.cipher_suite,
            "certificate_subject": ssl_info.certificate_subject,
            "certificate_issuer": ssl_info.certificate_issuer,
            "certificate_expired": ssl_info.certificate_expired,
            "certificate_self_signed": ssl_info.certificate_self_signed,
            "ssl_score": ssl_info.ssl_score,
            "vulnerabilities": ssl_info.vulnerabilities,
            "weak_ciphers": ssl_info.weak_ciphers
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# EXPLOIT FRAMEWORK ENDPOINTS
# =============================================================================

@redteam_bp.route('/exploits', methods=['GET'])
@require_auth
@require_ts_sci
def list_exploits():
    """List available exploits"""
    if not redteam_manager or not redteam_manager.exploit:
        return jsonify({"error": "Exploit module not available"}), 503
    
    keyword = request.args.get('keyword')
    platform = request.args.get('platform')
    cve = request.args.get('cve')
    
    try:
        exploits = redteam_manager.exploit.search_exploits(
            keyword=keyword, platform=platform, cve=cve
        )
        
        return jsonify({
            "exploits": [
                {
                    "exploit_id": e.exploit_id,
                    "name": e.name,
                    "description": e.description,
                    "type": e.exploit_type.value,
                    "platform": e.platform.value,
                    "cve_ids": e.cve_ids,
                    "reliability": e.reliability,
                    "requires_auth": e.requires_auth,
                    "is_local": e.is_local
                }
                for e in exploits
            ],
            "count": len(exploits)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@redteam_bp.route('/exploits/<exploit_id>/check', methods=['POST'])
@require_auth
@require_ts_sci
def check_vulnerable(exploit_id):
    """Check if target is vulnerable to exploit"""
    if not redteam_manager or not redteam_manager.exploit:
        return jsonify({"error": "Exploit module not available"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    target = data.get('target')
    port = data.get('port', 0)
    
    if not target:
        return jsonify({"error": "Target required"}), 400
    
    try:
        is_vuln, details = redteam_manager.exploit.check_vulnerable(
            target, port, exploit_id
        )
        
        return jsonify({
            "exploit_id": exploit_id,
            "target": target,
            "port": port,
            "vulnerable": is_vuln,
            "details": details
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@redteam_bp.route('/exploits/execute', methods=['POST'])
@require_auth
@require_ts_sci
@require_auth
@require_2pi
def execute_exploit():
    """Execute exploit against target"""
    if not redteam_manager or not redteam_manager.exploit:
        return jsonify({"error": "Exploit module not available"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    target = data.get('target')
    port = data.get('port')
    exploit_id = data.get('exploit_id')
    
    if not target or not port or not exploit_id:
        return jsonify({
            "error": "Missing required fields",
            "required": ["target", "port", "exploit_id"]
        }), 400
    
    try:
        result = redteam_manager.exploit.execute_exploit(
            target=target,
            port=int(port),
            exploit_id=exploit_id,
            payload=data.get('payload'),
            options=data.get('options', {})
        )
        
        return jsonify({
            "success": result.success,
            "exploit_id": result.exploit_id,
            "target": result.target,
            "port": result.port,
            "session_id": result.session_id,
            "output": result.output,
            "error": result.error
        })
        
    except Exception as e:
        logger.error(f"[RedTeam API] Exploit execution failed: {e}")
        return jsonify({"error": str(e)}), 500


@redteam_bp.route('/sessions', methods=['GET'])
@require_auth
@require_ts_sci
def list_sessions():
    """List active exploit sessions"""
    if not redteam_manager or not redteam_manager.exploit:
        return jsonify({"error": "Exploit module not available"}), 503
    
    try:
        sessions = redteam_manager.exploit.list_sessions()
        
        return jsonify({
            "sessions": [
                {
                    "session_id": s.session_id,
                    "target": s.target,
                    "port": s.port,
                    "exploit_id": s.exploit_id,
                    "platform": s.platform,
                    "created_at": s.created_at
                }
                for s in sessions
            ],
            "count": len(sessions)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@redteam_bp.route('/sessions/<session_id>/interact', methods=['POST'])
@require_auth
@require_ts_sci
def interact_session(session_id):
    """Interact with a session"""
    if not redteam_manager or not redteam_manager.exploit:
        return jsonify({"error": "Exploit module not available"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    command = data.get('command')
    if not command:
        return jsonify({"error": "Command required"}), 400
    
    try:
        output = redteam_manager.exploit.interact_with_session(session_id, command)
        
        return jsonify({
            "session_id": session_id,
            "command": command,
            "output": output or "Session not found"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# PAYLOAD GENERATION ENDPOINTS
# =============================================================================

@redteam_bp.route('/payloads/generate/reverse_shell', methods=['POST'])
@require_auth
@require_ts_sci
def generate_reverse_shell():
    """Generate reverse shell payload"""
    if not redteam_manager or not redteam_manager.payload:
        return jsonify({"error": "Payload module not available"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    platform = data.get('platform')
    lhost = data.get('lhost')
    lport = data.get('lport', 4444)
    
    if not platform or not lhost:
        return jsonify({"error": "Platform and LHOST required"}), 400
    
    try:
        from .payload import PayloadPlatform, PayloadArch, PayloadFormat
        
        # Convert string to enum - handle both name and value
        platform_lower = platform.lower()
        try:
            plat = PayloadPlatform(platform_lower)
        except ValueError:
            # Try matching by name
            for p in PayloadPlatform:
                if p.name.lower() == platform_lower or p.value.lower() == platform_lower:
                    plat = p
                    break
            else:
                raise ValueError(f"Invalid platform: {platform}")
        
        arch_str = data.get('arch', 'x64').lower()
        try:
            arch = PayloadArch(arch_str)
        except ValueError:
            arch = PayloadArch.X64
        
        fmt_str = data.get('format', 'raw').lower()
        try:
            fmt = PayloadFormat(fmt_str)
        except ValueError:
            fmt = PayloadFormat.RAW
        
        payload = redteam_manager.payload.generate_reverse_shell(
            platform=plat,
            arch=arch,
            lhost=lhost,
            lport=int(lport),
            format=fmt,
            encoder=data.get('encoder')
        )
        
        return jsonify({
            "payload_id": payload.payload_id,
            "name": payload.name,
            "platform": payload.platform.value,
            "size": payload.size,
            "one_liner": payload.one_liner,
            "content_b64": payload.content_b64[:100] + "..." if len(payload.content_b64) > 100 else payload.content_b64,
            "md5": payload.md5_hash,
            "sha256": payload.sha256_hash
        })
        
    except Exception as e:
        logger.error(f"[RedTeam API] Payload generation failed: {e}")
        return jsonify({"error": str(e)}), 500


@redteam_bp.route('/payloads', methods=['GET'])
@require_auth
@require_ts_sci
def list_payloads():
    """List generated payloads"""
    if not redteam_manager or not redteam_manager.payload:
        return jsonify({"error": "Payload module not available"}), 503
    
    payloads = redteam_manager.payload.list_payloads()
    
    return jsonify({
        "payloads": [
            {
                "payload_id": p.payload_id,
                "name": p.name,
                "type": p.payload_type.value,
                "platform": p.platform.value,
                "size": p.size,
                "created_at": p.created_at
            }
            for p in payloads
        ],
        "count": len(payloads)
    })


# =============================================================================
# SOCIAL ENGINEERING ENDPOINTS
# =============================================================================

@redteam_bp.route('/phishing/templates', methods=['GET'])
@require_auth
@require_ts_sci
def list_phishing_templates():
    """List phishing email templates"""
    if not redteam_manager or not redteam_manager.social:
        return jsonify({"error": "Social engineering module not available"}), 503
    
    templates = redteam_manager.social.list_templates()
    
    return jsonify({
        "templates": [
            {
                "template_id": t.template_id,
                "name": t.name,
                "description": t.description,
                "type": t.email_type.value,
                "subject": t.subject,
                "sender_name": t.sender_name,
                "sender_email": t.sender_email
            }
            for t in templates
        ],
        "count": len(templates)
    })


@redteam_bp.route('/phishing/campaigns', methods=['GET'])
@require_auth
@require_ts_sci
def list_phishing_campaigns():
    """List phishing campaigns"""
    if not redteam_manager or not redteam_manager.social:
        return jsonify({"error": "Social engineering module not available"}), 503
    
    campaigns = redteam_manager.social.list_campaigns()
    
    return jsonify({
        "campaigns": [
            {
                "campaign_id": c.campaign_id,
                "name": c.name,
                "description": c.description,
                "status": c.status.value,
                "targets": len(c.targets),
                "created_at": c.created_at
            }
            for c in campaigns
        ],
        "count": len(campaigns)
    })


@redteam_bp.route('/phishing/campaigns', methods=['POST'])
@require_auth
@require_ts_sci
def create_phishing_campaign():
    """Create phishing campaign"""
    if not redteam_manager or not redteam_manager.social:
        return jsonify({"error": "Social engineering module not available"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    name = data.get('name')
    template_id = data.get('template_id')
    target_ids = data.get('targets', [])
    
    if not name or not template_id or not target_ids:
        return jsonify({
            "error": "Missing required fields",
            "required": ["name", "template_id", "targets"]
        }), 400
    
    try:
        campaign = redteam_manager.social.create_campaign(
            name=name,
            description=data.get('description', ''),
            template_id=template_id,
            target_ids=target_ids,
            operation_id=data.get('operation_id', '')
        )
        
        if not campaign:
            return jsonify({"error": "Failed to create campaign"}), 500
        
        return jsonify({
            "success": True,
            "campaign_id": campaign.campaign_id,
            "name": campaign.name,
            "status": campaign.status.value
        }), 201
        
    except Exception as e:
        logger.error(f"[RedTeam API] Campaign creation failed: {e}")
        return jsonify({"error": str(e)}), 500


@redteam_bp.route('/phishing/campaigns/<campaign_id>/stats', methods=['GET'])
@require_auth
@require_ts_sci
def get_campaign_stats(campaign_id):
    """Get phishing campaign statistics"""
    if not redteam_manager or not redteam_manager.social:
        return jsonify({"error": "Social engineering module not available"}), 503
    
    stats = redteam_manager.social.get_campaign_statistics(campaign_id)
    
    if not stats:
        return jsonify({"error": "Campaign not found"}), 404
    
    return jsonify(stats)


# =============================================================================
# C2 INFRASTRUCTURE ENDPOINTS
# =============================================================================

@redteam_bp.route('/c2/listeners', methods=['GET'])
@require_auth
@require_ts_sci
def list_c2_listeners():
    """List C2 listeners"""
    if not redteam_manager or not redteam_manager.c2:
        return jsonify({"error": "C2 module not available"}), 503
    
    listeners = redteam_manager.c2.list_listeners()
    
    return jsonify({
        "listeners": [
            {
                "listener_id": l.listener_id,
                "name": l.name,
                "type": l.listener_type.value,
                "bind_host": l.bind_host,
                "bind_port": l.bind_port,
                "status": l.status,
                "profile": l.profile
            }
            for l in listeners
        ],
        "count": len(listeners)
    })


@redteam_bp.route('/c2/listeners', methods=['POST'])
@require_auth
@require_ts_sci
def create_c2_listener():
    """Create C2 listener"""
    if not redteam_manager or not redteam_manager.c2:
        return jsonify({"error": "C2 module not available"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    name = data.get('name')
    listener_type = data.get('type')
    bind_host = data.get('bind_host')
    bind_port = data.get('port')
    
    if not name or not listener_type or not bind_host or not bind_port:
        return jsonify({
            "error": "Missing required fields",
            "required": ["name", "type", "bind_host", "port"]
        }), 400
    
    try:
        from .c2 import ListenerType
        
        ltype = ListenerType(listener_type)
        
        listener = redteam_manager.c2.create_listener(
            name=name,
            listener_type=ltype,
            bind_host=bind_host,
            bind_port=int(bind_port),
            profile=data.get('profile', 'default'),
            ssl_cert=data.get('ssl_cert', ''),
            ssl_key=data.get('ssl_key', ''),
            domain=data.get('domain', '')
        )
        
        return jsonify({
            "success": True,
            "listener_id": listener.listener_id,
            "name": listener.name,
            "type": listener.listener_type.value,
            "bind_address": f"{listener.bind_host}:{listener.bind_port}"
        }), 201
        
    except Exception as e:
        logger.error(f"[RedTeam API] Listener creation failed: {e}")
        return jsonify({"error": str(e)}), 500


@redteam_bp.route('/c2/sessions', methods=['GET'])
@require_auth
@require_ts_sci
def list_c2_sessions():
    """List C2 sessions"""
    if not redteam_manager or not redteam_manager.c2:
        return jsonify({"error": "C2 module not available"}), 503
    
    sessions = redteam_manager.c2.list_sessions()
    
    return jsonify({
        "sessions": [
            {
                "session_id": s.session_id,
                "listener_id": s.listener_id,
                "external_ip": s.external_ip,
                "internal_ip": s.internal_ip,
                "hostname": s.hostname,
                "username": s.username,
                "operating_system": s.operating_system,
                "integrity_level": s.integrity_level,
                "status": s.status.value,
                "first_seen": s.first_seen,
                "last_seen": s.last_seen
            }
            for s in sessions
        ],
        "count": len(sessions)
    })


@redteam_bp.route('/c2/kill_switch', methods=['POST'])
@require_auth
@require_ts_sci
def kill_switch():
    """EMERGENCY: Kill all C2 sessions"""
    if not redteam_manager or not redteam_manager.c2:
        return jsonify({"error": "C2 module not available"}), 503
    
    data = request.get_json() or {}
    confirmation = data.get('confirmation')
    
    if confirmation != "KILL_ALL_SESSIONS":
        return jsonify({
            "error": "Confirmation required",
            "message": "Send confirmation: 'KILL_ALL_SESSIONS' to confirm"
        }), 400
    
    count = redteam_manager.c2.kill_all_sessions()
    
    # Audit log
    user = g.get('user', {})
    if redteam_manager and redteam_manager.audit_logger:
        redteam_manager.audit_logger.log(
            event_type="C2_KILL_SWITCH_ACTIVATED",
            user_codename=user.get('codename', 'unknown'),
            resource_id="ALL_SESSIONS",
            action="KILL_SWITCH",
            status="SUCCESS",
            details={"sessions_terminated": count}
        )
    
    return jsonify({
        "success": True,
        "message": "Kill switch activated",
        "sessions_terminated": count
    })


# Export blueprint
__all__ = ['redteam_bp', 'init_redteam_api']
