from __future__ import annotations

from dataclasses import dataclass
import json

from app.security import Principal


CLEARANCE_ORDER = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
}

ROLE_ACTIONS: dict[str, set[str]] = {
    "board_member": {"read_project", "approve_message", "dispatch", "manage_seats", "manage_extensions", "admin"},
    "officer": {"read_project", "approve_message", "dispatch", "manage_seats", "manage_extensions"},
    "architect": {"read_project", "write_message", "request_review", "dispatch"},
    "engineer": {"read_project", "write_message", "request_review"},
    "operator": {"read_project", "dispatch", "worker_action"},
    "auditor": {"read_project", "read_audit"},
}


@dataclass
class AuthorizationResult:
    decision: str
    reason_codes: list[str]

    def as_json(self) -> str:
        return json.dumps(
            {
                "decision": self.decision,
                "reason_codes": self.reason_codes,
            },
            sort_keys=True,
        )


def _clearance_ok(principal_clearance: str, required_clearance: str) -> bool:
    return CLEARANCE_ORDER.get(principal_clearance, -1) >= CLEARANCE_ORDER.get(required_clearance, 999)


def _roles_allow(principal_roles: list[str], action: str) -> bool:
    for role in principal_roles:
        allowed = ROLE_ACTIONS.get(role, set())
        if action in allowed or "admin" in allowed:
            return True
    return False


def evaluate_authorization(
    principal: Principal,
    *,
    action: str,
    required_clearance: str = "internal",
    required_compartments: list[str] | None = None,
    high_risk: bool = False,
) -> AuthorizationResult:
    reasons: list[str] = []

    if not _roles_allow(principal.roles, action):
        reasons.append("role_not_permitted")
        return AuthorizationResult(decision="deny", reason_codes=reasons)

    if not _clearance_ok(principal.clearance_tier, required_clearance):
        reasons.append("insufficient_clearance")
        return AuthorizationResult(decision="deny", reason_codes=reasons)

    req_comp = required_compartments or []
    if req_comp:
        missing = sorted(set(req_comp) - set(principal.compartments))
        if missing:
            reasons.append("compartment_missing")
            return AuthorizationResult(decision="deny", reason_codes=reasons)

    if high_risk and not any(r in {"officer", "board_member"} for r in principal.roles):
        reasons.append("requires_officer_review")
        return AuthorizationResult(decision="hold", reason_codes=reasons)

    reasons.append("policy_allow")
    return AuthorizationResult(decision="allow", reason_codes=reasons)

