# ORDL Platform Backend

Clean-room FastAPI backend for the ORDL fleet governance platform.

## Run (dev)

```powershell
cd ordl_platform\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload --port 8891
```

## Test

```powershell
pytest
```

## Protocol bootstrap

Seed adopted standards (MCP, A2A, WebMCP):

```powershell
powershell -ExecutionPolicy Bypass -File ..\scripts\bootstrap-adopted-standards.ps1
```

## Production identity and secrets

Backend supports:
- OIDC token validation via JWKS (`ORDL_OIDC_*` settings).
- Vault-backed secret resolution for provider credentials (`ORDL_SECRET_BACKEND=vault`).

For local bootstrap, local JWT issuer remains available unless disabled:
- `ORDL_OIDC_REQUIRED=true`
- `ORDL_ALLOW_LOCAL_TOKEN_ISSUER=false`
