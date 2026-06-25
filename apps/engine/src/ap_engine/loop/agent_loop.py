"""Agent Loop：主动感知闭环。

意图 → 微环境 → 模型推 (思考, 动作) → 环境执行 → 新微环境 → … → EOS。
流式 yield StreamEvent（供 WebSocket 边推边播），并把完整轨迹落盘（回放 / 兜底）。
含最大步数预算与防重复（卡死保护）。
"""

from __future__ import annotations

import datetime
import json
import logging
import time
import uuid
from pathlib import Path
from typing import AsyncGenerator, Optional

from ap_engine.config import Settings, get_settings
from ap_engine.environments import get_role, make_environment
from ap_engine.models import PolicyInput, make_policy
from ap_engine.models.prompts import build_investigation_final_messages
from ap_engine.storage import save_trajectory
from ap_protocol import (
    Action,
    ActionCounts,
    ElementTarget,
    Intent,
    ModelInfo,
    NavTarget,
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

_logger = logging.getLogger(__name__)

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


_OBSERVE_TYPES = ("see", "zoom_in", "zoom_out", "snapshot")


def _rect_overlap_ratio(a: Rect, b: Rect) -> float:
    x1 = max(a.x, b.x)
    y1 = max(a.y, b.y)
    x2 = min(a.x + a.w, b.x + b.w)
    y2 = min(a.y + a.h, b.y + b.h)
    iw = max(x2 - x1, 0)
    ih = max(y2 - y1, 0)
    inter = iw * ih
    denom = max(min(a.w * a.h, b.w * b.h), 1e-6)
    return inter / denom


def _stage_by_id(role_spec) -> dict[str, object]:
    return {st.id: st for st in role_spec.stages}


def _element_has_suffix(element_id: str, suffix: str) -> bool:
    return element_id.endswith(f"-{suffix}") or suffix in element_id


def _target_hits_element(action: Action, stage_spec, suffix: str) -> bool:
    if action.type not in _OBSERVE_TYPES:
        return False
    target = action.target
    if target is None:
        return action.type == "snapshot" and suffix == "keyvalue"
    if target.kind == "element":
        return _element_has_suffix(target.element_id, suffix)
    if target.kind != "region":
        return False
    return any(
        _element_has_suffix(e.id, suffix) and _rect_overlap_ratio(target.rect, e.rect) >= 0.25
        for e in stage_spec.elements
    )


def _observes_value(action: Action, stage_spec) -> bool:
    if _target_hits_element(action, stage_spec, "keyvalue"):
        return True
    target = action.target
    if action.type not in _OBSERVE_TYPES or target is None or target.kind != "element":
        return False
    eid = target.element_id
    return not (
        _element_has_suffix(eid, "footnote")
        or _element_has_suffix(eid, "header")
        or "-to-" in eid
    )


def _observes_footnote(action: Action, stage_spec) -> bool:
    return _target_hits_element(action, stage_spec, "footnote")


def _semantic_target(stage_spec, suffix: str) -> Optional[ElementTarget]:
    for e in stage_spec.elements:
        if _element_has_suffix(e.id, suffix):
            return ElementTarget(element_id=e.id)
    return None


def _nav_target_stage(action: Action, stage_spec) -> Optional[str]:
    target = action.target
    if target is None:
        return None
    if target.kind == "nav":
        return target.to
    if target.kind == "element":
        spec = stage_spec.element(target.element_id)
        if spec is not None and spec.kind == "link" and spec.to:
            return spec.to
    return None


def _next_unverified_stage(ledger: dict, current_stage: str) -> Optional[str]:
    for sid in ledger.get("unverified", []):
        if sid != current_stage:
            return sid
    if ledger.get("unverified"):
        return ledger["unverified"][0]
    return None


def _detect_source_cycle(history: list[Step], window: int = 6) -> bool:
    if len(history) < window:
        return False
    stages = [s.stage for s in history[-window:]]
    if len(set(stages)) != 2:
        return False
    return all(stages[i] == stages[i % 2] for i in range(window))


def _target_summary(action: Action) -> str:
    target = action.target
    if target is None:
        return ""
    if target.kind == "element":
        return target.element_id
    if target.kind == "nav":
        return target.to
    if target.kind == "region":
        r = target.rect
        return f"region({r.x:.3f},{r.y:.3f},{r.w:.3f},{r.h:.3f})"
    return ""


def _investigation_ledger(history: list[Step], role_spec) -> dict:
    """多源破案的证据账本：从历史核查记录算出每个来源的核查进度。

    某来源已核查(verified) = 看过它的关键数字（任一非脚注语义区/region 细看）
    且放大确认过它的脚注口径（对 -footnote 的观察）。判定只依赖 step 已记录的
    stage + 元素 id 后缀（-keyvalue / -footnote 等），不改协议。返回：
      {"sources": {sid: {title, seen_value, zoomed_footnote, verified}},
       "order": [...], "unverified": [...], "all_verified": bool}
    """
    sources: dict[str, dict] = {}
    order: list[str] = []
    for st in role_spec.stages:
        sources[st.id] = {
            "title": st.title,
            "seen_value": False,
            "zoomed_footnote": False,
            "verified": False,
        }
        order.append(st.id)
    stages = _stage_by_id(role_spec)
    for s in history:
        src = sources.get(s.stage)
        if src is None or s.action.type not in _OBSERVE_TYPES:
            continue
        stage_spec = stages.get(s.stage)
        if stage_spec is None:
            continue
        if _observes_footnote(s.action, stage_spec):
            src["zoomed_footnote"] = True
        if _observes_value(s.action, stage_spec):
            src["seen_value"] = True
    for sid in order:
        sources[sid]["verified"] = sources[sid]["seen_value"] and sources[sid]["zoomed_footnote"]
    unverified = [sid for sid in order if not sources[sid]["verified"]]
    return {
        "sources": sources,
        "order": order,
        "unverified": unverified,
        "all_verified": bool(order) and not unverified,
    }


def _guard_investigation_action(
    action: Action,
    thought: str,
    obs,
    role_spec,
    ledger: dict,
) -> tuple[Action, str, Optional[str]]:
    """D4 行为防护栏：不替模型答题，只阻止明显破坏证据闭环的动作。"""
    sources = ledger.get("sources", {})
    cur = sources.get(obs.stage)
    stages = _stage_by_id(role_spec)
    stage_spec = stages.get(obs.stage)
    if cur is None or stage_spec is None:
        return action, thought, None

    if not cur["verified"]:
        if not cur["seen_value"] and not _observes_value(action, stage_spec):
            target = _semantic_target(stage_spec, "keyvalue")
            if target is not None:
                guarded = Action(
                    type="see",
                    target=target,
                    label="SEE: 核查当前来源关键数字",
                )
                return (
                    guarded,
                    "证据账本显示当前来源的关键数字尚未确认，先读取关键数字再跳转。",
                    "force_current_value",
                )
        if cur["seen_value"] and not cur["zoomed_footnote"] and not _observes_footnote(
            action, stage_spec
        ):
            target = _semantic_target(stage_spec, "footnote")
            if target is not None:
                guarded = Action(
                    type="zoom_in",
                    target=target,
                    label="ZOOM: 放大脚注确认口径",
                )
                return (
                    guarded,
                    "关键数字已确认，但口径脚注尚未核查，先放大脚注找出差异原因。",
                    "force_current_footnote",
                )
        return action, thought, None

    if ledger.get("all_verified"):
        return action, thought, None

    next_sid = _next_unverified_stage(ledger, obs.stage)
    target_sid = _nav_target_stage(action, stage_spec)
    if target_sid and sources.get(target_sid, {}).get("verified") and next_sid:
        guarded = Action(
            type="navigate",
            target=NavTarget(to=next_sid),
            label="NAVIGATE: 前往未核查来源",
        )
        return (
            guarded,
            "目标来源已经核查完成，转向证据账本中仍未完成的来源。",
            "redirect_verified_target",
        )

    if action.type in _OBSERVE_TYPES and next_sid and next_sid != obs.stage:
        guarded = Action(
            type="navigate",
            target=NavTarget(to=next_sid),
            label="NAVIGATE: 前往未核查来源",
        )
        return (
            guarded,
            "当前来源已经核查完成，继续前往未核查来源，避免重复观察。",
            "leave_verified_source",
        )
    return action, thought, None


async def _finalize_investigation(policy, intent, history: list[Step], ledger: dict, reason: str):
    messages = build_investigation_final_messages(intent, history, ledger)
    fallback = history[-1].thought if history else "证据已核查完成，给出一致性结论。"
    tokens = None
    try:
        if hasattr(policy, "chat"):
            text, tokens = await policy.chat(messages)
        else:
            text = fallback
    except Exception as exc:  # noqa: BLE001
        text = f"{fallback}（最终总结调用失败，按已观察证据收尾：{exc}）"
    conclusion = text.strip() or fallback
    return (
        conclusion,
        Action(type="eos", label=f"OUTPUT: {conclusion}", reason=reason),
        tokens,
    )


def _finalize_reason(ledger: dict, history: list[Step], step_index: int, max_steps: int) -> Optional[str]:
    if not history:
        return None
    if ledger.get("all_verified"):
        if _detect_source_cycle(history):
            return "cycle_finalized"
        if step_index >= max_steps - 3:
            return "budget_finalized"
        return "all_verified"
    return None


def _log_d4_step(
    traj_id: str,
    step: Step,
    ledger: Optional[dict],
    guard_reason: Optional[str] = None,
    termination_reason: Optional[str] = None,
) -> None:
    payload = {
        "trajectory_id": traj_id,
        "step": step.index,
        "stage": step.stage,
        "action": step.action.type,
        "target": _target_summary(step.action),
        "guard_reason": guard_reason,
        "termination_reason": termination_reason,
        "ledger": ledger,
    }
    _logger.info("d4_loop %s", json.dumps(payload, ensure_ascii=False))


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
    termination_reason = "max_steps"
    guard_events: list[str] = []
    cycle_detected = False
    t0 = time.perf_counter()
    max_steps = settings.max_steps
    # 多源破案：每步计算证据账本并注入提示，作为唯一的行为引导（不改写动作/思考）
    is_inv = scene == "d4-investigation"

    for i in range(max_steps):
        # 多源破案：每步算证据账本，仅注入提示引导模型（不据此改写任何动作/思考）
        ledger = _investigation_ledger(steps, role_spec) if is_inv else None
        if is_inv and ledger is not None:
            cycle_detected = cycle_detected or _detect_source_cycle(steps)
            final_reason = _finalize_reason(ledger, steps, i, max_steps)
            if final_reason:
                s0 = time.perf_counter()
                thought, action, final_tokens = await _finalize_investigation(
                    policy, intent, steps, ledger, final_reason
                )
                dur_ms = round((time.perf_counter() - s0) * 1000, 1)
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
                if final_tokens:
                    tokens.prompt += final_tokens.prompt
                    tokens.completion += final_tokens.completion
                    tokens.total += final_tokens.total
                reached_eos = True
                termination_reason = final_reason
                _log_d4_step(traj_id, step, ledger, termination_reason=final_reason)
                yield StepEvent(step=step)
                break
        inp = PolicyInput(
            intent=intent,
            step_index=i,
            max_steps=max_steps,
            history=steps,
            observation=obs,
            scene_id=scene,
            ledger=ledger,
        )
        s0 = time.perf_counter()
        decision = await policy.decide(inp)
        dur_ms = round((time.perf_counter() - s0) * 1000, 1)

        action = decision.action
        thought = decision.thought  # 始终用模型原话，循环不再盖写动作/思考
        guard_reason = None
        if is_inv and ledger is not None:
            action, thought, guard_reason = _guard_investigation_action(
                action, thought, obs, role_spec, ledger
            )
            if guard_reason:
                guard_events.append(f"#{i}:{obs.stage}:{guard_reason}")
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

        if is_inv:
            _log_d4_step(traj_id, step, ledger, guard_reason=guard_reason)
        yield StepEvent(step=step)

        if action.type == "eos":
            reached_eos = True
            termination_reason = "model_eos"
            break

        # 卡死保护：连续相同的非 none 动作累计达阈值才终止（给模型自我纠正空间）
        if sig == prev_sig and action.type != "none":
            repeat += 1
            if repeat >= 3:
                # 反复纠结同一动作：D0 末页（无链接）或多源场景（已核查来源池）视为完成
                if scene == "d4-investigation" or not any(e.kind == "link" for e in obs.elements):
                    reached_eos = True
                    termination_reason = "repeat_guard"
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
    # 产出用模型自己给出的真实结论（eos 的 label/thought），不再使用任何预设文案
    final_output = None
    if last is not None and last.action.type == "eos":
        label = (last.action.label or "").strip()
        if label.upper().startswith("OUTPUT:"):
            label = label.split(":", 1)[1].strip()
        final_output = label or last.thought
    final_ledger = _investigation_ledger(steps, role_spec) if is_inv else None
    result = TrajectoryResult(
        conclusion=last.thought if last else None,
        output=final_output,
        stats=stats,
        termination_reason=termination_reason,
        diagnostics=(
            {
                "ledger": final_ledger,
                "guard_events": guard_events,
                "cycle_detected": cycle_detected,
            }
            if is_inv
            else None
        ),
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
    from ap_engine.models.prompts import build_oneshot_messages, build_oneshot_multisource_messages

    tokens: Optional[TokenUsage] = None
    try:
        policy = OpenAICompatiblePolicy(model_cfg)
        if scene == "d4-investigation":
            # 多源对照：把所有来源整图一次性喂入，期望被矛盾数字迷惑
            pages_dir = Path(settings.assets_dir) / "pages"
            image_paths = [pages_dir / st.image for st in role_spec.stages]
            messages = build_oneshot_multisource_messages(intent, image_paths)
        else:
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
