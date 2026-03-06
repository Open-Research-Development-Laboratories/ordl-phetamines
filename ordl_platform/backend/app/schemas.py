from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    tenant_name: str
    email: str
    display_name: str = ""
    roles: list[str] = Field(default_factory=lambda: ["engineer"])
    clearance_tier: str = "internal"
    compartments: list[str] = Field(default_factory=list)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str


class TenantCreate(BaseModel):
    name: str
    tenant_type: str = "organization"


class TenantOut(BaseModel):
    id: str
    name: str
    tenant_type: str


class OrgCreate(BaseModel):
    tenant_id: str
    name: str


class OrgOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    owner_user_id: str
    board_scope_mode: str


class TeamCreate(BaseModel):
    org_id: str
    name: str


class TeamOut(BaseModel):
    id: str
    org_id: str
    name: str


class ProjectCreate(BaseModel):
    team_id: str
    code: str
    name: str
    ingress_mode: str = "zero_trust"
    visibility_mode: str = "scoped"


class ProjectOut(BaseModel):
    id: str
    team_id: str
    code: str
    name: str
    ingress_mode: str
    visibility_mode: str


class SeatCreate(BaseModel):
    project_id: str
    user_id: str
    role: str
    rank: str = "member"
    position: str = ""
    group_name: str = ""
    clearance_tier: str = "internal"
    compartments: list[str] = Field(default_factory=list)
    status: str = "active"


class SeatOut(BaseModel):
    id: str
    project_id: str
    user_id: str
    role: str
    rank: str
    position: str
    group_name: str
    clearance_tier: str
    compartments: list[str]
    status: str


class ClearanceEvaluateRequest(BaseModel):
    action: str
    required_clearance: str = "internal"
    required_compartments: list[str] = Field(default_factory=list)
    high_risk: bool = False


class AuthorizationDecisionOut(BaseModel):
    decision: str
    reason_codes: list[str]


class MessageCreate(BaseModel):
    project_id: str
    title: str
    body: str
    reviewer_user_id: str | None = None
    parent_message_id: str | None = None


class MessageUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    review_notes: str | None = None


class MessageTransition(BaseModel):
    target_state: str
    review_notes: str = ""


class MessageOut(BaseModel):
    id: str
    project_id: str
    author_user_id: str
    reviewer_user_id: str | None
    title: str
    body: str
    state: str
    revision: int
    parent_message_id: str | None
    review_notes: str


class ApprovalCreate(BaseModel):
    project_id: str
    message_id: str
    decision: str = "approved"
    rationale: str = ""


class ApprovalOut(BaseModel):
    id: str
    project_id: str
    message_id: str
    reviewer_user_id: str
    decision: str
    rationale: str


class DispatchCreate(BaseModel):
    project_id: str
    message_id: str | None = None
    target_scope: Literal["group", "worker", "project", "team", "org"] = "group"
    target_value: str = "all"
    provider: Literal["openai_codex", "kimi"] = "openai_codex"
    model: str
    payload: dict[str, Any] = Field(default_factory=dict)


class DispatchOut(BaseModel):
    id: str
    project_id: str
    message_id: str | None
    target_scope: str
    target_value: str
    provider: str
    model: str
    request_hash: str
    state: str


class DispatchResultOut(BaseModel):
    id: str
    dispatch_request_id: str
    worker_id: str
    status: str
    provider_reference: str
    output: str
    error: str


class PolicyDecideRequest(BaseModel):
    project_id: str
    action: str
    resource_type: str
    resource_id: str
    payload: dict = Field(default_factory=dict)
    required_clearance: str = "internal"
    required_compartments: list[str] = Field(default_factory=list)
    high_risk: bool = False
    destination_scope: str = "project"


class PolicyDecideResponse(BaseModel):
    decision: str
    reason_codes: list[str]
    request_hash: str
    policy_token: str | None = None


class PolicyValidateRequest(BaseModel):
    token: str
    request_hash: str
    destination_scope: str


class ProviderCredentialUpsert(BaseModel):
    tenant_id: str
    provider: Literal["openai_codex", "kimi"]
    auth_mode: Literal["managed_secret", "oauth_supported"]
    configured: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtensionCreate(BaseModel):
    tenant_id: str
    name: str
    version: str
    scopes: list[str] = Field(default_factory=list)
    signature: str


class ExtensionOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    version: str
    scopes: list[str]
    status: str


class WorkerRegister(BaseModel):
    project_id: str
    name: str
    role: str
    host: str = ""
    device_id: str
    capabilities: list[str] = Field(default_factory=list)


class WorkerOut(BaseModel):
    id: str
    project_id: str
    name: str
    role: str
    host: str
    device_id: str
    status: str
    capabilities: list[str]


class WorkerActionRequest(BaseModel):
    action: str
    notes: str = ""


class DigestionRunRequest(BaseModel):
    project_id: str
    repo_root: str
    chunk_size: int = Field(default=200, ge=1, le=2000)
