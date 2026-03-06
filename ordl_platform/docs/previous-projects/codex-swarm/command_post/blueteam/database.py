#!/usr/bin/env python3
"""ORDL Blue Team Database Layer - IOC, Alert, and Incident Storage"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

class BlueTeamDatabase:
    """Database operations for Blue Team module"""
    
    def __init__(self, db_path: str = "/opt/codex-swarm/command-post/data/nexus.db"):
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self):
        """Initialize Blue Team database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # IOCs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blueteam_iocs (
                    ioc_id TEXT PRIMARY KEY,
                    ioc_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    source TEXT,
                    confidence INTEGER,
                    severity TEXT,
                    description TEXT,
                    threat_actor TEXT,
                    campaign TEXT,
                    added_at TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            
            # Alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blueteam_alerts (
                    alert_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    severity TEXT,
                    title TEXT,
                    description TEXT,
                    source TEXT,
                    rule_name TEXT,
                    rule_id TEXT,
                    raw_data TEXT,
                    ioc_matches TEXT,
                    related_events TEXT,
                    status TEXT DEFAULT 'OPEN',
                    assigned_to TEXT,
                    incident_id TEXT,
                    mitre_techniques TEXT,
                    cvss_score REAL
                )
            """)
            
            # Incidents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blueteam_incidents (
                    incident_id TEXT PRIMARY KEY,
                    created_at TEXT,
                    updated_at TEXT,
                    title TEXT,
                    description TEXT,
                    severity TEXT,
                    status TEXT,
                    lead_analyst TEXT,
                    assigned_team TEXT,
                    related_alerts TEXT,
                    affected_assets TEXT,
                    timeline TEXT,
                    evidence_refs TEXT,
                    containment_actions TEXT,
                    root_cause TEXT,
                    lessons_learned TEXT
                )
            """)
            
            # Log entries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blueteam_logs (
                    entry_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    source_type TEXT,
                    source_host TEXT,
                    message TEXT,
                    normalized_data TEXT,
                    ioc_matches TEXT,
                    alert_triggered BOOLEAN,
                    alert_id TEXT
                )
            """)
            
            conn.commit()
    
    def save_ioc(self, ioc_data: Dict) -> bool:
        """Save IOC to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO blueteam_iocs
                    (ioc_id, ioc_type, value, source, confidence, severity, description,
                     threat_actor, campaign, added_at, first_seen, last_seen, hit_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ioc_data['ioc_id'],
                    ioc_data['ioc_type'],
                    ioc_data['value'],
                    ioc_data.get('source'),
                    ioc_data.get('confidence'),
                    ioc_data.get('severity'),
                    ioc_data.get('description'),
                    ioc_data.get('threat_actor'),
                    ioc_data.get('campaign'),
                    ioc_data.get('added_at'),
                    ioc_data.get('first_seen'),
                    ioc_data.get('last_seen'),
                    ioc_data.get('hit_count', 0)
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"[DB ERROR] Failed to save IOC: {e}")
            return False
    
    def get_ioc_by_value(self, value: str) -> Optional[Dict]:
        """Get IOC by value"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM blueteam_iocs WHERE value = ?",
                (value,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row, cursor)
            return None
    
    def save_alert(self, alert_data: Dict) -> bool:
        """Save alert to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO blueteam_alerts
                    (alert_id, timestamp, severity, title, description, source,
                     rule_name, rule_id, raw_data, ioc_matches, related_events,
                     status, assigned_to, incident_id, mitre_techniques, cvss_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert_data['alert_id'],
                    alert_data['timestamp'],
                    alert_data['severity'],
                    alert_data['title'],
                    alert_data['description'],
                    alert_data.get('source'),
                    alert_data.get('rule_name'),
                    alert_data.get('rule_id'),
                    json.dumps(alert_data.get('raw_data', {})),
                    json.dumps(alert_data.get('ioc_matches', [])),
                    json.dumps(alert_data.get('related_events', [])),
                    alert_data.get('status', 'OPEN'),
                    alert_data.get('assigned_to'),
                    alert_data.get('incident_id'),
                    json.dumps(alert_data.get('mitre_techniques', [])),
                    alert_data.get('cvss_score')
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"[DB ERROR] Failed to save alert: {e}")
            return False
    
    def save_incident(self, incident_data: Dict) -> bool:
        """Save incident to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO blueteam_incidents
                    (incident_id, created_at, updated_at, title, description, severity,
                     status, lead_analyst, assigned_team, related_alerts, affected_assets,
                     timeline, evidence_refs, containment_actions, root_cause, lessons_learned)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    incident_data['incident_id'],
                    incident_data['created_at'],
                    incident_data['updated_at'],
                    incident_data['title'],
                    incident_data['description'],
                    incident_data['severity'],
                    incident_data['status'],
                    incident_data.get('lead_analyst'),
                    json.dumps(incident_data.get('assigned_team', [])),
                    json.dumps(incident_data.get('related_alerts', [])),
                    json.dumps(incident_data.get('affected_assets', [])),
                    json.dumps(incident_data.get('timeline', [])),
                    json.dumps(incident_data.get('evidence_refs', [])),
                    json.dumps(incident_data.get('containment_actions', [])),
                    incident_data.get('root_cause'),
                    incident_data.get('lessons_learned')
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"[DB ERROR] Failed to save incident: {e}")
            return False
    
    def _row_to_dict(self, row, cursor) -> Dict:
        """Convert database row to dictionary"""
        result = {}
        for idx, col in enumerate(cursor.description):
            result[col[0]] = row[idx]
        return result


# Singleton
_db_instance = None

def get_blueteam_db() -> BlueTeamDatabase:
    global _db_instance
    if _db_instance is None:
        _db_instance = BlueTeamDatabase()
    return _db_instance
