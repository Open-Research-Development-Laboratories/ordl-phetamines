from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.policy import validate_policy_token


PROVIDER_REGISTRY = {
    "openai_codex": {
        "display_name": "OpenAI Codex",
        "auth_modes": ["managed_secret", "oauth_supported"],
    },
    "kimi": {
        "display_name": "Kimi",
        "auth_modes": ["oauth_supported", "managed_secret"],
    },
}


@dataclass
class ProviderSendResult:
    provider_reference: str
    status: str


class BaseProviderAdapter:
    provider_name: str = "base"

    def send(
        self,
        *,
        policy_token: str,
        request_hash: str,
        destination_scope: str,
        payload: dict,
        settings: Settings,
    ) -> ProviderSendResult:
        validate_policy_token(
            token=policy_token,
            expected_request_hash=request_hash,
            expected_destination_scope=destination_scope,
            settings=settings,
        )
        ref = f"{self.provider_name}:{request_hash[:12]}"
        return ProviderSendResult(provider_reference=ref, status="accepted")


class OpenAICodexAdapter(BaseProviderAdapter):
    provider_name = "openai_codex"


class KimiAdapter(BaseProviderAdapter):
    provider_name = "kimi"


def get_provider_adapter(provider: str) -> BaseProviderAdapter:
    if provider == "openai_codex":
        return OpenAICodexAdapter()
    if provider == "kimi":
        return KimiAdapter()
    raise ValueError(f"unsupported provider: {provider}")

