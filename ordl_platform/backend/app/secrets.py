from __future__ import annotations

import os
from functools import lru_cache

from app.config import Settings, get_settings


class SecretResolutionError(RuntimeError):
    pass


def _normalize_secret_key(key: str) -> str:
    normalized = key.strip().upper().replace("-", "_").replace(".", "_")
    return normalized


class SecretResolver:
    def __init__(self, settings: Settings):
        self._settings = settings

    def get(self, key: str, *, default: str | None = None) -> str | None:
        backend = (self._settings.secret_backend or "env").strip().lower()
        if backend == "env":
            return self._get_from_env(key, default=default)
        if backend == "vault":
            try:
                return self._get_from_vault(key, default=default)
            except Exception as exc:
                raise SecretResolutionError(f"vault secret resolution failed for key={key}") from exc
        raise SecretResolutionError(f"unsupported secret backend: {backend}")

    def _get_from_env(self, key: str, *, default: str | None = None) -> str | None:
        env_key = f"ORDL_SECRET_{_normalize_secret_key(key)}"
        return os.getenv(env_key, default)

    def _get_from_vault(self, key: str, *, default: str | None = None) -> str | None:
        # Imported lazily to keep local/dev footprint light when vault is not used.
        import hvac  # type: ignore

        token = os.getenv(self._settings.vault_token_env_var, "")
        if not token:
            raise SecretResolutionError(
                f"vault token env var {self._settings.vault_token_env_var} is empty or not set"
            )
        client = hvac.Client(url=self._settings.vault_url, token=token)
        response = client.secrets.kv.v2.read_secret_version(
            mount_point=self._settings.vault_kv_mount,
            path=self._settings.vault_kv_path,
        )
        data = response.get("data", {}).get("data", {})
        if key in data:
            value = data.get(key)
        else:
            value = data.get(_normalize_secret_key(key))
        if value is None:
            return default
        return str(value)


@lru_cache(maxsize=1)
def get_secret_resolver() -> SecretResolver:
    return SecretResolver(get_settings())

