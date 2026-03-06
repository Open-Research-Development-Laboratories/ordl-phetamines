#!/usr/bin/env python3
"""
ACP v7.0 Comprehensive Tests
Tests all components: bus, subagents, skills, nexus
"""

import pytest
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from command_post.acp.bus import ACPMessageBus, ACPMessage, ACPRequest, ACPResponse
from command_post.acp.nexus import NexusRouter
from command_post.acp.subagent import ACPSubagent, SubagentConfig
from command_post.acp.skills.registry import SkillRegistry, ExecutionContext
from command_post.acp.skills.offensive import OFFENSIVE_SKILLS
from command_post.acp.skills.defensive import DEFENSIVE_SKILLS
from command_post.acp.skills.intelligence import INTELLIGENCE_SKILLS
from command_post.acp.skills.automation import AUTOMATION_SKILLS


class TestACPMessageBus:
    """Test ACP message bus functionality"""
    
    @pytest.mark.asyncio
    async def test_bus_initialization(self):
        """Test message bus starts and stops"""
        bus = ACPMessageBus(host="127.0.0.1", port=18030)
        await bus.start()
        
        assert bus.running
        assert bus.subscriptions
        
        await bus.stop()
        assert not bus.running
    
    @pytest.mark.asyncio
    async def test_agent_registration(self):
        """Test agent registration"""
        bus = ACPMessageBus(host="127.0.0.1", port=18031)
        await bus.start()
        
        # Register agent
        success = bus.register_agent("test-agent", {})
        assert success is True
        
        # Verify registration
        assert "test-agent" in bus.registered_agents
        
        await bus.stop()
    
    @pytest.mark.asyncio
    async def test_message_creation(self):
        """Test ACP message creation"""
        msg = ACPMessage(
            type="test",
            payload={"key": "value"}
        )
        
        assert msg.type == "test"
        assert msg.payload == {"key": "value"}
        assert msg.id is not None
        assert msg.timestamp is not None


class TestSkillRegistry:
    """Test 77+ skills registry"""
    
    def test_skill_counts(self):
        """Verify we have 77+ skills"""
        total = (
            len(OFFENSIVE_SKILLS) +
            len(DEFENSIVE_SKILLS) +
            len(INTELLIGENCE_SKILLS) +
            len(AUTOMATION_SKILLS)
        )
        
        assert total >= 77, f"Expected 77+ skills, got {total}"
    
    def test_offensive_skills(self):
        """Test offensive skills structure"""
        assert len(OFFENSIVE_SKILLS) >= 25
        
        for skill in OFFENSIVE_SKILLS:
            assert skill['id'].startswith("off_")
            assert skill.get('params_schema') is not None
            # Tier is an integer, not enum in the dict format
            assert skill.get('tier') in [1, 2, 3]
    
    def test_defensive_skills(self):
        """Test defensive skills structure"""
        assert len(DEFENSIVE_SKILLS) >= 25
        
        for skill in DEFENSIVE_SKILLS:
            assert skill['id'].startswith("def_")
            assert skill.get('params_schema') is not None
    
    def test_intelligence_skills(self):
        """Test intelligence skills structure"""
        assert len(INTELLIGENCE_SKILLS) >= 20
        
        for skill in INTELLIGENCE_SKILLS:
            assert skill['id'].startswith("int_")
            assert skill.get('params_schema') is not None
    
    def test_automation_skills(self):
        """Test automation skills structure"""
        assert len(AUTOMATION_SKILLS) >= 7
        
        for skill in AUTOMATION_SKILLS:
            assert skill['id'].startswith("auto_")
            assert skill.get('params_schema') is not None
    
    def test_registry_load(self):
        """Test skill registry loading"""
        registry = SkillRegistry()
        registry.load_skill_modules()
        
        # Check internal skills dict has been populated
        assert len(registry._skills) >= 77


class TestNexusRouter:
    """Test Nexus routing"""
    
    @pytest.mark.asyncio
    async def test_nexus_initialization(self):
        """Test Nexus starts with bus"""
        bus = ACPMessageBus(host="127.0.0.1", port=18032)
        skills = SkillRegistry()
        nexus = NexusRouter(bus, skills)
        
        await bus.start()
        await nexus.start()
        
        assert nexus.running
        assert nexus.agent_id == "nexus"
        
        await nexus.stop()
        await bus.stop()
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health check endpoint"""
        bus = ACPMessageBus(host="127.0.0.1", port=18033)
        skills = SkillRegistry()
        nexus = NexusRouter(bus, skills)
        
        await bus.start()
        await nexus.start()
        
        from command_post.acp.bus import ACPRequest
        
        request = ACPRequest(method="health.check")
        response = await bus.request_response("test", "nexus", request, timeout=5)
        
        assert response is not None
        assert response.status_code == 200
        
        await nexus.stop()
        await bus.stop()


class TestSubagents:
    """Test subagent functionality"""
    
    @pytest.mark.asyncio
    async def test_subagent_creation(self):
        """Test subagent creation and registration"""
        bus = ACPMessageBus(host="127.0.0.1", port=18034)
        await bus.start()
        
        config = SubagentConfig(
            agent_id="test-subagent",
            name="Test Agent",
            skills=["off_recon_nmap"],
            clearance="SECRET"
        )
        
        agent = ACPSubagent(bus, config)
        await agent.start()
        
        assert agent.agent_id == "test-subagent"
        assert agent.skills == ["off_recon_nmap"]
        assert agent.running
        
        await agent.stop()
        await bus.stop()
    
    @pytest.mark.asyncio
    async def test_subagent_status(self):
        """Test subagent status reporting"""
        bus = ACPMessageBus(host="127.0.0.1", port=18035)
        await bus.start()
        
        config = SubagentConfig(
            agent_id="status-test",
            name="Status Test",
            skills=["off_recon_nmap", "off_web_tech"],
            clearance="UNCLASSIFIED"
        )
        
        agent = ACPSubagent(bus, config)
        await agent.start()
        
        status = agent.get_status()
        
        assert status['agent_id'] == "status-test"
        assert status['state'] == "running"
        assert len(status['skills']) == 2
        assert status['clearance'] == "UNCLASSIFIED"
        
        await agent.stop()
        await bus.stop()


class TestIntegration:
    """Integration tests for ACP system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_message(self):
        """Test full message flow"""
        bus = ACPMessageBus(host="127.0.0.1", port=18036)
        skills = SkillRegistry()
        nexus = NexusRouter(bus, skills)
        
        await bus.start()
        await nexus.start()
        
        # Create a test agent
        config = SubagentConfig(
            agent_id="integration-agent",
            name="Integration Test",
            skills=["off_recon_nmap"],
            clearance="SECRET"
        )
        agent = ACPSubagent(bus, config)
        await agent.start()
        
        # Send request
        from command_post.acp.bus import ACPRequest
        
        request = ACPRequest(
            method="off_recon_nmap",
            params={"target": "127.0.0.1", "scan_type": "quick"}
        )
        
        response = await bus.request_response(
            "test-client",
            "integration-agent",
            request,
            timeout=10
        )
        
        # Verify response
        assert response is not None
        assert hasattr(response, 'status_code')
        assert hasattr(response, 'body')
        
        await agent.stop()
        await nexus.stop()
        await bus.stop()
    
    def test_skill_execution_context(self):
        """Test execution context creation"""
        context = ExecutionContext(
            agent_id="test-agent",
            clearance="SECRET",
            task_id="task-123",
            timeout=60
        )
        
        assert context.agent_id == "test-agent"
        assert context.clearance == "SECRET"
        assert context.task_id == "task-123"


class TestACPV7Stats:
    """Test ACP v7 statistics"""
    
    def test_skill_breakdown(self):
        """Output skill statistics"""
        stats = {
            'offensive': len(OFFENSIVE_SKILLS),
            'defensive': len(DEFENSIVE_SKILLS),
            'intelligence': len(INTELLIGENCE_SKILLS),
            'automation': len(AUTOMATION_SKILLS),
            'total': len(OFFENSIVE_SKILLS) + len(DEFENSIVE_SKILLS) +
                     len(INTELLIGENCE_SKILLS) + len(AUTOMATION_SKILLS)
        }
        
        print(f"\n{'='*50}")
        print("ORDL NEXUS v7.0 - ACP Statistics")
        print(f"{'='*50}")
        print(f"Offensive Skills:   {stats['offensive']:3d}")
        print(f"Defensive Skills:   {stats['defensive']:3d}")
        print(f"Intelligence:       {stats['intelligence']:3d}")
        print(f"Automation:         {stats['automation']:3d}")
        print(f"{'-'*50}")
        print(f"Total:              {stats['total']:3d}")
        print(f"{'='*50}")
        
        assert stats['total'] >= 77


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
