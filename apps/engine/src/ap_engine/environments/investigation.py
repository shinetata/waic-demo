"""D4 多源破案：多个矛盾信息源，主动选择阅读、发现矛盾、回看脚注、推出一致性解释。

复用同一轨迹协议（thought + action）。当前用 mock 剧本驱动打通"矛盾→解决"叙事；
真实模型（文本/多模态）后续可经适配层接入。证据为文本卡片，由前端证据板渲染。
"""

from __future__ import annotations

import asyncio
import datetime
import uuid
from dataclasses import dataclass
from typing import AsyncGenerator, Optional

from ap_protocol import (
    Action,
    ActionCounts,
    ElementTarget,
    Intent,
    ModelInfo,
    Observation,
    Step,
    StepEvent,
    StreamEvent,
    TrajectoryEndEvent,
    TrajectoryResult,
    TrajectoryStartEvent,
    TrajectoryStats,
    Trajectory,
)


@dataclass
class Source:
    id: str
    title: str
    kind: str
    value: str
    detail: str
    footnote: Optional[str] = None


@dataclass
class InvestigationCase:
    id: str
    title: str
    question: str
    sources: list[Source]
    conflict: tuple[str, str]
    resolution: str
    truth: str


CASES: dict[str, InvestigationCase] = {
    "revenue": InvestigationCase(
        id="revenue",
        title="企业营收核查",
        question="X 公司 2025 年的真实营收是多少？",
        sources=[
            Source("A", "公司年报", "report", "15 亿", "合并营业收入 15.0 亿元", "脚注③：合并口径，含关联交易"),
            Source("B", "券商研报", "analyst", "10 亿", "主营业务收入 10.2 亿元", None),
            Source("C", "新闻稿", "news", "12 亿", "营收约 12 亿元（媒体估算）", None),
        ],
        conflict=("A", "B"),
        resolution="A 为含关联交易的合并口径(15亿)，B 为主营业务口径(10亿)，统计口径不同，并不矛盾。",
        truth="主营业务约 10 亿，合并口径 15 亿（含关联交易）",
    ),
    "product": InvestigationCase(
        id="product",
        title="产品参数核查",
        question="Y 耳机的真实续航是多少小时？",
        sources=[
            Source("A", "官网参数", "report", "20 小时", "续航 20 小时", "脚注：25℃ 实验室、50% 音量、关闭降噪"),
            Source("B", "第三方评测", "analyst", "12 小时", "实测续航 12 小时", None),
            Source("C", "用户反馈", "news", "15 小时", "日常使用约 15 小时", None),
        ],
        conflict=("A", "B"),
        resolution="A 为实验室理想条件(20h)，B 为高负载实测(12h)，测试条件不同，并不矛盾。",
        truth="日常约 15h、高负载 12h、理想条件 20h",
    ),
}


def list_cases() -> list[dict]:
    out = []
    for c in CASES.values():
        out.append(
            {
                "id": c.id,
                "title": c.title,
                "question": c.question,
                "conflict": list(c.conflict),
                "sources": [
                    {"id": s.id, "title": s.title, "kind": s.kind, "value": s.value, "detail": s.detail, "footnote": s.footnote}
                    for s in c.sources
                ],
            }
        )
    return out


def get_case(case_id: str) -> InvestigationCase:
    if case_id not in CASES:
        raise KeyError(f"unknown case: {case_id}")
    return CASES[case_id]


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


async def run_investigation(
    scene: str,
    role: str,
    side: str = "ours",
    settings=None,
) -> AsyncGenerator[StreamEvent, None]:
    from ap_engine.config import get_settings
    from ap_engine.storage import save_trajectory

    settings = settings or get_settings()
    case = get_case(role)
    sa = next(s for s in case.sources if s.id == case.conflict[0])
    sb = next(s for s in case.sources if s.id == case.conflict[1])

    traj_id = uuid.uuid4().hex[:12]
    intent = Intent(role=role, persona=f"侦探 · {case.title}", prompt=case.question)
    traj = Trajectory(
        id=traj_id,
        scene=scene,
        intent=intent,
        model=ModelInfo(provider="mock", name="investigation-mock", side=side if side in ("ours", "baseline") else "ours"),
        steps=[],
        status="running",
        created_at=_now(),
    )
    yield TrajectoryStartEvent(trajectory=traj)

    # 剧本：读各源 → 发现矛盾 → 回看 A → zoom 脚注 → 顿悟 → 解决
    script: list[tuple[str, str, str, Optional[str]]] = []
    for s in case.sources:
        script.append((f"读取「{s.title}」（{s.id}）：{s.detail}。", "see", f"READ {s.id}", s.id))
    script.append((f"⚠️ 矛盾！{sa.title}={sa.value} 与 {sb.title}={sb.value} 对不上。", "none", f"CONFLICT {sa.id}↔{sb.id}", None))
    script.append((f"不急着下结论，主动回看「{sa.title}」找原因。", "navigate", f"RE-EXAMINE {sa.id}", sa.id))
    if sa.footnote:
        script.append((f"放大角落里那行小字 —— {sa.footnote}。", "zoom_in", f"ZOOM 脚注 {sa.id}", f"{sa.id}_footnote"))
    script.append((f"恍然大悟：{case.resolution}", "none", "INSIGHT 口径差异", None))
    script.append((f"结论：{case.truth}。矛盾已解决。", "eos", "RESOLVED", None))

    steps: list[Step] = []
    counts: dict[str, int] = {}
    for i, (thought, atype, label, tid) in enumerate(script):
        target = ElementTarget(element_id=tid) if tid else None
        action = Action(type=atype, target=target, label=label)
        step = Step(
            index=i,
            stage=(tid or "board"),
            thought=thought,
            action=action,
            observation=Observation(stage=(tid or "board")),
        )
        steps.append(step)
        counts[atype] = counts.get(atype, 0) + 1
        yield StepEvent(step=step)
        await asyncio.sleep(0.05)

    stats = TrajectoryStats(
        total_steps=len(steps),
        action_counts=ActionCounts(
            **{
                k: counts.get(k, 0)
                for k in ["see", "click", "zoom_in", "zoom_out", "scroll", "none", "navigate", "snapshot", "eos"]
            }
        ),
        reached_eos=True,
    )
    result = TrajectoryResult(conclusion=case.truth, output="RESOLVED", stats=stats)
    traj.steps = steps
    traj.result = result
    traj.status = "done"
    try:
        save_trajectory(traj, settings.trajectories_dir)
    except OSError:
        pass
    yield TrajectoryEndEvent(result=result, status="done")
