"""引擎配置：通过环境变量 / .env 注入，支持两侧模型独立可插拔配置。"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseModel):
    """单侧（ours / baseline）的策略模型配置。"""

    provider: str = "mock"
    model_name: str = "mock-model"
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
    max_steps: int = 24
    assets_dir: str = "assets"
    trajectories_dir: str = "trajectories"

    # "我们这一侧"
    ours_provider: str = "mock"
    ours_model_name: str = "mock-active-lifting"
    ours_base_url: Optional[str] = None
    ours_api_key: Optional[str] = None
    ours_label: str = "Active Lifting (ours)"

    # baseline
    baseline_provider: str = "mock"
    baseline_model_name: str = "google/gemma-4-31b-it"
    baseline_base_url: Optional[str] = "https://openrouter.ai/api/v1"
    baseline_api_key: Optional[str] = None
    baseline_label: str = "Gemma 4 31B (baseline)"

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
