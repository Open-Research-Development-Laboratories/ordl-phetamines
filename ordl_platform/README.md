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
