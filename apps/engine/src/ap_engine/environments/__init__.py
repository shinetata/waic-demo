"""环境层：主动感知微环境的抽象与实现。"""

from __future__ import annotations

from pathlib import Path

from ap_engine.environments.base import (
    ElementSpec,
    Environment,
    EnvObservation,
    RoleSpec,
    SceneSpec,
    StageSpec,
)
from ap_engine.environments.scenes import (
    SCENES,
    get_role,
    get_scene,
    list_scenes,
)
from ap_engine.environments.self_page import SelfPageEnvironment


def make_environment(
    scene_id: str,
    role_key: str,
    *,
    assets_dir: str | Path,
    runtime_dir: str | Path,
    asset_base_url: str = "/assets",
    traj_id: str = "traj",
) -> Environment:
    """工厂：当前返回 SelfPageEnvironment；后期可按 scene 配置切换 RealBrowserEnvironment。"""
    return SelfPageEnvironment(
        scene_id,
        role_key,
        assets_dir=assets_dir,
        runtime_dir=runtime_dir,
        asset_base_url=asset_base_url,
        traj_id=traj_id,
    )


__all__ = [
    "ElementSpec",
    "Environment",
    "EnvObservation",
    "RoleSpec",
    "SceneSpec",
    "StageSpec",
    "SCENES",
    "SelfPageEnvironment",
    "get_role",
    "get_scene",
    "list_scenes",
    "make_environment",
]
