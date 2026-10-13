import json
from functools import lru_cache
from typing import Any, Protocol

import httpx

from app.core.config import get_settings


class LlmError(Exception):
    """The model was unreachable, timed out, or returned unusable output."""


class LlmProvider(Protocol):
    name: str
    model: str

    def generate_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]: ...


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float) -> None:
        self.model = model
        self._client = httpx.Client(base_url=base_url, timeout=timeout)

    def generate_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "stream": False,
            "format": schema,  # constrains the output to this JSON schema
            "options": {"temperature": 0, "num_ctx": 8192},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            response = self._client.post("/api/chat", json=payload)
            response.raise_for_status()
            parsed = json.loads(response.json()["message"]["content"])
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LlmError("The language model call failed") from exc
        if not isinstance(parsed, dict):
            raise LlmError("The language model returned unexpected output")
        return parsed


@lru_cache
def get_llm_provider() -> LlmProvider | None:
    settings = get_settings()
    if not settings.llm_enabled:
        return None
    return OllamaProvider(
        settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout_seconds
    )