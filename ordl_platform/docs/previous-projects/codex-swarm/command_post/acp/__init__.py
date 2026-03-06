#!/usr/bin/env python3
"""
================================================================================
ORDL NEXUS v7.0 - AGENT COMMUNICATION PROTOCOL (ACP)
================================================================================
Classification: TOP SECRET//SCI//NOFORN

Bulletproof subagent communication system:
- ZeroMQ backend for sub-millisecond latency
- Guaranteed message delivery with ACKs
- Encrypted channels (post-quantum ready)
- Auto-scaling to 1000+ subagents
- Skill orchestration across distributed agents

Author: ORDL Cyber Operations Division
Version: 7.0.0
================================================================================
"""

from .bus import ACPMessageBus, ACPMessage, ACPRequest, ACPResponse
from .subagent import ACPSubagent, SubagentConfig
from .nexus import NexusRouter

__all__ = [
    'ACPMessageBus',
    'ACPMessage', 
    'ACPRequest',
    'ACPResponse',
    'ACPSubagent',
    'SubagentConfig',
    'NexusRouter'
]

__version__ = '7.0.0'
