#!/usr/bin/env python3
"""
Training Data Collector
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class TrainingDataCollector:
    """Collect training data from all ORDL components"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    async def collect_skill_traces(self) -> List[Dict]:
        """Collect skill execution traces"""
        traces = []
        
        # From BlueTeam DB
        bt_db = Path('/opt/codex-swarm/command-post/blueteam/blueteam.db')
        if bt_db.exists():
            conn = sqlite3.connect(str(bt_db))
            cursor = conn.cursor()
            
            # Get log entries that triggered alerts
            cursor.execute("""
                SELECT * FROM log_entries 
                WHERE alert_triggered = 1 
                ORDER BY timestamp DESC
                LIMIT 1000
            """)
            
            for row in cursor.fetchall():
                traces.append({
                    'type': 'detection',
                    'source': 'blueteam',
                    'timestamp': row[1],
                    'data': row[4],
                    'outcome': 'alert_generated'
                })
            
            conn.close()
        
        return traces
    
    async def collect_conversations(self) -> List[Dict]:
        """Collect agent conversation logs"""
        conversations = []
        
        # From Nexus DB
        nexus_db = Path('/opt/codex-swarm/command-post/data/nexus.db')
        if nexus_db.exists():
            conn = sqlite3.connect(str(nexus_db))
            cursor = conn.cursor()
            
            # Get conversation history
            cursor.execute("""
                SELECT * FROM conversations
                ORDER BY created_at DESC
                LIMIT 500
            """)
            
            for row in cursor.fetchall():
                conversations.append({
                    'type': 'conversation',
                    'id': row[0],
                    'messages': json.loads(row[2]) if row[2] else [],
                    'created_at': row[3]
                })
            
            conn.close()
        
        return conversations
    
    async def collect_detections(self) -> List[Dict]:
        """Collect detection outcomes"""
        detections = []
        
        bt_db = Path('/opt/codex-swarm/command-post/blueteam/blueteam.db')
        if bt_db.exists():
            conn = sqlite3.connect(str(bt_db))
            cursor = conn.cursor()
            
            # Get alerts with their resolution
            cursor.execute("""
                SELECT * FROM alerts
                ORDER BY timestamp DESC
                LIMIT 500
            """)
            
            for row in cursor.fetchall():
                detections.append({
                    'type': 'detection',
                    'alert_id': row[0],
                    'severity': row[3],
                    'rule_triggered': row[4],
                    'status': row[9],
                    'timestamp': row[1]
                })
            
            conn.close()
        
        return detections
    
    async def collect_tool_usage(self) -> List[Dict]:
        """Collect tool usage patterns"""
        usage = []
        
        # From agent audit logs
        nexus_db = Path('/opt/codex-swarm/command-post/data/nexus.db')
        if nexus_db.exists():
            conn = sqlite3.connect(str(nexus_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM agent_audit_logs
                WHERE action LIKE '%tool%'
                ORDER BY timestamp DESC
                LIMIT 1000
            """)
            
            for row in cursor.fetchall():
                usage.append({
                    'type': 'tool_usage',
                    'agent_id': row[1],
                    'action': row[2],
                    'details': json.loads(row[3]) if row[3] else {},
                    'timestamp': row[4]
                })
            
            conn.close()
        
        return usage
    
    async def create_training_dataset(self, data_sources: Dict[str, List]) -> Path:
        """
        Create unified training dataset
        
        Format: Alpaca-style instruction tuning
        """
        dataset_path = self.data_dir / 'training_dataset.jsonl'
        
        with open(dataset_path, 'w') as f:
            # Skill execution examples
            for trace in data_sources.get('skill_traces', []):
                if trace.get('data'):
                    example = {
                        'instruction': f"Analyze this security event: {trace['data'][:200]}",
                        'input': trace['data'],
                        'output': f"This event triggered a {trace['outcome']}. Recommendation: Investigate immediately."
                    }
                    f.write(json.dumps(example) + '\n')
            
            # Conversation examples
            for conv in data_sources.get('agent_conversations', []):
                messages = conv.get('messages', [])
                if len(messages) >= 2:
                    example = {
                        'instruction': messages[0].get('content', ''),
                        'input': '',
                        'output': messages[1].get('content', '')
                    }
                    f.write(json.dumps(example) + '\n')
            
            # Detection examples
            for det in data_sources.get('detection_outcomes', []):
                example = {
                    'instruction': f"A {det['severity']} severity alert was triggered by rule {det['rule_triggered']}. What actions should be taken?",
                    'input': json.dumps(det),
                    'output': f"Investigate the alert immediately. Check logs for the timeframe around {det['timestamp']}. Validate if this is a true positive."
                }
                f.write(json.dumps(example) + '\n')
        
        return dataset_path
