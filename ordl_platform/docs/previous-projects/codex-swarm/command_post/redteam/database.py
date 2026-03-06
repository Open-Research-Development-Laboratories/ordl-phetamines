"""
ORDL RED TEAM - DATABASE SCHEMA
Classification: TOP SECRET//SCI//NOFORN

Database schema for Red Team operations:
- Operations table
- Targets table
- Campaigns table
- Sessions table
- Tasks table
- Audit trail
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def init_redteam_database(db_path: str = "/opt/codex-swarm/command-post/data/redteam.db"):
    """Initialize Red Team database with all tables"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Operations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operations (
            operation_id TEXT PRIMARY KEY,
            codename TEXT UNIQUE NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            authorization_code TEXT NOT NULL,
            two_person_integrity BOOLEAN DEFAULT 1,
            witness_codename TEXT,
            operator_codename TEXT NOT NULL,
            classification TEXT DEFAULT 'TOP SECRET//SCI//NOFORN',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            phases_completed TEXT,  -- JSON array
            findings TEXT  -- JSON array
        )
    ''')
    
    # Targets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS targets (
            target_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            target_type TEXT NOT NULL,
            value TEXT NOT NULL,  -- IP, domain, email, etc.
            description TEXT,
            classification TEXT DEFAULT 'UNCLASSIFIED',
            country TEXT,
            isp TEXT,
            tags TEXT,  -- JSON array
            notes TEXT,
            osint_data TEXT,  -- JSON
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Operation-Target relationship
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operation_targets (
            operation_id TEXT,
            target_id TEXT,
            PRIMARY KEY (operation_id, target_id),
            FOREIGN KEY (operation_id) REFERENCES operations(operation_id),
            FOREIGN KEY (target_id) REFERENCES targets(target_id)
        )
    ''')
    
    # Scan results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_results (
            scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id TEXT,
            target_id TEXT,
            scan_type TEXT NOT NULL,  -- port_scan, vuln_scan, web_scan
            results TEXT NOT NULL,  -- JSON
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (operation_id) REFERENCES operations(operation_id),
            FOREIGN KEY (target_id) REFERENCES targets(target_id)
        )
    ''')
    
    # Vulnerabilities table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vulnerabilities (
            vuln_id TEXT PRIMARY KEY,
            operation_id TEXT,
            target_id TEXT,
            name TEXT NOT NULL,
            description TEXT,
            severity TEXT NOT NULL,  -- CRITICAL, HIGH, MEDIUM, LOW, INFO
            cvss_score REAL,
            cve_ids TEXT,  -- JSON array
            port INTEGER,
            service TEXT,
            evidence TEXT,
            remediation TEXT,
            verified BOOLEAN DEFAULT 0,
            false_positive BOOLEAN DEFAULT 0,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (operation_id) REFERENCES operations(operation_id),
            FOREIGN KEY (target_id) REFERENCES targets(target_id)
        )
    ''')
    
    # Exploit attempts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exploit_attempts (
            attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id TEXT,
            target_id TEXT,
            exploit_id TEXT NOT NULL,
            payload_id TEXT,
            success BOOLEAN DEFAULT 0,
            output TEXT,
            error TEXT,
            session_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (operation_id) REFERENCES operations(operation_id),
            FOREIGN KEY (target_id) REFERENCES targets(target_id)
        )
    ''')
    
    # C2 Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS c2_sessions (
            session_id TEXT PRIMARY KEY,
            operation_id TEXT,
            listener_id TEXT,
            beacon_id TEXT,
            external_ip TEXT,
            internal_ip TEXT,
            hostname TEXT,
            username TEXT,
            operating_system TEXT,
            architecture TEXT,
            process_id INTEGER,
            process_name TEXT,
            integrity_level TEXT,
            status TEXT DEFAULT 'active',
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (operation_id) REFERENCES operations(operation_id)
        )
    ''')
    
    # C2 Tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS c2_tasks (
            task_id TEXT PRIMARY KEY,
            session_id TEXT,
            command TEXT NOT NULL,
            arguments TEXT,  -- JSON array
            status TEXT DEFAULT 'pending',  -- pending, running, complete, failed
            output TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES c2_sessions(session_id)
        )
    ''')
    
    # Phishing campaigns table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phishing_campaigns (
            campaign_id TEXT PRIMARY KEY,
            operation_id TEXT,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'draft',
            template_id TEXT,
            delivery_method TEXT DEFAULT 'email',
            landing_page_html TEXT,
            redirect_url TEXT,
            tracking_enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (operation_id) REFERENCES operations(operation_id)
        )
    ''')
    
    # Phishing targets (campaign-specific)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phishing_targets (
            target_id TEXT PRIMARY KEY,
            campaign_id TEXT,
            first_name TEXT,
            last_name TEXT,
            email TEXT NOT NULL,
            phone TEXT,
            company TEXT,
            position TEXT,
            department TEXT,
            linkedin TEXT,
            osint_data TEXT,  -- JSON
            tags TEXT,  -- JSON array
            notes TEXT,
            FOREIGN KEY (campaign_id) REFERENCES phishing_campaigns(campaign_id)
        )
    ''')
    
    # Phishing results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phishing_results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id TEXT,
            target_id TEXT,
            email_sent BOOLEAN DEFAULT 0,
            email_opened BOOLEAN DEFAULT 0,
            link_clicked BOOLEAN DEFAULT 0,
            credentials_entered BOOLEAN DEFAULT 0,
            attachment_opened BOOLEAN DEFAULT 0,
            replied BOOLEAN DEFAULT 0,
            reported BOOLEAN DEFAULT 0,
            ip_address TEXT,
            user_agent TEXT,
            captured_username TEXT,
            captured_password TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES phishing_campaigns(campaign_id),
            FOREIGN KEY (target_id) REFERENCES phishing_targets(target_id)
        )
    ''')
    
    # Payloads table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payloads (
            payload_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            payload_type TEXT NOT NULL,
            platform TEXT NOT NULL,
            architecture TEXT,
            format TEXT,
            content_b64 TEXT,
            one_liner TEXT,
            md5_hash TEXT,
            sha256_hash TEXT,
            options TEXT,  -- JSON
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # C2 Listeners table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS c2_listeners (
            listener_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            listener_type TEXT NOT NULL,
            bind_host TEXT NOT NULL,
            bind_port INTEGER NOT NULL,
            status TEXT DEFAULT 'stopped',
            profile TEXT DEFAULT 'default',
            ssl_cert TEXT,
            ssl_key TEXT,
            domain TEXT,
            uri_path TEXT DEFAULT '/update',
            user_agent TEXT,
            jitter INTEGER DEFAULT 20,
            beacon_interval INTEGER DEFAULT 60,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP
        )
    ''')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ops_status ON operations(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_targets_type ON targets(target_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vulns_severity ON vulnerabilities(severity)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_status ON c2_sessions(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_phish_campaign ON phishing_results(campaign_id)')
    
    conn.commit()
    conn.close()
    
    logger.info(f"[RedTeam] Database initialized: {db_path}")


def get_db_connection(db_path: str = "/opt/codex-swarm/command-post/data/redteam.db"):
    """Get database connection with row factory"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


class RedTeamDatabase:
    """Database interface for Red Team operations"""
    
    def __init__(self, db_path: str = "/opt/codex-swarm/command-post/data/redteam.db"):
        self.db_path = db_path
        init_redteam_database(db_path)
    
    def save_operation(self, operation: Dict) -> bool:
        """Save operation to database"""
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO operations (
                    operation_id, codename, description, status, authorization_code,
                    two_person_integrity, witness_codename, operator_codename,
                    classification, phases_completed, findings
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                operation['operation_id'],
                operation['codename'],
                operation.get('description', ''),
                operation.get('status', 'pending'),
                operation.get('authorization_code', ''),
                operation.get('two_person_integrity', True),
                operation.get('witness_codename'),
                operation.get('operator_codename', ''),
                operation.get('classification', 'TOP SECRET//SCI//NOFORN'),
                json.dumps(operation.get('phases_completed', [])),
                json.dumps(operation.get('findings', []))
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[RedTeam] Failed to save operation: {e}")
            return False
    
    def save_target(self, target: Dict) -> bool:
        """Save target to database"""
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO targets (
                    target_id, name, target_type, value, description,
                    classification, country, isp, tags, notes, osint_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                target['target_id'],
                target['name'],
                target['target_type'],
                target['value'],
                target.get('description', ''),
                target.get('classification', 'UNCLASSIFIED'),
                target.get('country', ''),
                target.get('isp', ''),
                json.dumps(target.get('tags', [])),
                target.get('notes', ''),
                json.dumps(target.get('osint_data', {}))
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[RedTeam] Failed to save target: {e}")
            return False
    
    def save_vulnerability(self, vuln: Dict) -> bool:
        """Save vulnerability finding"""
        try:
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO vulnerabilities (
                    vuln_id, operation_id, target_id, name, description,
                    severity, cvss_score, cve_ids, port, service,
                    evidence, remediation, verified, false_positive
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                vuln['vuln_id'],
                vuln.get('operation_id', ''),
                vuln.get('target_id', ''),
                vuln['name'],
                vuln.get('description', ''),
                vuln['severity'],
                vuln.get('cvss_score', 0),
                json.dumps(vuln.get('cve_ids', [])),
                vuln.get('port', 0),
                vuln.get('service', ''),
                vuln.get('evidence', ''),
                vuln.get('remediation', ''),
                vuln.get('verified', False),
                vuln.get('false_positive', False)
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[RedTeam] Failed to save vulnerability: {e}")
            return False
    
    def get_operations(self, status: str = None) -> List[Dict]:
        """Get all operations, optionally filtered by status"""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('SELECT * FROM operations WHERE status = ?', (status,))
        else:
            cursor.execute('SELECT * FROM operations')
        
        rows = cursor.fetchall()
        conn.close()
        
        operations = []
        for row in rows:
            op = dict(row)
            op['phases_completed'] = json.loads(op.get('phases_completed', '[]'))
            op['findings'] = json.loads(op.get('findings', '[]'))
            operations.append(op)
        
        return operations
    
    def get_targets(self, operation_id: str = None) -> List[Dict]:
        """Get targets, optionally filtered by operation"""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        if operation_id:
            cursor.execute('''
                SELECT t.* FROM targets t
                JOIN operation_targets ot ON t.target_id = ot.target_id
                WHERE ot.operation_id = ?
            ''', (operation_id,))
        else:
            cursor.execute('SELECT * FROM targets')
        
        rows = cursor.fetchall()
        conn.close()
        
        targets = []
        for row in rows:
            target = dict(row)
            target['tags'] = json.loads(target.get('tags', '[]'))
            target['osint_data'] = json.loads(target.get('osint_data', '{}'))
            targets.append(target)
        
        return targets
    
    def get_vulnerabilities(self, operation_id: str = None, 
                           severity: str = None) -> List[Dict]:
        """Get vulnerabilities with optional filtering"""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM vulnerabilities'
        params = []
        conditions = []
        
        if operation_id:
            conditions.append('operation_id = ?')
            params.append(operation_id)
        
        if severity:
            conditions.append('severity = ?')
            params.append(severity)
        
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        vulns = []
        for row in rows:
            vuln = dict(row)
            vuln['cve_ids'] = json.loads(vuln.get('cve_ids', '[]'))
            vulns.append(vuln)
        
        return vulns
    
    def get_statistics(self) -> Dict:
        """Get Red Team database statistics"""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Count operations
        cursor.execute('SELECT COUNT(*) FROM operations')
        stats['total_operations'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM operations WHERE status = 'completed'")
        stats['completed_operations'] = cursor.fetchone()[0]
        
        # Count targets
        cursor.execute('SELECT COUNT(*) FROM targets')
        stats['total_targets'] = cursor.fetchone()[0]
        
        # Count vulnerabilities
        cursor.execute('SELECT COUNT(*) FROM vulnerabilities')
        stats['total_vulnerabilities'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM vulnerabilities WHERE severity = 'CRITICAL'")
        stats['critical_vulns'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM vulnerabilities WHERE severity = 'HIGH'")
        stats['high_vulns'] = cursor.fetchone()[0]
        
        # Count sessions
        cursor.execute("SELECT COUNT(*) FROM c2_sessions WHERE status = 'active'")
        stats['active_sessions'] = cursor.fetchone()[0]
        
        # Count phishing campaigns
        cursor.execute('SELECT COUNT(*) FROM phishing_campaigns')
        stats['phishing_campaigns'] = cursor.fetchone()[0]
        
        conn.close()
        return stats


__all__ = [
    'init_redteam_database',
    'RedTeamDatabase',
    'get_db_connection'
]
