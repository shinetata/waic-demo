"""Agent Loop：主动感知闭环。

意图 → 微环境 → 模型推 (心语 wₜ, 动作 aₜ) → 环境执行 → 新微环境 → … → EOS。
流式 yield StreamEvent（供 WebSocket 边推边播），并把完整轨迹落盘（回放 / 兜底）。
含最大步数预算与防重复（卡死保护）。
"""

from __future__ import annotations

import datetime
import time
import uuid
from pathlib import Path
from typing import AsyncGenerator, Optional

from ap_engine.config import Settings, get_settings
from ap_engine.environments import get_role, make_environment
from ap_engine.models import PolicyInput, make_policy
from ap_engine.storage import save_trajectory
from ap_protocol import (
    ActionCounts,
    Intent,
    ModelInfo,
    Step,
    StepEvent,
    StreamEvent,
    Timing,
    TokenUsage,
    Trajectory,
    TrajectoryEndEvent,
    TrajectoryResult,
    TrajectoryStartEvent,
    TrajectoryStats,
)

_ACTION_KEYS = [
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


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


async def run_trajectory(
    scene: str,
    role: str,
    side: str = "ours",
    settings: Optional[Settings] = None,
) -> AsyncGenerator[StreamEvent, None]:
    settings = settings or get_settings()

    # D4 多源破案：复用协议与流式，走独立的多源环境/剧本
    if scene.startswith("d4"):
        from ap_engine.environments.investigation import run_investigation

        async for ev in run_investigation(scene, role, side, settings):
            yield ev
        return

    role_spec = get_role(scene, role)  # KeyError -> 由调用方处理
    side = side if side in ("ours", "baseline") else "ours"
    model_cfg = settings.model_for(side)

    traj_id = uuid.uuid4().hex[:12]
    runtime_dir = str(Path(settings.assets_dir) / "runtime")
    env = make_environment(
        scene,
        role,
        assets_dir=settings.assets_dir,
        runtime_dir=runtime_dir,
        asset_base_url="/assets",
        traj_id=traj_id,
    )
    policy = make_policy(model_cfg)
    intent = Intent(role=role, persona=role_spec.persona, prompt=role_spec.prompt)

    traj = Trajectory(
        id=traj_id,
        scene=scene,
        intent=intent,
        model=ModelInfo(provider=model_cfg.provider, name=model_cfg.model_name, side=side),
        steps=[],
        status="running",
        created_at=_now(),
    )
    yield TrajectoryStartEvent(trajectory=traj)

    obs = env.reset()
    steps: list[Step] = []
    counts: dict[str, int] = {}
    tokens = TokenUsage(prompt=0, completion=0, total=0)
    seen_elements: set[str] = set()
    prev_sig: Optional[str] = None
    repeat = 0
    reached_eos = False
    t0 = time.perf_counter()
    max_steps = settings.max_steps

    for i in range(max_steps):
        inp = PolicyInput(
            intent=intent,
            goal_hint=role_spec.goal_hint,
            step_index=i,
            max_steps=max_steps,
            history=steps,
            observation=obs,
        )
        s0 = time.perf_counter()
        decision = await policy.decide(inp)
        dur_ms = round((time.perf_counter() - s0) * 1000, 1)

        action = decision.action
        step = Step(
            index=i,
            stage=obs.stage,
            thought=decision.thought,
            action=action,
            observation=obs.to_protocol(),
            timing=Timing(started_at=_now(), duration_ms=dur_ms),
        )
        steps.append(step)
        counts[action.type] = counts.get(action.type, 0) + 1
        if decision.tokens:
            tokens.prompt += decision.tokens.prompt
            tokens.completion += decision.tokens.completion
            tokens.total += decision.tokens.total
        if action.target is not None and getattr(action.target, "kind", None) == "element":
            seen_elements.add(action.target.element_id)

        yield StepEvent(step=step)

        if action.type == "eos":
            reached_eos = True
            break

        # 防重复（卡死保护）：连续 3 次完全相同的非 none 动作才终止（给模型自我纠正空间）
        sig = f"{action.type}:{action.target.model_dump_json() if action.target else ''}"
        if sig == prev_sig and action.type != "none":
            repeat += 1
            if repeat >= 2:
                break
        else:
            repeat = 0
        prev_sig = sig

        obs = env.step(action)

    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    total_elements = len(env.elements)
    skipped = max(total_elements - len(seen_elements), 0)

    stats = TrajectoryStats(
        total_steps=len(steps),
        action_counts=ActionCounts(**{k: counts.get(k, 0) for k in _ACTION_KEYS}),
        skipped_regions=skipped,
        tokens=tokens if tokens.total > 0 else None,
        duration_ms=total_ms,
        reached_eos=reached_eos,
    )
    last = steps[-1] if steps else None
    final_output = role_spec.output or (
        last.action.label if (last and last.action.type == "eos") else None
    )
    result = TrajectoryResult(
        conclusion=last.thought if last else None,
        output=final_output,
        stats=stats,
    )

    traj.steps = steps
    traj.result = result
    traj.status = "done"
    try:
        save_trajectory(traj, settings.trajectories_dir)
    except OSError:
        pass

    yield TrajectoryEndEvent(result=result, status="done")


async def run_trajectory_collect(
    scene: str,
    role: str,
    side: str = "ours",
    settings: Optional[Settings] = None,
) -> Trajectory:
    """跑完整条轨迹并返回 Trajectory（命令行 / 离线生成用）。"""
    traj: Optional[Trajectory] = None
    steps: list[Step] = []
    async for ev in run_trajectory(scene, role, side, settings):
        if isinstance(ev, TrajectoryStartEvent):
            traj = ev.trajectory
        elif isinstance(ev, StepEvent):
            steps.append(ev.step)
        elif isinstance(ev, TrajectoryEndEvent) and traj is not None:
            traj.steps = steps
            traj.result = ev.result
            traj.status = ev.status
    assert traj is not None
    return traj
