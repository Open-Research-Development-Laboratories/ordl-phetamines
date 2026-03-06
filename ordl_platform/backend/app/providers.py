from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from urllib import error, request

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
    output_text: str = ""
    error_text: str = ""
    events: list[dict[str, Any]] | None = None


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
        return self.execute(
            policy_token=policy_token,
            request_hash=request_hash,
            destination_scope=destination_scope,
            payload=payload,
            model="",
            settings=settings,
            provider_metadata={},
        )

    def execute(
        self,
        *,
        policy_token: str,
        request_hash: str,
        destination_scope: str,
        payload: dict,
        model: str,
        settings: Settings,
        provider_metadata: dict[str, Any],
    ) -> ProviderSendResult:
        validate_policy_token(
            token=policy_token,
            expected_request_hash=request_hash,
            expected_destination_scope=destination_scope,
            settings=settings,
        )
        self._resolve_required_secrets(settings=settings)
        ref = f"{self.provider_name}:{request_hash[:12]}"
        prompt = self._extract_prompt(payload)
        events = [
            {"event_type": "execution.started", "payload": {"provider": self.provider_name, "model": model}},
            {
                "event_type": "execution.accepted",
                "payload": {"provider_reference": ref, "prompt_chars": len(prompt)},
            },
            {"event_type": "execution.completed", "payload": {"status": "completed"}},
        ]
        return ProviderSendResult(
            provider_reference=ref,
            status="completed",
            output_text=f"[simulated:{self.provider_name}] {prompt}".strip(),
            error_text="",
            events=events,
        )

    def _extract_prompt(self, payload: dict[str, Any]) -> str:
        direct = str(payload.get("prompt", "")).strip()
        if direct:
            return direct
        task = str(payload.get("task", "")).strip()
        context = str(payload.get("context", "")).strip()
        if task and context:
            return f"{task}\n\nContext:\n{context}"
        if task:
            return task
        return json.dumps(payload, sort_keys=True)

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

    def execute(
        self,
        *,
        policy_token: str,
        request_hash: str,
        destination_scope: str,
        payload: dict,
        model: str,
        settings: Settings,
        provider_metadata: dict[str, Any],
    ) -> ProviderSendResult:
        validate_policy_token(
            token=policy_token,
            expected_request_hash=request_hash,
            expected_destination_scope=destination_scope,
            settings=settings,
        )
        self._resolve_required_secrets(settings=settings)
        prompt = self._extract_prompt(payload)
        ref = f"{self.provider_name}:{request_hash[:12]}"

        resolver = get_secret_resolver()
        api_key = resolver.get("OPENAI_API_KEY", default="") or ""
        live_enabled = bool(provider_metadata.get("live_enabled", False))
        if not live_enabled or not api_key:
            return ProviderSendResult(
                provider_reference=ref,
                status="completed",
                output_text=f"[simulated:openai_codex] {prompt}".strip(),
                error_text="",
                events=[
                    {"event_type": "execution.started", "payload": {"provider": self.provider_name, "model": model}},
                    {"event_type": "execution.simulated", "payload": {"reason": "live_disabled_or_missing_secret"}},
                    {"event_type": "execution.completed", "payload": {"status": "completed"}},
                ],
            )

        endpoint = str(provider_metadata.get("responses_endpoint") or "https://api.openai.com/v1/responses")
        body = {
            "model": model or str(provider_metadata.get("default_model") or "gpt-5.4"),
            "input": prompt,
        }
        try:
            req = request.Request(
                endpoint,
                method="POST",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps(body).encode("utf-8"),
            )
            with request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
            parsed = json.loads(raw)
            output_text = str(parsed.get("output_text", "")).strip()
            if not output_text:
                output_chunks: list[str] = []
                output = parsed.get("output", [])
                if isinstance(output, list):
                    for item in output:
                        if not isinstance(item, dict):
                            continue
                        content = item.get("content", [])
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict):
                                    text = str(block.get("text", "")).strip()
                                    if text:
                                        output_chunks.append(text)
                output_text = "\n".join(output_chunks).strip()
            provider_id = str(parsed.get("id", ref))
            return ProviderSendResult(
                provider_reference=provider_id,
                status="completed",
                output_text=output_text,
                error_text="",
                events=[
                    {"event_type": "execution.started", "payload": {"provider": self.provider_name, "model": body["model"]}},
                    {"event_type": "provider.response", "payload": {"provider_reference": provider_id}},
                    {"event_type": "execution.completed", "payload": {"status": "completed"}},
                ],
            )
        except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return ProviderSendResult(
                provider_reference=ref,
                status="failed",
                output_text="",
                error_text=str(exc),
                events=[
                    {"event_type": "execution.started", "payload": {"provider": self.provider_name, "model": model}},
                    {"event_type": "provider.error", "payload": {"error": str(exc)}},
                    {"event_type": "execution.failed", "payload": {"status": "failed"}},
                ],
            )


class KimiAdapter(BaseProviderAdapter):
    provider_name = "kimi"

    def execute(
        self,
        *,
        policy_token: str,
        request_hash: str,
        destination_scope: str,
        payload: dict,
        model: str,
        settings: Settings,
        provider_metadata: dict[str, Any],
    ) -> ProviderSendResult:
        validate_policy_token(
            token=policy_token,
            expected_request_hash=request_hash,
            expected_destination_scope=destination_scope,
            settings=settings,
        )
        self._resolve_required_secrets(settings=settings)
        prompt = self._extract_prompt(payload)
        ref = f"{self.provider_name}:{request_hash[:12]}"

        resolver = get_secret_resolver()
        token = resolver.get("KIMI_TOKEN", default="") or ""
        live_enabled = bool(provider_metadata.get("live_enabled", False))
        if not live_enabled or not token:
            return ProviderSendResult(
                provider_reference=ref,
                status="completed",
                output_text=f"[simulated:kimi] {prompt}".strip(),
                error_text="",
                events=[
                    {"event_type": "execution.started", "payload": {"provider": self.provider_name, "model": model}},
                    {"event_type": "execution.simulated", "payload": {"reason": "live_disabled_or_missing_secret"}},
                    {"event_type": "execution.completed", "payload": {"status": "completed"}},
                ],
            )

        endpoint = str(
            provider_metadata.get("chat_endpoint")
            or provider_metadata.get("api_base")
            or "https://api.moonshot.cn/v1/chat/completions"
        )
        body = {
            "model": model or str(provider_metadata.get("default_model") or "kimi-k2"),
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        try:
            req = request.Request(
                endpoint,
                method="POST",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                data=json.dumps(body).encode("utf-8"),
            )
            with request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
            parsed = json.loads(raw)
            output_text = ""
            choices = parsed.get("choices", [])
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    message = first.get("message", {})
                    if isinstance(message, dict):
                        output_text = str(message.get("content", "")).strip()
            provider_id = str(parsed.get("id", ref))
            return ProviderSendResult(
                provider_reference=provider_id,
                status="completed",
                output_text=output_text,
                error_text="",
                events=[
                    {"event_type": "execution.started", "payload": {"provider": self.provider_name, "model": body["model"]}},
                    {"event_type": "provider.response", "payload": {"provider_reference": provider_id}},
                    {"event_type": "execution.completed", "payload": {"status": "completed"}},
                ],
            )
        except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return ProviderSendResult(
                provider_reference=ref,
                status="failed",
                output_text="",
                error_text=str(exc),
                events=[
                    {"event_type": "execution.started", "payload": {"provider": self.provider_name, "model": model}},
                    {"event_type": "provider.error", "payload": {"error": str(exc)}},
                    {"event_type": "execution.failed", "payload": {"status": "failed"}},
                ],
            )


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
