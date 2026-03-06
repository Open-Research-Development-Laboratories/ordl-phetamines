#!/usr/bin/env python3
"""
ORDL NEXUS - Skills Framework
All 77+ skills organized by category
"""

from .registry import SkillRegistry, Skill, SkillCategory, SkillResult
from .offensive import OFFENSIVE_SKILLS
from .defensive import DEFENSIVE_SKILLS
from .intelligence import INTELLIGENCE_SKILLS
from .automation import AUTOMATION_SKILLS

__all__ = [
    'SkillRegistry',
    'Skill',
    'SkillCategory',
    'SkillResult',
    'OFFENSIVE_SKILLS',
    'DEFENSIVE_SKILLS',
    'INTELLIGENCE_SKILLS',
    'AUTOMATION_SKILLS'
]
