"""Active Perception 轨迹协议 — Pydantic v2 模型。

与 packages/protocol/schema/trajectory.schema.json 及 TS 定义 (src/index.ts) 对齐。
作为引擎产出/序列化轨迹与流式事件的契约。
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field

# ── 基础 ────────────────────────────────────────────────────

ActionType = Literal[
    "see",
    "click",
    "zoom_in",
    "zoom_out",
    "scroll",
    "none",
    "navigate",
    "snapshot",
    "eos",
]

ModelSide = Literal["ours", "baseline"]
TrajectoryStatus = Literal["running", "done", "aborted", "error"]

ACTION_TYPES: list[ActionType] = [
    "see",
    "click",
    "zoom_in",
    "zoom_out",
    "scroll",
    "none",
    "navigate",
    "snapshot",
    "eos",
]


class Rect(BaseModel):
    """归一化矩形 [0,1]，相对所在 stage 的整页/大图坐标系。"""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(ge=0, le=1)
    h: float = Field(ge=0, le=1)


# ── 混合 grounding ─────────────────────────────────────────


class ElementTarget(BaseModel):
    kind: Literal["element"] = "element"
    element_id: str
    stage: Optional[str] = None


class RegionTarget(BaseModel):
    kind: Literal["region"] = "region"
    rect: Rect
    stage: Optional[str] = None


class NavTarget(BaseModel):
    kind: Literal["nav"] = "nav"
    to: str


Target = Annotated[
    Union[ElementTarget, RegionTarget, NavTarget],
    Field(discriminator="kind"),
]


class Action(BaseModel):
    """动作。see/click/zoom_* 需 target；none/eos/snapshot 通常无 target。"""

    type: ActionType
    target: Optional[Target] = None
    label: Optional[str] = None
    reason: Optional[str] = None


class Observation(BaseModel):
    """环境产出的当前微环境：全局缩略图 + 当前局部高清 + 视野位置。"""

    stage: str
    full_image: Optional[str] = None
    thumbnail: Optional[str] = None
    crop_image: Optional[str] = None
    rect: Optional[Rect] = None
    zoom_level: Optional[float] = None


class Timing(BaseModel):
    started_at: Optional[str] = None
    duration_ms: Optional[float] = None


class Step(BaseModel):
    """一步主动感知：思考 + 动作 + 微环境。"""

    index: int = Field(ge=0)
    stage: str
    thought: str
    action: Action
    observation: Optional[Observation] = None
    timing: Optional[Timing] = None


class Intent(BaseModel):
    role: str
    persona: Optional[str] = None
    prompt: str


class ModelInfo(BaseModel):
    provider: Optional[str] = None
    name: str
    side: ModelSide = "ours"


class ActionCounts(BaseModel):
    see: int = 0
    click: int = 0
    zoom_in: int = 0
    zoom_out: int = 0
    scroll: int = 0
    none: int = 0
    navigate: int = 0
    snapshot: int = 0
    eos: int = 0


class TokenUsage(BaseModel):
    prompt: int = 0
    completion: int = 0
    total: int = 0


class TrajectoryStats(BaseModel):
    """对比模式与数据面板用的可量化指标。"""

    total_steps: int = 0
    action_counts: Optional[ActionCounts] = None
    skipped_regions: Optional[int] = None
    tokens: Optional[TokenUsage] = None
    duration_ms: Optional[float] = None
    # True = 模型主动 EOS 终止；False = 被步数预算截断
    reached_eos: bool = False


class TrajectoryResult(BaseModel):
    conclusion: Optional[str] = None
    output: Optional[str] = None
    stats: TrajectoryStats
    termination_reason: Optional[str] = None
    diagnostics: Optional[dict[str, Any]] = None


class Trajectory(BaseModel):
    id: str
    scene: str
    intent: Intent
    model: ModelInfo
    steps: list[Step] = Field(default_factory=list)
    result: Optional[TrajectoryResult] = None
    status: TrajectoryStatus = "running"
    created_at: str


# ── 流式事件 ────────────────────────────────────────────────


class TrajectoryStartEvent(BaseModel):
    type: Literal["trajectory_start"] = "trajectory_start"
    trajectory: Trajectory


class StepEvent(BaseModel):
    type: Literal["step"] = "step"
    step: Step


class ThoughtDeltaEvent(BaseModel):
    type: Literal["thought_delta"] = "thought_delta"
    index: int
    delta: str


class TrajectoryEndEvent(BaseModel):
    type: Literal["trajectory_end"] = "trajectory_end"
    result: TrajectoryResult
    status: TrajectoryStatus


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str


StreamEvent = Annotated[
    Union[
        TrajectoryStartEvent,
        StepEvent,
        ThoughtDeltaEvent,
        TrajectoryEndEvent,
        ErrorEvent,
    ],
    Field(discriminator="type"),
]
