from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORDL_", env_file=".env", extra="ignore")

    app_name: str = "ORDL Platform API"
    api_prefix: str = "/v1"
    environment: str = "development"

    database_url: str = "sqlite:///./ordl_platform.db"
    policy_secret: str = "ordl-dev-policy-secret-please-change-this-32b"
    auth_secret: str = "ordl-dev-auth-secret-please-change-this-32b"
    extension_signing_secret: str = "ordl-dev-extension-secret-please-change-this-32b"
    secret_backend: str = "env"
    vault_url: str = ""
    vault_token_env_var: str = "VAULT_TOKEN"
    vault_kv_mount: str = "secret"
    vault_kv_path: str = "ordl"

    oidc_enabled: bool = False
    oidc_required: bool = False
    oidc_issuer: str = ""
    oidc_jwks_url: str = ""
    oidc_audience: str = ""
    oidc_roles_claim: str = "roles"
    oidc_clearance_claim: str = "clearance_tier"
    oidc_compartments_claim: str = "compartments"
    oidc_tenant_claim: str = "tenant_id"
    oidc_subject_claim: str = "sub"
    oidc_email_claim: str = "email"
    allow_local_token_issuer: bool = True

    access_token_ttl_seconds: int = 3600
    policy_token_ttl_seconds: int = 300

    allowed_ingress_defaults: str = "zero_trust"
    storage_backend: str = "local"
    storage_bucket: str = "ordl-artifacts"
    storage_local_root: str = "./state/artifacts"

    @model_validator(mode="after")
    def validate_security_posture(self) -> "Settings":
        if self.environment.lower() not in {"production", "prod"}:
            return self

        weak_defaults = {
            "ordl-dev-policy-secret-please-change-this-32b",
            "ordl-dev-auth-secret-please-change-this-32b",
            "ordl-dev-extension-secret-please-change-this-32b",
        }

        secret_fields = {
            "policy_secret": self.policy_secret,
            "auth_secret": self.auth_secret,
            "extension_signing_secret": self.extension_signing_secret,
        }

        weak = [
            name
            for name, value in secret_fields.items()
            if value in weak_defaults or len(value) < 32
        ]
        if weak:
            field_list = ", ".join(sorted(weak))
            raise ValueError(
                f"production environment requires strong non-default secrets; fix: {field_list}"
            )

        if self.secret_backend not in {"env", "vault"}:
            raise ValueError("production environment requires secret_backend in {env,vault}")
        if self.secret_backend == "vault":
            if not self.vault_url:
                raise ValueError("production with secret_backend=vault requires vault_url")
            if not self.vault_token_env_var:
                raise ValueError("production with secret_backend=vault requires vault_token_env_var")

        if self.oidc_required:
            if not self.oidc_enabled:
                raise ValueError("oidc_required=true requires oidc_enabled=true")
            required_oidc_fields = {
                "oidc_issuer": self.oidc_issuer,
                "oidc_jwks_url": self.oidc_jwks_url,
                "oidc_audience": self.oidc_audience,
            }
            missing = [name for name, value in required_oidc_fields.items() if not value]
            if missing:
                raise ValueError(f"oidc_required=true missing fields: {', '.join(sorted(missing))}")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
