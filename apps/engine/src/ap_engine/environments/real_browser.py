"""RealBrowserEnvironment（预留）。

后期接入：用 Playwright 驱动真实浏览器渲染任意网页 → 截图 → 主动感知裁剪。
阶段一未实现，仅占位以体现环境层可扩展。
"""

from __future__ import annotations

from ap_engine.environments.base import Environment, EnvObservation
from ap_protocol import Action


class RealBrowserEnvironment(Environment):
    def __init__(self, *args, **kwargs) -> None:  # noqa: D401
        raise NotImplementedError(
            "RealBrowserEnvironment 预留，未实现（需 playwright；阶段一用 SelfPageEnvironment）"
        )

    def reset(self) -> EnvObservation:  # pragma: no cover
        raise NotImplementedError

    def step(self, action: Action) -> EnvObservation:  # pragma: no cover
        raise NotImplementedError

    @property
    def stage(self) -> str:  # pragma: no cover
        raise NotImplementedError

    @property
    def elements(self):  # pragma: no cover
        raise NotImplementedError
