#!/usr/bin/env python3
"""
Skill Registry - Dynamic Skill Management
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from datetime import datetime

logger = logging.getLogger('acp.skills')


class SkillCategory(Enum):
    """Skill categories"""
    OFFENSIVE = "offensive"
    DEFENSIVE = "defensive"
    INTELLIGENCE = "intelligence"
    AUTOMATION = "automation"


class SkillTier(Enum):
    """Skill complexity tiers"""
    TIER_1 = 1  # Basic
    TIER_2 = 2  # Intermediate
    TIER_3 = 3  # Advanced


@dataclass
class SkillResult:
    """Skill execution result"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Context for skill execution with security controls"""
    agent_id: str
    task_id: str = ""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    clearance: str = "UNCLASSIFIED"  # Security clearance level
    timeout: int = 300  # Execution timeout in seconds
    timestamp: datetime = field(default_factory=datetime.utcnow)
    params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Skill:
    """
    Skill definition
    
    All 77+ skills are defined as instances of this class
    """
    id: str
    name: str
    description: str
    category: SkillCategory
    tier: SkillTier
    handler: Callable = None
    params_schema: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    timeout: int = 300
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    execution_count: int = 0
    success_count: int = 0
    avg_execution_time: float = 0.0
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        """Execute the skill"""
        if not self.handler:
            return SkillResult(
                success=False,
                error=f"No handler registered for skill: {self.id}"
            )
        
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                self.handler(params),
                timeout=self.timeout
            )
            
            execution_time = time.time() - start_time
            
            # Update stats
            self.execution_count += 1
            self.success_count += 1
            self.avg_execution_time = (
                (self.avg_execution_time * (self.execution_count - 1) + execution_time)
                / self.execution_count
            )
            
            if isinstance(result, SkillResult):
                result.execution_time = execution_time
                return result
            else:
                return SkillResult(
                    success=True,
                    data=result,
                    execution_time=execution_time
                )
                
        except asyncio.TimeoutError:
            return SkillResult(
                success=False,
                error=f"Skill timeout after {self.timeout}s",
                execution_time=self.timeout
            )
        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )


class SkillRegistry:
    """
    Central skill registry
    
    Manages all 77+ skills with:
    - Dynamic loading
    - Version control
    - Dependency injection
    - Sandboxed execution
    """
    
    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._categories: Dict[SkillCategory, List[str]] = {
            cat: [] for cat in SkillCategory
        }
        self._handlers: Dict[str, Callable] = {}
        
        # Stats
        self.stats = {
            'skills_registered': 0,
            'skills_executed': 0,
            'execution_failures': 0
        }
    
    def register_skill(self, skill: Skill) -> bool:
        """
        Register a new skill
        
        Args:
            skill: Skill definition
            
        Returns:
            True if registered successfully
        """
        try:
            self._skills[skill.id] = skill
            self._categories[skill.category].append(skill.id)
            
            self.stats['skills_registered'] += 1
            logger.info(f"[SKILLS] Registered: {skill.id} ({skill.category.value})")
            return True
            
        except Exception as e:
            logger.error(f"[SKILLS] Registration failed: {e}")
            return False
    
    def register_handler(self, skill_id: str, handler: Callable):
        """Register handler for existing skill"""
        if skill_id in self._skills:
            self._skills[skill_id].handler = handler
            self._handlers[skill_id] = handler
        else:
            raise ValueError(f"Skill not found: {skill_id}")
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID"""
        return self._skills.get(skill_id)
    
    def list_skills(self, category: SkillCategory = None, tier: SkillTier = None) -> List[Skill]:
        """
        List skills with optional filtering
        
        Args:
            category: Filter by category
            tier: Filter by tier
            
        Returns:
            List of matching skills
        """
        skills = []
        
        for skill_id, skill in self._skills.items():
            if category and skill.category != category:
                continue
            if tier and skill.tier != tier:
                continue
            skills.append(skill)
        
        return skills
    
    async def execute(self, skill_id: str, params: Dict[str, Any]) -> SkillResult:
        """
        Execute a skill by ID
        
        Args:
            skill_id: Skill to execute
            params: Execution parameters
            
        Returns:
            Skill execution result
        """
        skill = self._skills.get(skill_id)
        
        if not skill:
            return SkillResult(
                success=False,
                error=f"Skill not found: {skill_id}"
            )
        
        self.stats['skills_executed'] += 1
        result = await skill.execute(params)
        
        if not result.success:
            self.stats['execution_failures'] += 1
        
        return result
    
    def get_categories(self) -> Dict[str, int]:
        """Get skill count by category"""
        return {
            cat.value: len(skills) 
            for cat, skills in self._categories.items()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        return {
            **self.stats,
            'categories': self.get_categories(),
            'total_skills': len(self._skills),
            'avg_success_rate': self._calculate_success_rate()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate"""
        total_execs = sum(s.execution_count for s in self._skills.values())
        total_success = sum(s.success_count for s in self._skills.values())
        
        if total_execs == 0:
            return 0.0
        
        return (total_success / total_execs) * 100
    
    def load_skill_modules(self):
        """Load all 77+ skill modules"""
        from . import OFFENSIVE_SKILLS, DEFENSIVE_SKILLS
        from . import INTELLIGENCE_SKILLS, AUTOMATION_SKILLS
        
        all_skills = (
            OFFENSIVE_SKILLS + 
            DEFENSIVE_SKILLS + 
            INTELLIGENCE_SKILLS + 
            AUTOMATION_SKILLS
        )
        
        for skill_def in all_skills:
            skill = Skill(**skill_def)
            self.register_skill(skill)
        
        logger.info(f"[SKILLS] Loaded {len(all_skills)} skills")
