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

Optionally include a Flask faceplate revision audit (strict `url_for` + TODO + `/api/*` checks):

```powershell
powershell -ExecutionPolicy Bypass -File ordl_platform\scripts\release-gate.ps1 -FlaskRevisionPath "C:\path\to\revision-8-flask-app"
```

## /v1 API contract artifact

Generate backend `/v1` source-of-truth route artifacts used for frontend wiring:

```powershell
python ordl_platform\scripts\generate-v1-contract.py
```

Outputs:

- `ordl_platform/docs/contracts/api-v1-contract.json`
- `ordl_platform/docs/contracts/api-v1-routes.md`

## OpenAI alignment artifacts

Generate URL manifest and adoption backlog from the OpenAI research report:

```powershell
python ordl_platform\scripts\build-openai-alignment-manifest.py --input ordl_platform\docs\research\openai_developers_comprehensive_report.md
```

Outputs:

- `ordl_platform/docs/research/openai-url-manifest.json`
- `ordl_platform/docs/research/openai-adoption-backlog.md`

Validate OpenAI standards implementation (artifact presence, adapter alignment, dialect lint, release-gate wiring):

```powershell
python ordl_platform\scripts\validate-openai-standards.py
```

Output:

- `ordl_platform/state/reports/openai-standards-validation.json`

## Revision 8 contract review

Compare `revision-8` frontend contract matrix against actual backend `/v1` routes:

```powershell
python ordl_platform\scripts\review-revision8-contract.py --matrix ordl_platform\docs\faceplate\revision-8-js-files\ORDL_CONTRACT_MATRIX.md
```

Outputs:

- `ordl_platform/state/reports/revision-8-contract-review.json`
- `ordl_platform/docs/faceplate/revision-8-js-files/REVISION_8_CONTRACT_REVIEW.md`

## Markdown instruction dialect lint

Lint instruction markdown files against ORDL OpenAI dialect sections:

```powershell
python ordl_platform\scripts\lint-md-instruction-dialect.py ordl_platform\docs\templates
```

## Production-first pipeline

See:

- [deployment-first-pipeline.md](/C:/Users/Winsock/Documents/GitHub/ordl-phetamines/ordl_platform/docs/deployment-first-pipeline.md)
- `ordl_platform/infra/podman-compose.prod.yml`
- `ordl_platform/infra/.env.prod.example`
