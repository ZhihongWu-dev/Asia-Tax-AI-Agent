"""Thin OpenAI-compatible chat client (stdlib only) with strict-JSON support.

L0 governance (PRD s.3.3 / decision gate 2026-08-31): only synthetic data
may be sent to any model; keys live in .env (git-ignored), never in code,
logs, or committed files.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelSettings(BaseSettings):
    base_url: str = ""   # e.g. https://api.provider.com/v1
    api_key: str = ""
    model_name: str = ""  # e.g. gpt-4o-mini / qwen-plus
    timeout_seconds: float = 60.0
    max_retries: int = 2

    model_config = SettingsConfigDict(env_file=".env", env_prefix="FSIE_MODEL_", extra="ignore")


@lru_cache
def get_model_config() -> "ModelConfig":
    s = ModelSettings()
    return ModelConfig(
        base_url=s.base_url.rstrip("/"),
        api_key=s.api_key,
        model_name=s.model_name,
        timeout_seconds=s.timeout_seconds,
        max_retries=s.max_retries,
    )


@dataclass(frozen=True)
class ModelConfig:
    base_url: str
    api_key: str
    model_name: str
    timeout_seconds: float = 60.0
    max_retries: int = 2

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model_name)

    def require(self) -> "ModelConfig":
        if not self.is_configured:
            raise ModelError(
                "model adapter not configured: set FSIE_MODEL_BASE_URL, "
                "FSIE_MODEL_API_KEY and FSIE_MODEL_NAME in .env"
            )
        return self


class ModelError(RuntimeError):
    pass


class OpenAICompatibleClient:
    """Minimal chat-completions client. JSON-mode helper strips code fences."""

    def __init__(self, config: ModelConfig | None = None):
        self.config = (config or get_model_config()).require()

    def chat(self, system: str, user: str, *, temperature: float = 0.0, max_tokens: int = 2000) -> str:
        payload = {
            "model": self.config.model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        body = self._post("/chat/completions", payload)
        try:
            return body["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelError(f"unexpected chat response shape: {str(body)[:300]}") from exc

    def chat_json(self, system: str, user: str, *, temperature: float = 0.0, max_tokens: int = 2000) -> dict:
        raw = self.chat(system, user, temperature=temperature, max_tokens=max_tokens)
        return parse_json_loose(raw)

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.config.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            request = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:400]
                # 4xx (except 429) will not succeed on retry.
                if 400 <= exc.code < 500 and exc.code != 429:
                    raise ModelError(f"model API HTTP {exc.code}: {detail}") from exc
                last_error = ModelError(f"model API HTTP {exc.code}: {detail}")
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = ModelError(f"model API transport error: {exc}")
            if attempt < self.config.max_retries:
                time.sleep(1.5 * (attempt + 1))
        raise ModelError(f"model call failed after retries: {last_error}")


def parse_json_loose(raw: str) -> dict:
    """Parse a model JSON answer, tolerating code fences and prose around it."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ModelError(f"model did not return JSON: {text[:200]!r}")
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ModelError(f"model returned malformed JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ModelError("model JSON must be an object of field_name -> value")
    return parsed
