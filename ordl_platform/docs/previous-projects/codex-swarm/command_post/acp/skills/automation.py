#!/usr/bin/env python3
"""
Automation Skills - 7 Skills
Workflow automation, reporting, integration
"""

AUTOMATION_SKILLS = [
    {
        "id": "auto_report",
        "name": "Report Generation",
        "description": "Generate penetration test reports",
        "category": "automation",
        "tier": 1,
        "params_schema": {
            "template": {"type": "string", "default": "executive"},
            "findings": {"type": "list", "required": True},
            "format": {"type": "string", "default": "pdf"},
            "classification": {"type": "string", "default": "CONFIDENTIAL"}
        }
    },
    {
        "id": "auto_scope",
        "name": "Scope Validation",
        "description": "Validate penetration test scope",
        "category": "automation",
        "tier": 1,
        "params_schema": {
            "targets": {"type": "list", "required": True},
            "rules_of_engagement": {"type": "string", "default": ""},
            "verify_ownership": {"type": "boolean", "default": True}
        }
    },
    {
        "id": "auto_workflow",
        "name": "Workflow Orchestration",
        "description": "Chain multiple skills into workflows",
        "category": "automation",
        "tier": 2,
        "params_schema": {
            "workflow": {"type": "string", "required": True},
            "parameters": {"type": "dict", "default": {}},
            "parallel": {"type": "boolean", "default": False}
        }
    },
    {
        "id": "auto_notify",
        "name": "Alert Notification",
        "description": "Send alerts via multiple channels",
        "category": "automation",
        "tier": 1,
        "params_schema": {
            "message": {"type": "string", "required": True},
            "severity": {"type": "string", "default": "info"},
            "channels": {"type": "list", "default": ["email"]},
            "recipients": {"type": "list", "required": True}
        }
    },
    {
        "id": "auto_ticket",
        "name": "Ticketing Integration",
        "description": "Create and update tickets",
        "category": "automation",
        "tier": 2,
        "params_schema": {
            "system": {"type": "string", "default": "jira"},
            "action": {"type": "string", "default": "create"},
            "data": {"type": "dict", "required": True}
        }
    },
    {
        "id": "auto_api",
        "name": "API Integration",
        "description": "Generic API connector",
        "category": "automation",
        "tier": 2,
        "params_schema": {
            "endpoint": {"type": "string", "required": True},
            "method": {"type": "string", "default": "GET"},
            "headers": {"type": "dict", "default": {}},
            "data": {"type": "dict", "default": {}}
        }
    },
    {
        "id": "auto_schedule",
        "name": "Task Scheduling",
        "description": "Schedule recurring security tasks",
        "category": "automation",
        "tier": 2,
        "params_schema": {
            "task": {"type": "string", "required": True},
            "schedule": {"type": "string", "required": True},
            "parameters": {"type": "dict", "default": {}}
        }
    }
]
