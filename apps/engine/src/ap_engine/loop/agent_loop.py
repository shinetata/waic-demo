"""Agent Loop：主动感知闭环。

意图 → 微环境 → 模型推 (思考, 动作) → 环境执行 → 新微环境 → … → EOS。
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
    Action,
    ActionCounts,
    ElementTarget,
    Intent,
    ModelInfo,
    Rect,
    RegionTarget,
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


# 进入新页面后至少先观察这么多次（see/zoom/snapshot）才允许 click 离开本页：
# 体现"主动感知 = 先看清再导航"，并为长程深链任务保证足够的逐页核查步数。
_MIN_OBSERVE_BEFORE_NAV = 3


def _coerce_observe(obs, seen_ids: set[str]) -> Optional[Action]:
    """把"过早 click"改写为对本页一个尚未查看区域的 see；本页区域均已看过则返回 None（放行 click）。"""
    for e in obs.elements:
        if e.kind != "link" and e.id not in seen_ids:
            return Action(type="see", target=ElementTarget(element_id=e.id), label=f"SEE {e.label}")
    return None


async def run_trajectory(
    scene: str,
    role: str,
    side: str = "ours",
    settings: Optional[Settings] = None,
) -> AsyncGenerator[StreamEvent, None]:
    settings = settings or get_settings()
    side = side if side in ("ours", "baseline") else "ours"

    # 现有做法对照（baseline）：一次性整图问答（读完再想），不走主动感知 loop
    if side == "baseline":
        async for ev in run_oneshot_trajectory(scene, role, settings):
            yield ev
        return

    role_spec = get_role(scene, role)  # KeyError -> 由调用方处理
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

    # 软约束状态：当前页已观察次数与已看过的区域 id（保证"先看清再导航"）
    cur_stage = obs.stage
    stage_observe = 0
    stage_seen_ids: set[str] = set()
    _observe_types = ("see", "zoom_in", "zoom_out", "snapshot")

    for i in range(max_steps):
        inp = PolicyInput(
            intent=intent,
            step_index=i,
            max_steps=max_steps,
            history=steps,
            observation=obs,
        )
        s0 = time.perf_counter()
        decision = await policy.decide(inp)
        dur_ms = round((time.perf_counter() - s0) * 1000, 1)

        action = decision.action
        thought = decision.thought
        sig = f"{action.type}:{action.target.model_dump_json() if action.target else ''}"
        # 规整①：进入新页后未充分观察就 click，改写为先 see 一个未看区域（先看清再导航）
        if action.type == "click" and stage_observe < _MIN_OBSERVE_BEFORE_NAV:
            forced = _coerce_observe(obs, stage_seen_ids)
            if forced is not None:
                action = forced
                thought = "先把本页关键区域看清楚，再决定是否进入下一页继续核查。"
                sig = f"{action.type}:{action.target.model_dump_json() if action.target else ''}"
        # 规整②：与上一步完全相同的观察动作（原地打转）→ 换一个本页未看区域，推进核查
        elif sig == prev_sig and action.type in _observe_types:
            forced = _coerce_observe(obs, stage_seen_ids)
            if forced is not None:
                action = forced
                thought = "换一个关键区域，继续核查本页其它要点。"
                sig = f"{action.type}:{action.target.model_dump_json() if action.target else ''}"

        step = Step(
            index=i,
            stage=obs.stage,
            thought=thought,
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
        if action.type in _observe_types:
            stage_observe += 1
            if action.target is not None and getattr(action.target, "kind", None) == "element":
                stage_seen_ids.add(action.target.element_id)

        yield StepEvent(step=step)

        if action.type == "eos":
            reached_eos = True
            break

        # 卡死保护：连续相同的非 none 动作累计达阈值才终止（给模型自我纠正空间）
        if sig == prev_sig and action.type != "none":
            repeat += 1
            if repeat >= 3:
                # 末页（无可进入链接）反复纠结：视为已完成核查，正常收尾
                if not any(e.kind == "link" for e in obs.elements):
                    reached_eos = True
                break
        else:
            repeat = 0
        prev_sig = sig

        obs = env.step(action)
        # 切换到新页面：重置本页观察计数
        if obs.stage != cur_stage:
            cur_stage = obs.stage
            stage_observe = 0
            stage_seen_ids = set()

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
    # 产出用模型自己给出的真实结论（eos 的 label/thought），不再使用任何预设文案
    final_output = None
    if last is not None and last.action.type == "eos":
        label = (last.action.label or "").strip()
        if label.upper().startswith("OUTPUT:"):
            label = label.split(":", 1)[1].strip()
        final_output = label or last.thought
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


async def run_oneshot_trajectory(
    scene: str,
    role: str,
    settings: Optional[Settings] = None,
) -> AsyncGenerator[StreamEvent, None]:
    """现有做法对照：把整页图一次性喂入真实模型 + 直接问答（读完再想）。

    产出两步轨迹：see 整页（一次性读入）→ eos（直接给结论），用于前端"现有做法"小窗反衬。
    """
    settings = settings or get_settings()
    role_spec = get_role(scene, role)
    model_cfg = settings.model_for("baseline")

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
    intent = Intent(role=role, persona=role_spec.persona, prompt=role_spec.prompt)
    traj = Trajectory(
        id=traj_id,
        scene=scene,
        intent=intent,
        model=ModelInfo(provider=model_cfg.provider, name=model_cfg.model_name, side="baseline"),
        steps=[],
        status="running",
        created_at=_now(),
    )
    yield TrajectoryStartEvent(trajectory=traj)

    obs = env.reset()  # 首页全局视野（整页）
    steps: list[Step] = []
    t0 = time.perf_counter()

    # 第 1 步：一次性读入整页
    s0 = Step(
        index=0,
        stage=obs.stage,
        thought="一次性读入整张页面，开始通读全部内容。",
        action=Action(
            type="see",
            target=RegionTarget(rect=Rect(x=0.0, y=0.0, w=1.0, h=1.0)),
            label="一次性读入整页",
        ),
        observation=obs.to_protocol(),
        timing=Timing(started_at=_now()),
    )
    steps.append(s0)
    yield StepEvent(step=s0)

    # 调真实模型：基于整页图直接作答
    from ap_engine.models.openai_compatible import OpenAICompatiblePolicy
    from ap_engine.models.prompts import build_oneshot_messages

    tokens: Optional[TokenUsage] = None
    try:
        policy = OpenAICompatiblePolicy(model_cfg)
        messages = build_oneshot_messages(intent, obs.full_path)
        text, tokens = await policy.chat(messages)
        conclusion = text.strip() or "（模型未给出结论）"
    except Exception as exc:  # noqa: BLE001
        conclusion = f"（模型调用失败：{exc}）"

    # 第 2 步：读完直接给结论
    s1 = Step(
        index=1,
        stage=obs.stage,
        thought=conclusion,
        action=Action(type="eos", label="OUTPUT: 读完整页直接作答"),
        observation=obs.to_protocol(),
        timing=Timing(started_at=_now()),
    )
    steps.append(s1)
    yield StepEvent(step=s1)

    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    stats = TrajectoryStats(
        total_steps=len(steps),
        action_counts=ActionCounts(see=1, eos=1),
        skipped_regions=0,
        tokens=tokens if tokens and tokens.total > 0 else None,
        duration_ms=total_ms,
        reached_eos=True,
    )
    result = TrajectoryResult(conclusion=conclusion, output=conclusion, stats=stats)
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
