#!/usr/bin/env python3
"""
ACP Integration Layer
Ties ACP, Skills, Protocol Adapters, and existing ORDL system together
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from .bus import ACPMessageBus
from .nexus import NexusRouter
from .skills.registry import SkillRegistry
from .subagent import ACPSubagent, SubagentConfig
from .adapters import AdapterRegistry, ExecutionRequest

logger = logging.getLogger('acp.integration')


class ACPIntegration:
    """
    Main integration point for ACP into ORDL
    
    This connects the new ACP system with the existing:
    - Blue Team
    - Agent System
    - Router
    - Protocol Adapters (MCP, A2A)
    """
    
    def __init__(self, app=None):
        self.app = app
        self.bus: Optional[ACPMessageBus] = None
        self.nexus: Optional[NexusRouter] = None
        self.skills: Optional[SkillRegistry] = None
        self.subagents: Dict[str, ACPSubagent] = {}
        self.adapters: Optional[AdapterRegistry] = None
        self.running = False
    
    async def initialize(self, adapter_configs: Optional[list] = None):
        """
        Initialize ACP integration
        
        Args:
            adapter_configs: Optional list of adapter configurations to register
        """
        logger.info("[ACP] Initializing integration...")
        
        # Create message bus
        self.bus = ACPMessageBus(host="127.0.0.1", port=18020)
        
        # Create skill registry and load all 77+ skills
        self.skills = SkillRegistry()
        self.skills.load_skill_modules()
        
        # Create Nexus router
        self.nexus = NexusRouter(self.bus, self.skills)
        
        # Create adapter registry for external protocol support
        self.adapters = AdapterRegistry()
        
        # Register any configured adapters
        if adapter_configs:
            for config in adapter_configs:
                try:
                    await self.adapters.register(config)
                    logger.info(f"[ACP] Registered adapter: {config.name}")
                except Exception as e:
                    logger.error(f"[ACP] Failed to register adapter {config.name}: {e}")
        
        # Start components
        await self.bus.start()
        await self.nexus.start()
        
        # Create default subagents
        await self._create_default_subagents()
        
        self.running = True
        logger.info("[ACP] Integration initialized successfully")
        logger.info(f"[ACP] Skills loaded: {len(self.skills._skills)}")
        logger.info(f"[ACP] Subagents created: {len(self.subagents)}")
        if self.adapters:
            logger.info(f"[ACP] Protocol adapters: {len(self.adapters.list_adapters())}")
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("[ACP] Shutting down...")
        
        # Stop all subagents
        for agent_id, agent in self.subagents.items():
            await agent.stop()
        
        # Stop Nexus and bus
        if self.nexus:
            await self.nexus.stop()
        if self.bus:
            await self.bus.stop()
        
        # Close all adapters
        if self.adapters:
            await self.adapters.close_all()
        
        self.running = False
        logger.info("[ACP] Shutdown complete")
    
    async def _create_default_subagents(self):
        """Create default specialized subagents"""
        
        # Reconnaissance Subagent
        recon_agent = ACPSubagent(
            self.bus,
            SubagentConfig(
                agent_id="subagent-recon",
                name="Reconnaissance Agent",
                skills=[
                    "off_recon_nmap",
                    "off_recon_subdomain",
                    "off_recon_dns",
                    "off_web_tech",
                    "int_osint_shodan"
                ],
                clearance="SECRET"
            )
        )
        await recon_agent.start()
        self.subagents["subagent-recon"] = recon_agent
        
        # Web Testing Subagent
        web_agent = ACPSubagent(
            self.bus,
            SubagentConfig(
                agent_id="subagent-web",
                name="Web Application Tester",
                skills=[
                    "off_web_sqlmap",
                    "off_web_xss",
                    "off_web_csrf",
                    "off_web_lfi",
                    "off_web_nuclei"
                ],
                clearance="SECRET"
            )
        )
        await web_agent.start()
        self.subagents["subagent-web"] = web_agent
        
        # Blue Team Subagent
        blueteam_agent = ACPSubagent(
            self.bus,
            SubagentConfig(
                agent_id="subagent-blueteam",
                name="Blue Team Defender",
                skills=[
                    "def_mon_sigma",
                    "def_mon_yara",
                    "def_mon_hunt",
                    "def_ir_contain",
                    "def_ir_playbook"
                ],
                clearance="TOPSECRET"
            )
        )
        await blueteam_agent.start()
        self.subagents["subagent-blueteam"] = blueteam_agent
        
        # Intelligence Subagent
        intel_agent = ACPSubagent(
            self.bus,
            SubagentConfig(
                agent_id="subagent-intel",
                name="Threat Intelligence",
                skills=[
                    "int_osint_shodan",
                    "int_osint_theharvester",
                    "int_dark_search",
                    "int_git_search",
                    "int_adv_correlate"
                ],
                clearance="TOPSECRET"
            )
        )
        await intel_agent.start()
        self.subagents["subagent-intel"] = intel_agent
        
        # Exploitation Subagent
        exploit_agent = ACPSubagent(
            self.bus,
            SubagentConfig(
                agent_id="subagent-exploit",
                name="Exploitation Specialist",
                skills=[
                    "off_exp_metasploit",
                    "off_exp_cve",
                    "off_exp_bruteforce",
                    "off_exp_password",
                    "off_adv_payload"
                ],
                clearance="TOPSECRET"
            )
        )
        await exploit_agent.start()
        self.subagents["subagent-exploit"] = exploit_agent
        
        # Forensics Subagent
        forensics_agent = ACPSubagent(
            self.bus,
            SubagentConfig(
                agent_id="subagent-forensics",
                name="Digital Forensics",
                skills=[
                    "def_for_disk",
                    "def_for_memory",
                    "def_for_network",
                    "def_for_timeline",
                    "def_for_malware"
                ],
                clearance="TOPSECRET"
            )
        )
        await forensics_agent.start()
        self.subagents["subagent-forensics"] = forensics_agent
    
    async def execute_skill(self, skill_name: str, params: Dict[str, Any],
                          agent_id: Optional[str] = None) -> Any:
        """
        Execute a skill through ACP
        
        Args:
            skill_name: Skill to execute
            params: Skill parameters
            agent_id: Specific agent, or None for auto-routing
            
        Returns:
            Skill execution result
        """
        if agent_id and agent_id in self.subagents:
            # Direct to specific agent
            agent = self.subagents[agent_id]
            return await agent.execute_skill(skill_name, params)
        else:
            # Route through Nexus
            from .bus import ACPRequest
            
            request = ACPRequest(
                method=skill_name,
                params=params
            )
            
            response = await self.bus.request_response(
                'ordl-core',
                'nexus',
                request
            )
            
            return response
    
    def get_status(self) -> Dict[str, Any]:
        """Get complete ACP status"""
        status = {
            'running': self.running,
            'bus': self.bus.get_stats() if self.bus else {},
            'nexus': self.nexus.get_system_status() if self.nexus else {},
            'subagents': {
                aid: agent.get_status()
                for aid, agent in self.subagents.items()
            }
        }
        
        # Add adapter status
        if self.adapters:
            adapter_status = asyncio.run(self.adapters.health_check())
            status['adapters'] = adapter_status
        
        return status
    
    async def register_adapter(self, config) -> bool:
        """
        Register a protocol adapter
        
        Args:
            config: Adapter configuration (MCP or A2A)
            
        Returns:
            True if successful
        """
        if not self.adapters:
            logger.error("[ACP] Adapter registry not initialized")
            return False
        
        adapter = await self.adapters.register(config)
        return adapter is not None
    
    async def execute_via_adapter(self, adapter_name: str, capability_id: str,
                                   parameters: Dict[str, Any]) -> Any:
        """
        Execute a capability through a protocol adapter
        
        Args:
            adapter_name: Name of the registered adapter
            capability_id: Capability/tool/skill ID
            parameters: Execution parameters
            
        Returns:
            Execution result
        """
        if not self.adapters:
            return {'error': 'Adapter registry not initialized'}
        
        request = ExecutionRequest(
            capability_id=capability_id,
            parameters=parameters
        )
        
        result = await self.adapters.execute(adapter_name, request)
        return {
            'success': result.success,
            'data': result.data,
            'error': result.error,
            'execution_time': result.execution_time
        }
    
    async def discover_adapters(self) -> Dict[str, list]:
        """
        Discover all capabilities from registered adapters
        
        Returns:
            Dictionary mapping adapter names to their capabilities
        """
        if not self.adapters:
            return {}
        
        return await self.adapters.discover_all_capabilities()
