# ORDL First Deployment Pipeline (Production-First)

Status: Approved baseline (2026-03-06)

## Decisions locked

- Organization: Open Research and Development Laboratories (ORDL)
- Pilot principals:
  - Aaron Ferguson (`aferguson@ordl.org`) - CEO/CTO
  - Dustin Stroup (`dstroup@ordl.org`) - Debugger/Tester
- Secrets: Vault-first (`ORDL_SECRET_BACKEND=vault`)
- Identity: OIDC federation enabled (provider-agnostic; Keycloak/Entra/Auth0 compatible)
- Provider strategy: broad support now, not narrow support later.

## Why this pipeline

- Minimizes rework by enabling identity/secrets/provider abstraction from day one.
- Keeps local bootstrap simple while preserving production controls.
- Aligns with NIST-style control mapping using evidence artifacts and deterministic release gates.

## Deployment topology (v1)

1. Edge access and ingress
- Cloudflare Tunnel + Access (private ingress and policy gating).

2. Core platform
- ORDL backend API
- ORDL frontend
- Postgres
- Valkey
- Object storage (S3-compatible)

3. Security services
- Vault for runtime secrets
- OIDC identity provider

4. Fleet control plane
- Fleet API orchestration layer
- Worker nodes (build laptop + batch server + future nodes)

## Required backend settings (prod profile)

- `ORDL_ENVIRONMENT=production`
- `ORDL_SECRET_BACKEND=vault`
- `ORDL_VAULT_URL=...`
- `ORDL_VAULT_TOKEN_ENV_VAR=VAULT_TOKEN`
- `ORDL_VAULT_KV_MOUNT=secret`
- `ORDL_VAULT_KV_PATH=ordl`
- `ORDL_OIDC_ENABLED=true`
- `ORDL_OIDC_REQUIRED=true`
- `ORDL_OIDC_ISSUER=...`
- `ORDL_OIDC_JWKS_URL=...`
- `ORDL_OIDC_AUDIENCE=...`
- `ORDL_ALLOW_LOCAL_TOKEN_ISSUER=false`

## Vault key contract

At `mount=secret`, `path=ordl`, provision:

- `OPENAI_API_KEY`
- `KIMI_TOKEN`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `XAI_API_KEY`
- `MISTRAL_API_KEY`
- `GROQ_API_KEY`
- `TOGETHER_API_KEY`
- `PERPLEXITY_API_KEY`
- `DEEPSEEK_API_KEY`
- `AWS_REGION`
- `OPENROUTER_API_KEY`

## Release gates (must pass)

1. Backend tests green.
2. Fleet API tests green.
3. Frontend production build green.
4. Adopted standards registry bootstrapped.
5. Protocol compatibility check pass for core standards.
6. Fleet health green (`ok=true`) before traffic enablement.

## Operator sequence

1. Run release gate:
   - `powershell -ExecutionPolicy Bypass -File ordl_platform/scripts/release-gate.ps1`
2. Run sneak-preview preflight (env validation + compose validation + fleet pairing gate):
   - `powershell -ExecutionPolicy Bypass -File ordl_platform/scripts/sneak-preview-preflight.ps1 -InitEnvFile`
   - Copy `ordl_platform/infra/.env.prod.example` to local `ordl_platform/infra/.env.prod`
   - Fill `ordl_platform/infra/.env.prod`
   - Re-run:
   - `powershell -ExecutionPolicy Bypass -File ordl_platform/scripts/sneak-preview-preflight.ps1`
   - For immediate local sneak preview (no container runtime required):
   - `powershell -ExecutionPolicy Bypass -File ordl_platform/scripts/launch-sneak-preview-local.ps1`
3. Start production stack profile.
4. Bootstrap ORDL pilot principals and tenant/project.
5. Bootstrap adopted standards.
6. Validate protocol compatibility + conformance runs.
7. Enable external ingress policy.

## Local no-dependency bootstrap mode

If you want zero external dependencies for initial bring-up:

- `podman-compose -f ordl_platform/infra/podman-compose.prod.yml --profile local-vault --profile local-idp up --build -d`

This starts:
- local Vault (dev mode) at `http://127.0.0.1:8200`
- local Keycloak (dev mode) at `http://127.0.0.1:8080`

For production, replace both with hardened managed services and keep the same backend interfaces.

## Current hardening gap list (next sprint)

- OIDC login UI and authorization-code flow endpoints.
- Vault auth via AppRole/Kubernetes auth (replace static token).
- Signed extension verification with asymmetric trust roots.
- Automated evidence bundle export for audit and control verification.
