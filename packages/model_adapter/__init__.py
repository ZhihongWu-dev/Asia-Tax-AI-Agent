"""Vendor-neutral model adapter layer (roadmap s.2: 模型接入 = 供应商适配层).

Business logic never talks to a specific vendor; it talks to this adapter,
which speaks the OpenAI-compatible chat-completions dialect over HTTP.
Provider, model and credentials come from environment configuration only.
"""

from packages.model_adapter.client import (
    ModelConfig,
    ModelError,
    OpenAICompatibleClient,
    get_model_config,
)

__all__ = [
    "ModelConfig",
    "ModelError",
    "OpenAICompatibleClient",
    "get_model_config",
]
