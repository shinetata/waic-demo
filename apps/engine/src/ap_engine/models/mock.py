"""MockPolicy：无需网络/Key 的确定性策略，用于跑通闭环、前端联调与现场离线兜底。

支持任意长度的多 stage 深链：每到一页先扫看若干关键区域，对 manifest 标注"需放大"的
小字/关键数字做 zoom-in 确认；只要本页还有 [链接] 元素就 click 进入下一页继续核查，直到
走到链路末端（无链接的页面）才用 none 连续思考并 eos 给出综合结论。每页限量浏览，确保
长链总步数控制在步数预算内。
"""

from __future__ import annotations

from typing import Optional

from ap_engine.models.base import PolicyDecision, PolicyInput, VisionPolicy
from ap_engine.environments.base import ElementSpec
from ap_protocol import Action, ElementTarget, Rect, RegionTarget

_SKIP_KW = ["广告", "无关", "banner", "推广"]
# 每页普通区域最多浏览数（标注"需放大"的关键区域不受此限，始终查看并 zoom）
_BROWSE_LIMIT = 3


def _has(text: str, kws: list[str]) -> bool:
    return any(k in text for k in kws)


def _is_key(e: ElementSpec) -> bool:
    """是否为需要放大确认的关键小字/数字（由 manifest 的 hint 含"放大"标注驱动）。"""
    return bool(e.hint and "放大" in e.hint)


class MockPolicy(VisionPolicy):
    def __init__(self, config) -> None:
        super().__init__(config)
        self._cur_stage: Optional[str] = None
        self._plan: list[tuple[Action, str]] = []
        self._cursor = 0

    def _build_stage_plan(
        self, stage: str, elements: list[ElementSpec]
    ) -> list[tuple[Action, str]]:
        links = [e for e in elements if e.kind == "link"]
        regions = [e for e in elements if e.kind != "link"]
        plan: list[tuple[Action, str]] = []

        shown = 0
        for e in regions:
            tag = e.label + (e.hint or "") + e.id
            if _has(tag, _SKIP_KW):
                continue
            key = _is_key(e)
            if shown >= _BROWSE_LIMIT and not key:
                continue
            plan.append(
                (
                    Action(type="see", target=ElementTarget(element_id=e.id), label=f"SEE {e.label}"),
                    f"查看「{e.label}」。",
                )
            )
            shown += 1
            if key:
                r = e.rect
                w, h = r.w * 0.6, r.h * 0.6
                detail = Rect(x=r.x + r.w / 2 - w / 2, y=r.y + r.h / 2 - h / 2, w=w, h=h)
                plan.append(
                    (
                        Action(type="zoom_in", target=RegionTarget(rect=detail), label=f"ZOOM-IN {e.label}"),
                        f"「{e.label}」是关键数字，放大看清细节。",
                    )
                )

        if links:
            # 中间页：本页关键信息看过后，点击 [链接] 进入下一页继续核查
            target = links[0]
            plan.append(
                (
                    Action(type="click", target=ElementTarget(element_id=target.id), label=f"CLICK {target.label}"),
                    f"本页关键信息已看过，点击「{target.label}」进入下一页继续核查。",
                )
            )
        else:
            # 末端页：无可进入的链接，连续思考并给出综合结论
            plan.append(
                (Action(type="none", label="THINK"), "已走到信息链末端，综合沿途各页的关键证据。")
            )
            plan.append(
                (Action(type="eos", label="OUTPUT: 给出综合结论"), "多源证据齐全且无重大矛盾，给出最终结论。")
            )
        return plan

    async def decide(self, inp: PolicyInput) -> PolicyDecision:
        stage = inp.observation.stage
        if stage != self._cur_stage:
            self._cur_stage = stage
            self._plan = self._build_stage_plan(stage, inp.observation.elements)
            self._cursor = 0

        if self._cursor < len(self._plan):
            action, thought = self._plan[self._cursor]
            self._cursor += 1
        else:
            action, thought = (
                Action(type="eos", label="OUTPUT: 结束"),
                "信息已足够，结束观察。",
            )
        return PolicyDecision(thought=thought, action=action, tokens=None, raw="(mock)")
