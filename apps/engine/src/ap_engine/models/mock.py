"""MockPolicy：无需网络/Key 的确定性策略，用于跑通闭环、前端联调与现场离线兜底。

支持多 stage：在 home（有可点击 link 的页面）先扫描分区/头条、跳过广告，再点击目标新闻进入详情；
在 detail 页对各语义区域 see、对关键区域 zoom-in、用 none 体现连续思考，最后 eos 给出结论。
"""

from __future__ import annotations

from typing import Optional

from ap_engine.models.base import PolicyDecision, PolicyInput, VisionPolicy
from ap_engine.environments.base import ElementSpec
from ap_protocol import Action, ElementTarget, Rect, RegionTarget

_KEY_KW = [
    "K线", "指标", "盘口", "净流入", "净利", "突破", "放量",
    "比分", "号码", "进球", "事件轴", "技术统计", "球场", "价格",
]
_SKIP_KW = ["广告", "无关", "banner", "推广"]


def _has(text: str, kws: list[str]) -> bool:
    return any(k in text for k in kws)


class MockPolicy(VisionPolicy):
    def __init__(self, config) -> None:
        super().__init__(config)
        self._cur_stage: Optional[str] = None
        self._plan: list[tuple[Action, str]] = []
        self._cursor = 0

    def _build_stage_plan(
        self, stage: str, elements: list[ElementSpec], goal_hint: str
    ) -> list[tuple[Action, str]]:
        links = [e for e in elements if e.kind == "link"]
        regions = [e for e in elements if e.kind != "link"]
        plan: list[tuple[Action, str]] = []

        if links:
            # 首页：扫描分区/头条/侧栏，跳过广告，最后点击目标新闻进入详情
            for e in regions:
                tag = e.label + (e.hint or "") + e.id
                if _has(tag, _SKIP_KW):
                    continue
                plan.append(
                    (
                        Action(type="see", target=ElementTarget(element_id=e.id), label=f"SEE {e.label}"),
                        f"首页扫到「{e.label}」。",
                    )
                )
            target = links[0]
            plan.append(
                (
                    Action(type="click", target=ElementTarget(element_id=target.id), label=f"CLICK {target.label}"),
                    f"锁定「{target.label}」，点击进入详情页。",
                )
            )
            return plan

        # 详情页：see 各区域 + 对关键区域 zoom-in + 一次连续思考 + eos
        first_zoom = False
        for e in regions:
            tag = e.label + (e.hint or "")
            plan.append(
                (
                    Action(type="see", target=ElementTarget(element_id=e.id), label=f"SEE {e.label}"),
                    f"查看「{e.label}」。",
                )
            )
            if _has(tag, _KEY_KW):
                r = e.rect
                w, h = r.w * 0.55, r.h * 0.55
                detail = Rect(x=r.x + r.w / 2 - w / 2, y=r.y + r.h / 2 - h / 2, w=w, h=h)
                plan.append(
                    (
                        Action(type="zoom_in", target=RegionTarget(rect=detail), label=f"ZOOM-IN {e.label}"),
                        f"「{e.label}」是关键信息，放大看清细节。",
                    )
                )
                if not first_zoom:
                    first_zoom = True
                    plan.append(
                        (Action(type="none", label="THINK"), "再多看两眼，确认这里的读数没有看错。")
                    )

        plan.append(
            (Action(type="eos", label="OUTPUT: 给出结论"), "关键信息已齐全，给出最终结论。")
        )
        return plan

    async def decide(self, inp: PolicyInput) -> PolicyDecision:
        stage = inp.observation.stage
        if stage != self._cur_stage:
            self._cur_stage = stage
            self._plan = self._build_stage_plan(stage, inp.observation.elements, inp.goal_hint)
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
