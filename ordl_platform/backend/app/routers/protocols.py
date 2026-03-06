from __future__ import annotations

import json
import re
from datetime import timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import append_audit_event, build_actor_snapshot
from app.authz import evaluate_authorization
from app.common import ensure_project_scope, ensure_tenant_scope, json_list
from app.db import get_db
from app.models import (
    ProtocolConformanceRun,
    ProtocolStandard,
    ProtocolStandardVersion,
)
from app.schemas import (
    ProtocolBootstrapOut,
    ProtocolBootstrapRequest,
    ProtocolCompatibilityItemOut,
    ProtocolCompatibilityOut,
    ProtocolConformanceRunCreate,
    ProtocolConformanceRunOut,
    ProtocolStandardCreate,
    ProtocolStandardOut,
    ProtocolStandardVersionCreate,
    ProtocolStandardVersionOut,
    ProtocolValidateItemOut,
    ProtocolValidateOut,
    ProtocolValidateRequest,
)
from app.security import Principal, get_current_principal

router = APIRouter(prefix="/protocols", tags=["protocols"])

_VERSION_TOKEN = re.compile(r"\d+")
_ADOPTED_PROTOCOLS: tuple[dict[str, Any], ...] = (
    {
        "code": "mcp",
        "name": "Model Context Protocol",
        "domain": "agent_to_tool",
        "steward": "Agentic AI Foundation",
        "home_url": "https://modelcontextprotocol.io/",
        "status": "adopted",
        "adoption_tier": "core",
        "description": "Open protocol for connecting AI applications to tools, data, and workflows.",
        "tags": ["mcp", "agent", "tooling"],
        "source_urls": [
            "https://modelcontextprotocol.io/",
            "https://blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation/",
        ],
        "versions": [
            {
                "version": "2026.03",
                "lifecycle_status": "adopted",
                "specification_url": "https://modelcontextprotocol.io/specification/",
                "schema_uri": "",
                "required_by_default": True,
                "change_notes": "Baseline ORDL enterprise requirement.",
                "compatibility": {"transport": ["stdio", "http"]},
            }
        ],
    },
    {
        "code": "a2a",
        "name": "Agent2Agent",
        "domain": "agent_to_agent",
        "steward": "Linux Foundation",
        "home_url": "https://github.com/a2aproject/A2A",
        "status": "adopted",
        "adoption_tier": "core",
        "description": "Protocol for secure agent-to-agent interoperability across frameworks and vendors.",
        "tags": ["a2a", "interoperability", "multi-agent"],
        "source_urls": [
            "https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/",
            "https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents",
            "https://github.com/a2aproject/A2A",
        ],
        "versions": [
            {
                "version": "0.2.0",
                "lifecycle_status": "adopted",
                "specification_url": "https://github.com/a2aproject/A2A/tree/main/specification",
                "schema_uri": "",
                "required_by_default": True,
                "change_notes": "Current adopted baseline for ORDL fleet interop.",
                "compatibility": {"transport": ["json-rpc-2.0-http", "sse"]},
            }
        ],
    },
    {
        "code": "webmcp",
        "name": "WebMCP",
        "domain": "web_agent_tools",
        "steward": "WebML / browser ecosystem",
        "home_url": "https://github.com/webmachinelearning/webmcp",
        "status": "adopted",
        "adoption_tier": "recommended",
        "description": "Browser/web capability surface for agent tool usage.",
        "tags": ["webmcp", "browser", "agentic-web"],
        "source_urls": [
            "https://developer.chrome.com/blog/webmcp-epp",
            "https://github.com/webmachinelearning/webmcp",
        ],
        "versions": [
            {
                "version": "2026.02-epp",
                "lifecycle_status": "draft",
                "specification_url": "https://github.com/webmachinelearning/webmcp",
                "schema_uri": "",
                "required_by_default": False,
                "change_notes": "Early preview support for browser agent tooling.",
                "compatibility": {"maturity": "early_preview"},
            }
        ],
    },
)


def _dump_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load_json_dict(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _version_rank(version: str) -> tuple[int, ...]:
    parts = [int(token) for token in _VERSION_TOKEN.findall(version or "")]
    return tuple(parts)


def _version_at_least(evaluated: str | None, minimum: str | None) -> bool:
    if not minimum:
        return True
    if not evaluated:
        return False
    ev_rank = _version_rank(evaluated)
    min_rank = _version_rank(minimum)
    if ev_rank and min_rank:
        max_len = max(len(ev_rank), len(min_rank))
        ev_padded = ev_rank + (0,) * (max_len - len(ev_rank))
        min_padded = min_rank + (0,) * (max_len - len(min_rank))
        return ev_padded >= min_padded
    return evaluated >= minimum


def _latest_standard_version(db: Session, standard_id: str) -> ProtocolStandardVersion | None:
    return db.scalar(
        select(ProtocolStandardVersion)
        .where(ProtocolStandardVersion.standard_id == standard_id)
        .order_by(ProtocolStandardVersion.created_at.desc())
        .limit(1)
    )


def _standard_out(db: Session, row: ProtocolStandard) -> ProtocolStandardOut:
    latest = _latest_standard_version(db, row.id)
    return ProtocolStandardOut(
        id=row.id,
        tenant_id=row.tenant_id,
        code=row.code,
        name=row.name,
        domain=row.domain,
        steward=row.steward,
        home_url=row.home_url,
        status=row.status,
        adoption_tier=row.adoption_tier,
        description=row.description,
        tags=json_list(row.tags_json),
        source_urls=json_list(row.source_urls_json),
        latest_version=latest.version if latest else None,
    )


def _version_out(row: ProtocolStandardVersion) -> ProtocolStandardVersionOut:
    return ProtocolStandardVersionOut(
        id=row.id,
        standard_id=row.standard_id,
        version=row.version,
        lifecycle_status=row.lifecycle_status,
        specification_url=row.specification_url,
        schema_uri=row.schema_uri,
        required_by_default=bool(row.required_by_default),
        change_notes=row.change_notes,
        compatibility=_load_json_dict(row.compatibility_json),
        released_at=row.released_at.astimezone(timezone.utc).isoformat() if row.released_at else None,
        deprecated_at=row.deprecated_at.astimezone(timezone.utc).isoformat() if row.deprecated_at else None,
    )


def _conformance_out(row: ProtocolConformanceRun) -> ProtocolConformanceRunOut:
    return ProtocolConformanceRunOut(
        id=row.id,
        project_id=row.project_id,
        standard_id=row.standard_id,
        standard_version_id=row.standard_version_id,
        suite_name=row.suite_name,
        target_scope=row.target_scope,
        status=row.status,
        score=row.score,
        findings=json_list(row.findings_json),
        evidence_refs=json_list(row.evidence_refs_json),
        run_metadata=_load_json_dict(row.run_metadata_json),
        created_at=row.created_at.astimezone(timezone.utc).isoformat(),
    )


def _authorize_manage_protocols(principal: Principal) -> None:
    auth = evaluate_authorization(principal, action="manage_extensions")
    if auth.decision != "allow":
        raise HTTPException(status_code=403, detail=f"protocol management denied: {auth.reason_codes}")


def _authorize_record_conformance(principal: Principal) -> None:
    auth = evaluate_authorization(principal, action="dispatch")
    if auth.decision == "deny":
        raise HTTPException(status_code=403, detail=f"conformance record denied: {auth.reason_codes}")


def _find_standard_by_code(db: Session, tenant_id: str, code: str) -> ProtocolStandard | None:
    return db.scalar(
        select(ProtocolStandard).where(
            ProtocolStandard.tenant_id == tenant_id,
            ProtocolStandard.code == code,
        )
    )


@router.post("/bootstrap/adopted", response_model=ProtocolBootstrapOut)
def bootstrap_adopted_protocols(
    payload: ProtocolBootstrapRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProtocolBootstrapOut:
    ensure_tenant_scope(db, principal)
    _authorize_manage_protocols(principal)

    created_standards: list[str] = []
    existing_standards: list[str] = []
    created_versions: list[str] = []

    for protocol in _ADOPTED_PROTOCOLS:
        code = str(protocol["code"])
        standard = _find_standard_by_code(db, principal.tenant_id, code)
        if standard is None:
            standard = ProtocolStandard(
                tenant_id=principal.tenant_id,
                code=code,
                name=str(protocol.get("name", code.upper())),
                domain=str(protocol.get("domain", "general")),
                steward=str(protocol.get("steward", "")),
                home_url=str(protocol.get("home_url", "")),
                status=str(protocol.get("status", "adopted")),
                adoption_tier=str(protocol.get("adoption_tier", "recommended")),
                description=str(protocol.get("description", "")),
                tags_json=_dump_json(protocol.get("tags", [])),
                source_urls_json=_dump_json(protocol.get("source_urls", [])),
                created_by_user_id=principal.user_id,
            )
            db.add(standard)
            db.flush()
            created_standards.append(code)
        else:
            existing_standards.append(code)
            if payload.overwrite_existing:
                standard.name = str(protocol.get("name", standard.name))
                standard.domain = str(protocol.get("domain", standard.domain))
                standard.steward = str(protocol.get("steward", standard.steward))
                standard.home_url = str(protocol.get("home_url", standard.home_url))
                standard.status = str(protocol.get("status", standard.status))
                standard.adoption_tier = str(protocol.get("adoption_tier", standard.adoption_tier))
                standard.description = str(protocol.get("description", standard.description))
                standard.tags_json = _dump_json(protocol.get("tags", []))
                standard.source_urls_json = _dump_json(protocol.get("source_urls", []))

        if not payload.include_versions:
            continue

        for version in protocol.get("versions", []):
            version_value = str(version.get("version", "")).strip()
            if not version_value:
                continue
            existing_version = db.scalar(
                select(ProtocolStandardVersion).where(
                    ProtocolStandardVersion.standard_id == standard.id,
                    ProtocolStandardVersion.version == version_value,
                )
            )
            if existing_version is not None:
                if payload.overwrite_existing:
                    existing_version.lifecycle_status = str(version.get("lifecycle_status", existing_version.lifecycle_status))
                    existing_version.specification_url = str(version.get("specification_url", existing_version.specification_url))
                    existing_version.schema_uri = str(version.get("schema_uri", existing_version.schema_uri))
                    existing_version.required_by_default = 1 if bool(version.get("required_by_default", False)) else 0
                    existing_version.change_notes = str(version.get("change_notes", existing_version.change_notes))
                    existing_version.compatibility_json = _dump_json(version.get("compatibility", {}))
                continue

            created_version = ProtocolStandardVersion(
                standard_id=standard.id,
                version=version_value,
                lifecycle_status=str(version.get("lifecycle_status", "adopted")),
                specification_url=str(version.get("specification_url", "")),
                schema_uri=str(version.get("schema_uri", "")),
                required_by_default=1 if bool(version.get("required_by_default", False)) else 0,
                change_notes=str(version.get("change_notes", "")),
                compatibility_json=_dump_json(version.get("compatibility", {})),
                created_by_user_id=principal.user_id,
            )
            db.add(created_version)
            db.flush()
            created_versions.append(f"{code}:{version_value}")

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=None,
        event_type="protocol.bootstrap.adopted",
        payload={
            "created_standards": created_standards,
            "existing_standards": existing_standards,
            "created_versions": created_versions,
            "overwrite_existing": payload.overwrite_existing,
            "include_versions": payload.include_versions,
        },
        actor=build_actor_snapshot(db, principal),
        resource={"resource_type": "protocol_registry", "resource_id": "adopted_bootstrap"},
    )
    db.commit()
    return ProtocolBootstrapOut(
        created_standards=created_standards,
        existing_standards=existing_standards,
        created_versions=created_versions,
    )


@router.post("/standards", response_model=ProtocolStandardOut)
def create_protocol_standard(
    payload: ProtocolStandardCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProtocolStandardOut:
    ensure_tenant_scope(db, principal)
    _authorize_manage_protocols(principal)

    existing = _find_standard_by_code(db, principal.tenant_id, payload.code)
    if existing is not None:
        raise HTTPException(status_code=409, detail="protocol standard code already exists for tenant")

    row = ProtocolStandard(
        tenant_id=principal.tenant_id,
        code=payload.code,
        name=payload.name,
        domain=payload.domain,
        steward=payload.steward,
        home_url=payload.home_url,
        status=payload.status,
        adoption_tier=payload.adoption_tier,
        description=payload.description,
        tags_json=_dump_json(payload.tags),
        source_urls_json=_dump_json(payload.source_urls),
        created_by_user_id=principal.user_id,
    )
    db.add(row)
    db.flush()

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=None,
        event_type="protocol.standard.created",
        payload={
            "standard_id": row.id,
            "code": row.code,
            "name": row.name,
            "adoption_tier": row.adoption_tier,
        },
        actor=build_actor_snapshot(db, principal),
        resource={"resource_type": "protocol_standard", "resource_id": row.id},
    )
    db.commit()
    return _standard_out(db, row)


@router.get("/standards", response_model=list[ProtocolStandardOut])
def list_protocol_standards(
    status: str | None = Query(default=None),
    adoption_tier: str | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ProtocolStandardOut]:
    ensure_tenant_scope(db, principal)
    stmt = select(ProtocolStandard).where(ProtocolStandard.tenant_id == principal.tenant_id).order_by(ProtocolStandard.code.asc())
    if status:
        stmt = stmt.where(ProtocolStandard.status == status)
    if adoption_tier:
        stmt = stmt.where(ProtocolStandard.adoption_tier == adoption_tier)
    rows = db.scalars(stmt).all()
    return [_standard_out(db, row) for row in rows]


@router.post("/standards/{standard_id}/versions", response_model=ProtocolStandardVersionOut)
def create_protocol_standard_version(
    standard_id: str,
    payload: ProtocolStandardVersionCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProtocolStandardVersionOut:
    ensure_tenant_scope(db, principal)
    _authorize_manage_protocols(principal)

    standard = db.get(ProtocolStandard, standard_id)
    if standard is None:
        raise HTTPException(status_code=404, detail="standard not found")
    if standard.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail="tenant scope denied")

    existing = db.scalar(
        select(ProtocolStandardVersion).where(
            ProtocolStandardVersion.standard_id == standard_id,
            ProtocolStandardVersion.version == payload.version,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="standard version already exists")

    row = ProtocolStandardVersion(
        standard_id=standard_id,
        version=payload.version,
        lifecycle_status=payload.lifecycle_status,
        specification_url=payload.specification_url,
        schema_uri=payload.schema_uri,
        required_by_default=1 if payload.required_by_default else 0,
        change_notes=payload.change_notes,
        compatibility_json=_dump_json(payload.compatibility),
        created_by_user_id=principal.user_id,
    )
    db.add(row)
    db.flush()

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=None,
        event_type="protocol.standard_version.created",
        payload={
            "standard_id": standard.id,
            "standard_code": standard.code,
            "standard_version_id": row.id,
            "version": row.version,
            "required_by_default": bool(row.required_by_default),
        },
        actor=build_actor_snapshot(db, principal),
        resource={"resource_type": "protocol_standard_version", "resource_id": row.id},
    )
    db.commit()
    return _version_out(row)


@router.get("/standards/{standard_id}/versions", response_model=list[ProtocolStandardVersionOut])
def list_protocol_standard_versions(
    standard_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ProtocolStandardVersionOut]:
    ensure_tenant_scope(db, principal)
    standard = db.get(ProtocolStandard, standard_id)
    if standard is None:
        raise HTTPException(status_code=404, detail="standard not found")
    if standard.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail="tenant scope denied")

    rows = db.scalars(
        select(ProtocolStandardVersion)
        .where(ProtocolStandardVersion.standard_id == standard_id)
        .order_by(ProtocolStandardVersion.created_at.desc())
    ).all()
    return [_version_out(row) for row in rows]


@router.get("/compatibility", response_model=ProtocolCompatibilityOut)
def get_protocol_compatibility(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProtocolCompatibilityOut:
    ensure_project_scope(db, principal, project_id)

    standards = db.scalars(
        select(ProtocolStandard)
        .where(ProtocolStandard.tenant_id == principal.tenant_id)
        .order_by(ProtocolStandard.code.asc())
    ).all()

    items: list[ProtocolCompatibilityItemOut] = []
    for standard in standards:
        latest = _latest_standard_version(db, standard.id)
        required = bool(standard.adoption_tier == "core" or (latest and latest.required_by_default))
        last_run = db.scalar(
            select(ProtocolConformanceRun)
            .where(
                ProtocolConformanceRun.project_id == project_id,
                ProtocolConformanceRun.standard_id == standard.id,
            )
            .order_by(ProtocolConformanceRun.created_at.desc())
            .limit(1)
        )
        conformance_status = last_run.status if last_run else "none"
        reasons: list[str] = []
        if required and conformance_status != "pass":
            reasons.append("required_standard_not_passing")
        if conformance_status == "fail":
            reasons.append("latest_conformance_failed")
        compatible = len(reasons) == 0
        if not reasons:
            reasons.append("compatible")

        items.append(
            ProtocolCompatibilityItemOut(
                standard_id=standard.id,
                code=standard.code,
                name=standard.name,
                adoption_tier=standard.adoption_tier,
                latest_version=latest.version if latest else None,
                required=required,
                conformance_status=conformance_status,
                last_run_id=last_run.id if last_run else None,
                compatible=compatible,
                reasons=reasons,
            )
        )

    overall_compatible = all(item.compatible for item in items)
    return ProtocolCompatibilityOut(project_id=project_id, compatible=overall_compatible, items=items)


@router.post("/validate", response_model=ProtocolValidateOut)
def validate_protocol_requirements(
    payload: ProtocolValidateRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProtocolValidateOut:
    ensure_project_scope(db, principal, payload.project_id)

    requirements = list(payload.requirements)
    if not requirements:
        standards = db.scalars(
            select(ProtocolStandard).where(
                ProtocolStandard.tenant_id == principal.tenant_id,
                ProtocolStandard.adoption_tier == "core",
                ProtocolStandard.status != "deprecated",
            )
        ).all()
        requirements = [
            {
                "standard_code": row.code,
                "minimum_version": None,
                "required_tier": row.adoption_tier,
            }
            for row in standards
        ]

    items: list[ProtocolValidateItemOut] = []
    for requirement in requirements:
        if isinstance(requirement, dict):
            standard_code = requirement.get("standard_code", "")
            minimum_version = requirement.get("minimum_version")
        else:
            standard_code = requirement.standard_code
            minimum_version = requirement.minimum_version

        reasons: list[str] = []
        standard = _find_standard_by_code(db, principal.tenant_id, standard_code)
        if standard is None:
            items.append(
                ProtocolValidateItemOut(
                    standard_code=standard_code,
                    minimum_version=minimum_version,
                    evaluated_version=None,
                    result="fail",
                    reasons=["missing_standard"],
                )
            )
            continue

        latest = _latest_standard_version(db, standard.id)
        evaluated_version = latest.version if latest else None
        if latest is None:
            reasons.append("missing_standard_version")
        elif latest.lifecycle_status == "deprecated":
            reasons.append("latest_version_deprecated")

        if not _version_at_least(evaluated_version, minimum_version):
            reasons.append("minimum_version_not_met")

        result = "pass" if len(reasons) == 0 else "fail"
        if not reasons:
            reasons.append("validated")
        items.append(
            ProtocolValidateItemOut(
                standard_code=standard_code,
                minimum_version=minimum_version,
                evaluated_version=evaluated_version,
                result=result,
                reasons=reasons,
            )
        )

    ok = all(item.result == "pass" for item in items)
    return ProtocolValidateOut(project_id=payload.project_id, ok=ok, items=items)


@router.post("/conformance/runs", response_model=ProtocolConformanceRunOut)
def create_protocol_conformance_run(
    payload: ProtocolConformanceRunCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProtocolConformanceRunOut:
    ensure_project_scope(db, principal, payload.project_id)
    _authorize_record_conformance(principal)

    standard: ProtocolStandard | None = None
    if payload.standard_id:
        standard = db.get(ProtocolStandard, payload.standard_id)
    elif payload.standard_code:
        standard = _find_standard_by_code(db, principal.tenant_id, payload.standard_code)
    if standard is None:
        raise HTTPException(status_code=404, detail="standard not found")
    if standard.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail="tenant scope denied")

    standard_version: ProtocolStandardVersion | None = None
    if payload.standard_version_id:
        standard_version = db.get(ProtocolStandardVersion, payload.standard_version_id)
        if standard_version is None or standard_version.standard_id != standard.id:
            raise HTTPException(status_code=400, detail="standard_version_id does not belong to target standard")
    elif payload.standard_version:
        standard_version = db.scalar(
            select(ProtocolStandardVersion).where(
                ProtocolStandardVersion.standard_id == standard.id,
                ProtocolStandardVersion.version == payload.standard_version,
            )
        )
        if standard_version is None:
            raise HTTPException(status_code=404, detail="standard version not found")
    else:
        standard_version = _latest_standard_version(db, standard.id)

    row = ProtocolConformanceRun(
        project_id=payload.project_id,
        standard_id=standard.id,
        standard_version_id=standard_version.id if standard_version else None,
        suite_name=payload.suite_name,
        target_scope=payload.target_scope,
        status=payload.status,
        score=payload.score,
        findings_json=_dump_json(payload.findings),
        evidence_refs_json=_dump_json(payload.evidence_refs),
        run_metadata_json=_dump_json(payload.run_metadata),
        executed_by_user_id=principal.user_id,
    )
    db.add(row)
    db.flush()

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type="protocol.conformance_run.created",
        payload={
            "conformance_run_id": row.id,
            "standard_id": standard.id,
            "standard_code": standard.code,
            "standard_version_id": row.standard_version_id,
            "status": row.status,
            "score": row.score,
        },
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={"resource_type": "protocol_conformance_run", "resource_id": row.id},
        run_id=row.id,
        trace_id=row.id,
    )
    db.commit()
    return _conformance_out(row)


@router.get("/conformance/runs", response_model=list[ProtocolConformanceRunOut])
def list_protocol_conformance_runs(
    project_id: str,
    standard_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ProtocolConformanceRunOut]:
    ensure_project_scope(db, principal, project_id)
    stmt = (
        select(ProtocolConformanceRun)
        .where(ProtocolConformanceRun.project_id == project_id)
        .order_by(ProtocolConformanceRun.created_at.desc())
        .limit(limit)
    )
    if standard_id:
        stmt = stmt.where(ProtocolConformanceRun.standard_id == standard_id)
    rows = db.scalars(stmt).all()
    return [_conformance_out(row) for row in rows]
