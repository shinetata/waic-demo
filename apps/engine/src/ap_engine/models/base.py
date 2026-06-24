"""策略模型适配层：统一的 VisionPolicy 接口与输入/输出结构。

策略模型 = 给定意图 + 历史 + 当前微环境（全局缩略图 + 局部高清），决定下一步 (思考, 动作)。
"""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ap_engine.config import ModelConfig
from ap_engine.environments.base import EnvObservation
from ap_protocol import Action, Intent, Step, TokenUsage


@dataclass
class PolicyInput:
    intent: Intent
    step_index: int
    max_steps: int
    history: list[Step]
    observation: EnvObservation
    # 场景标识（d4-* 走多源破案侦探提示词）与案件上下文（可核查的源/目标）
    scene: str = "d0"
    case_context: Optional[str] = None


@dataclass
class PolicyDecision:
    thought: str
    action: Action
    tokens: Optional[TokenUsage] = None
    raw: Optional[str] = None


def image_data_url(path: str | Path, max_width: Optional[int] = None) -> str:
    """读图为 data URL。

    max_width 设置时先按比例降采样并降质（模拟"一次性整页、看不清细节"）——
    用于"现有做法"对照：整页缩略图里密集的脚注/口径小字不可读，只能依据显眼大字作答。
    """
    p = Path(path)
    if max_width is None:
        raw = p.read_bytes()
        return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")

    from io import BytesIO

    from PIL import Image

    img = Image.open(p).convert("RGB")
    if img.width > max_width:
        h = max(int(img.height * max_width / img.width), 1)
        img = img.resize((max_width, h), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def summarize_history(history: list[Step], limit: int = 8) -> str:
    if not history:
        return "（无，这是第一步）"
    recent = history[-limit:]
    lines = []
    for s in recent:
        label = s.action.label or s.action.type
        lines.append(f"  #{s.index} [{s.action.type}] {label} — {s.thought[:40]}")
    return "\n".join(lines)


class VisionPolicy(ABC):
    """策略模型接口。具体 provider 通过 .env 配置选择。"""

    def __init__(self, config: ModelConfig) -> None:
        self.config = config

    @property
    def side(self) -> str:
        return self.config.side

    @property
    def provider(self) -> str:
        return self.config.provider

    @property
    def model_name(self) -> str:
        return self.config.model_name

    @abstractmethod
    async def decide(self, inp: PolicyInput) -> PolicyDecision:
        """根据当前微环境产出下一步 (thought, action)。"""
        ...
