# ORDL Platform (Clean-Room)

This module is a clean-room enterprise fleet platform implementation.

## Scope in this implementation

- FastAPI backend with governance, authorization, policy-token, dispatch, extension-signing, worker actions, audit, and code-digestion APIs.
- React TypeScript control UI shell.
- Podman Compose runtime with Postgres, Valkey, MinIO, backend, worker, and frontend.
- Test suite covering authorization, workflow transitions, policy no-bypass, multi-tenant isolation, extension signatures, and digestion coverage.

## Run Backend

```powershell
cd ordl_platform/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
python -m uvicorn app.main:app --reload --port 8891
```

## Run Frontend

```powershell
cd ordl_platform/frontend
npm install
npm run dev
```

## Run Stack (Podman Compose)

```powershell
cd ordl_platform/infra
podman-compose -f podman-compose.yml up --build
```

## Security posture defaults

- RBAC + ABAC decision model.
- 4-tier clearance model with compartments.
- Signed policy token required for provider dispatch.
- Signed extension registration.
- Zero-trust ingress default with policy-controlled override capability.

## Standards bootstrap

Seed adopted standards (MCP, A2A, WebMCP) into a fresh tenant registry:

```powershell
powershell -ExecutionPolicy Bypass -File ordl_platform\scripts\bootstrap-adopted-standards.ps1
```

## ORDL pilot bootstrap

Provision ORDL pilot org/team/project and users:

```powershell
powershell -ExecutionPolicy Bypass -File ordl_platform\scripts\bootstrap-ordl-pilot.ps1
```

## Release gate

Run backend tests, fleet tests, and frontend build before shipping:

```powershell
powershell -ExecutionPolicy Bypass -File ordl_platform\scripts\release-gate.ps1
```

## Production-first pipeline

See:
- [deployment-first-pipeline.md](/C:/Users/Winsock/Documents/GitHub/ordl-phetamines/ordl_platform/docs/deployment-first-pipeline.md)
- `ordl_platform/infra/podman-compose.prod.yml`
- `ordl_platform/infra/.env.prod.example`
