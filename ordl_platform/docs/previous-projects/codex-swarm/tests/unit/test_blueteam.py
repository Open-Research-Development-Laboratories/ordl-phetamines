#!/usr/bin/env python3
"""
================================================================================
ORDL BLUE TEAM UNIT TESTS
================================================================================
Classification: TOP SECRET//SCI//NOFORN
================================================================================
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, '/opt/codex-swarm/command-post')

from blueteam import (
    BlueTeamManager, Alert, AlertSeverity, Incident, IncidentStatus,
    IOC, IOCType, LogSource
)


class TestAlertSeverity:
    """Test AlertSeverity enum"""
    
    def test_severity_levels(self):
        assert AlertSeverity.CRITICAL.value == 'CRITICAL'
        assert AlertSeverity.HIGH.value == 'HIGH'
        assert AlertSeverity.MEDIUM.value == 'MEDIUM'
        assert AlertSeverity.LOW.value == 'LOW'
        assert AlertSeverity.INFO.value == 'INFO'


class TestIncidentStatus:
    """Test IncidentStatus enum"""
    
    def test_status_workflow(self):
        assert IncidentStatus.NEW.value == 'NEW'
        assert IncidentStatus.ASSIGNED.value == 'ASSIGNED'
        assert IncidentStatus.INVESTIGATING.value == 'INVESTIGATING'
        assert IncidentStatus.CONTAINED.value == 'CONTAINED'
        assert IncidentStatus.ERADICATED.value == 'ERADICATED'
        assert IncidentStatus.RECOVERED.value == 'RECOVERED'
        assert IncidentStatus.CLOSED.value == 'CLOSED'


class TestIOCType:
    """Test IOCType enum"""
    
    def test_ioc_types(self):
        assert IOCType.IP.value == 'ip'
        assert IOCType.DOMAIN.value == 'domain'
        assert IOCType.HASH_MD5.value == 'hash_md5'
        assert IOCType.HASH_SHA256.value == 'hash_sha256'


class TestAlert:
    """Test Alert dataclass"""
    
    @pytest.fixture
    def sample_alert(self):
        return Alert(
            alert_id='alert-001',
            timestamp=datetime.utcnow(),
            severity=AlertSeverity.HIGH,
            title='Test Alert',
            description='Test description',
            source='test_source',
            rule_name='BT-TEST-001',
            rule_id='BT-TEST-001',
            raw_data={'test': 'data'}
        )
    
    def test_alert_creation(self, sample_alert):
        assert sample_alert.alert_id == 'alert-001'
        assert sample_alert.severity == AlertSeverity.HIGH
        assert sample_alert.status == 'OPEN'
    
    def test_alert_to_dict(self, sample_alert):
        data = sample_alert.to_dict()
        assert data['alert_id'] == 'alert-001'
        assert data['severity'] == 'HIGH'
        assert 'timestamp' in data


class TestBlueTeamManager:
    """Test BlueTeamManager"""
    
    @pytest.fixture
    def bt_manager(self, temp_db_path):
        with patch('blueteam.sqlite3') as mock_sqlite:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_sqlite.connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            mgr = BlueTeamManager(db_path=temp_db_path)
            yield mgr
    
    def test_initialization(self, bt_manager):
        assert bt_manager is not None
        assert hasattr(bt_manager, 'alerts')
        assert hasattr(bt_manager, 'incidents')
        assert hasattr(bt_manager, 'iocs')
    
    def test_add_ioc(self, bt_manager):
        ioc = bt_manager.add_ioc(
            ioc_type=IOCType.IP,
            value='192.168.1.100',
            source='test_intel',
            confidence=90,
            severity=AlertSeverity.HIGH,
            description='Test IOC'
        )
        
        assert ioc is not None
        assert ioc.ioc_type == IOCType.IP
        assert ioc.value == '192.168.1.100'
    
    def test_check_ioc_match(self, bt_manager):
        # Add IOC first
        bt_manager.add_ioc(
            ioc_type=IOCType.IP,
            value='192.168.1.100',
            source='test',
            confidence=90,
            severity=AlertSeverity.HIGH,
            description='Malicious IP'
        )
        
        # Check match
        match = bt_manager.check_ioc('192.168.1.100')
        assert match is not None
        assert match.ioc_type == IOCType.IP
    
    def test_check_ioc_no_match(self, bt_manager):
        match = bt_manager.check_ioc('10.0.0.1')
        assert match is None
    
    def test_create_incident(self, bt_manager):
        incident = bt_manager.create_incident(
            title='Test Incident',
            description='Test description',
            severity=AlertSeverity.HIGH
        )
        
        assert incident is not None
        assert incident.title == 'Test Incident'
        assert incident.status == IncidentStatus.NEW
    
    def test_update_incident_status(self, bt_manager):
        # Create incident
        incident = bt_manager.create_incident(
            title='Test',
            description='Test',
            severity=AlertSeverity.MEDIUM
        )
        
        # Update status
        updated = bt_manager.update_incident_status(
            incident.incident_id,
            IncidentStatus.INVESTIGATING
        )
        
        assert updated is True
        assert incident.status == IncidentStatus.INVESTIGATING
    
    def test_get_stats(self, bt_manager):
        stats = bt_manager.get_stats()
        assert 'total_alerts' in stats
        assert 'open_alerts' in stats
        assert 'total_incidents' in stats
        assert 'total_iocs' in stats


class TestDetectionEngine:
    """Test detection engine (to be implemented)"""
    
    @pytest.mark.skip(reason="Detection engine not yet implemented")
    def test_detection_engine_exists(self):
        """Placeholder for detection engine tests"""
        pass


class TestLogIngestion:
    """Test log ingestion (to be implemented)"""
    
    @pytest.mark.skip(reason="Log ingestion not yet implemented")
    def test_log_ingestion_exists(self):
        """Placeholder for log ingestion tests"""
        pass
