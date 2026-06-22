"""策略模型适配层：通过 .env 的 provider 可插拔切换。"""

from __future__ import annotations

from ap_engine.config import ModelConfig
from ap_engine.models.base import (
    PolicyDecision,
    PolicyInput,
    VisionPolicy,
    image_data_url,
    summarize_history,
)
from ap_engine.models.mock import MockPolicy

_OPENAI_ALIASES = {"openai_compatible", "openai", "openrouter", "vllm", "compat"}


def make_policy(config: ModelConfig) -> VisionPolicy:
    provider = (config.provider or "mock").lower()
    if provider == "mock":
        return MockPolicy(config)
    if provider in _OPENAI_ALIASES:
        from ap_engine.models.openai_compatible import OpenAICompatiblePolicy

        return OpenAICompatiblePolicy(config)
    raise ValueError(f"unknown model provider: {config.provider!r}")


__all__ = [
    "MockPolicy",
    "PolicyDecision",
    "PolicyInput",
    "VisionPolicy",
    "image_data_url",
    "make_policy",
    "summarize_history",
]
