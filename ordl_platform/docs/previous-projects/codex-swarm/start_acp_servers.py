#!/usr/bin/env python3
"""
ACP Server Starter
Starts all configured MCP and A2A servers.
"""

import asyncio
import subprocess
import sys
import yaml
import signal
from pathlib import Path
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('acp_starter')


class ACPServerManager:
    """Manages MCP and A2A server processes"""
    
    def __init__(self, config_path: str = "acp_config.yaml"):
        self.config_path = Path(config_path)
        self.processes: List[subprocess.Popen] = []
        self.running = False
        
    def load_config(self) -> Dict:
        """Load configuration from YAML"""
        if not self.config_path.exists():
            logger.error(f"Config file not found: {self.config_path}")
            return {}
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def start_mcp_server(self, server_config: Dict) -> subprocess.Popen:
        """Start an MCP server process"""
        name = server_config['name']
        command = server_config['command']
        args = server_config.get('args', [])
        
        full_command = [command] + args
        
        logger.info(f"Starting MCP server: {name}")
        logger.info(f"  Command: {' '.join(full_command)}")
        
        process = subprocess.Popen(
            full_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return process
    
    def start_a2a_agent(self, agent_config: Dict) -> subprocess.Popen:
        """Start an A2A agent process"""
        name = agent_config['name']
        agent_file = Path(__file__).parent / "a2a_agents" / f"{name}_agent.py"
        
        if not agent_file.exists():
            logger.error(f"A2A agent file not found: {agent_file}")
            return None
        
        logger.info(f"Starting A2A agent: {name}")
        logger.info(f"  File: {agent_file}")
        
        process = subprocess.Popen(
            [sys.executable, str(agent_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return process
    
    async def start_all(self):
        """Start all configured servers"""
        config = self.load_config()
        if not config:
            return
        
        self.running = True
        
        # Start MCP servers
        mcp_servers = config.get('mcp_servers', [])
        for server_config in mcp_servers:
            if server_config.get('enabled', True):
                try:
                    process = self.start_mcp_server(server_config)
                    if process:
                        self.processes.append(process)
                        await asyncio.sleep(2)  # Wait for server to start
                except Exception as e:
                    logger.error(f"Failed to start MCP server {server_config['name']}: {e}")
        
        # Start A2A agents
        a2a_agents = config.get('a2a_agents', [])
        for agent_config in a2a_agents:
            if agent_config.get('enabled', True):
                try:
                    process = self.start_a2a_agent(agent_config)
                    if process:
                        self.processes.append(process)
                        await asyncio.sleep(2)  # Wait for agent to start
                except Exception as e:
                    logger.error(f"Failed to start A2A agent {agent_config['name']}: {e}")
        
        logger.info(f"Started {len(self.processes)} processes")
    
    def stop_all(self):
        """Stop all server processes"""
        logger.info("Stopping all ACP servers...")
        
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
        
        self.processes.clear()
        self.running = False
        logger.info("All servers stopped")
    
    async def monitor(self):
        """Monitor running processes"""
        while self.running:
            for process in list(self.processes):
                ret = process.poll()
                if ret is not None:
                    logger.warning(f"Process exited with code {ret}")
                    self.processes.remove(process)
            
            await asyncio.sleep(5)
    
    async def run(self):
        """Main run loop"""
        await self.start_all()
        
        if self.processes:
            logger.info("\n" + "="*60)
            logger.info("ACP Servers Running")
            logger.info("="*60)
            logger.info("Press Ctrl+C to stop")
            
            try:
                await self.monitor()
            except KeyboardInterrupt:
                pass
            finally:
                self.stop_all()


def main():
    """Main entry point"""
    manager = ACPServerManager()
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("\nReceived shutdown signal")
        manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run
    asyncio.run(manager.run())


if __name__ == "__main__":
    main()
