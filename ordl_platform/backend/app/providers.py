from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.policy import validate_policy_token
from app.secrets import get_secret_resolver


PROVIDER_REGISTRY = {
    "openai_codex": {
        "display_name": "OpenAI Codex",
        "auth_modes": ["managed_secret", "oauth_supported"],
        "required_secrets": ["OPENAI_API_KEY"],
    },
    "kimi": {
        "display_name": "Kimi",
        "auth_modes": ["oauth_supported", "managed_secret"],
        "required_secrets": ["KIMI_TOKEN"],
    },
    "anthropic": {
        "display_name": "Anthropic",
        "auth_modes": ["managed_secret", "oauth_supported"],
        "required_secrets": ["ANTHROPIC_API_KEY"],
    },
    "google_gemini": {
        "display_name": "Google Gemini",
        "auth_modes": ["managed_secret", "oauth_supported"],
        "required_secrets": ["GOOGLE_API_KEY"],
    },
    "azure_openai": {
        "display_name": "Azure OpenAI",
        "auth_modes": ["managed_secret", "oauth_supported"],
        "required_secrets": ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"],
    },
    "xai": {
        "display_name": "xAI",
        "auth_modes": ["managed_secret"],
        "required_secrets": ["XAI_API_KEY"],
    },
    "mistral": {
        "display_name": "Mistral",
        "auth_modes": ["managed_secret", "oauth_supported"],
        "required_secrets": ["MISTRAL_API_KEY"],
    },
    "groq": {
        "display_name": "Groq",
        "auth_modes": ["managed_secret"],
        "required_secrets": ["GROQ_API_KEY"],
    },
    "together": {
        "display_name": "Together AI",
        "auth_modes": ["managed_secret"],
        "required_secrets": ["TOGETHER_API_KEY"],
    },
    "perplexity": {
        "display_name": "Perplexity",
        "auth_modes": ["managed_secret"],
        "required_secrets": ["PERPLEXITY_API_KEY"],
    },
    "deepseek": {
        "display_name": "DeepSeek",
        "auth_modes": ["managed_secret"],
        "required_secrets": ["DEEPSEEK_API_KEY"],
    },
    "bedrock": {
        "display_name": "AWS Bedrock",
        "auth_modes": ["oauth_supported", "managed_secret"],
        "required_secrets": ["AWS_REGION"],
    },
    "openrouter": {
        "display_name": "OpenRouter",
        "auth_modes": ["managed_secret"],
        "required_secrets": ["OPENROUTER_API_KEY"],
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
        self._resolve_required_secrets(settings=settings)
        ref = f"{self.provider_name}:{request_hash[:12]}"
        return ProviderSendResult(provider_reference=ref, status="accepted")

    def _resolve_required_secrets(self, *, settings: Settings) -> None:
        if settings.environment.lower() not in {"production", "prod"}:
            return
        provider_meta = PROVIDER_REGISTRY.get(self.provider_name, {})
        required = provider_meta.get("required_secrets", [])
        resolver = get_secret_resolver()
        missing: list[str] = []
        for key in required:
            value = resolver.get(str(key))
            if not value:
                missing.append(str(key))
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise RuntimeError(f"missing required provider secrets for {self.provider_name}: {missing_text}")


class OpenAICodexAdapter(BaseProviderAdapter):
    provider_name = "openai_codex"


class KimiAdapter(BaseProviderAdapter):
    provider_name = "kimi"


def get_provider_adapter(provider: str) -> BaseProviderAdapter:
    if provider not in PROVIDER_REGISTRY:
        raise ValueError(f"unsupported provider: {provider}")
    if provider == "openai_codex":
        return OpenAICodexAdapter()
    if provider == "kimi":
        return KimiAdapter()
    adapter = BaseProviderAdapter()
    adapter.provider_name = provider
    return adapter
