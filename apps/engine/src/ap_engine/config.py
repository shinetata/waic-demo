"""引擎配置：通过环境变量 / .env 注入，支持两侧模型独立可插拔配置（仅真实模型）。"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseModel):
    """单侧（ours / baseline）的策略模型配置。"""

    provider: str = "openai_compatible"
    model_name: str = "qwen/qwen3.5-vl-instruct"
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    label: str = "model"
    side: str = "ours"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8000
    max_steps: int = 40
    assets_dir: str = "assets"
    trajectories_dir: str = "trajectories"

    # 认知基模这一侧（主动感知逐步探索；前期 Qwen3.5-VL 代理，自研基模 ready 后替换）
    ours_provider: str = "openai_compatible"
    ours_model_name: str = "qwen/qwen3.5-vl-instruct"
    ours_base_url: Optional[str] = "https://openrouter.ai/api/v1"
    ours_api_key: Optional[str] = None
    ours_label: str = "认知基模"

    # 现有做法对照（同样真实模型，但一次性读入整图、读完再想）
    baseline_provider: str = "openai_compatible"
    baseline_model_name: str = "qwen/qwen3.5-vl-instruct"
    baseline_base_url: Optional[str] = "https://openrouter.ai/api/v1"
    baseline_api_key: Optional[str] = None
    baseline_label: str = "现有做法"

    def model_for(self, side: str) -> ModelConfig:
        """取某一侧的模型配置。side ∈ {ours, baseline}。"""
        if side == "baseline":
            return ModelConfig(
                provider=self.baseline_provider,
                model_name=self.baseline_model_name,
                base_url=self.baseline_base_url,
                api_key=self.baseline_api_key,
                label=self.baseline_label,
                side="baseline",
            )
        return ModelConfig(
            provider=self.ours_provider,
            model_name=self.ours_model_name,
            base_url=self.ours_base_url,
            api_key=self.ours_api_key,
            label=self.ours_label,
            side="ours",
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
