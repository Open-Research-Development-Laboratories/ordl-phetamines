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
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
