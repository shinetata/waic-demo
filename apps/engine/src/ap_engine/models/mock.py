"""MockPolicy：无需网络/Key 的确定性策略，用于跑通闭环、前端联调与现场离线兜底。

按当前微环境的语义元素清单产出一条"有选择性"的主动感知轨迹：
扫看高价值元素、对关键元素 zoom-in 看细节、用 none 体现连续思考、跳过无关区域、最后 eos。
"""

from __future__ import annotations

from typing import Optional

from ap_engine.models.base import PolicyDecision, PolicyInput, VisionPolicy
from ap_engine.environments.base import ElementSpec
from ap_protocol import Action, ElementTarget, Rect, RegionTarget

_KEY_KW = ["K线", "走势", "放量", "盘口", "主屏", "号码", "号", "球", "进球", "比分"]
_SKIP_KW = ["无信息", "无行情", "键盘", "无关"]


def _has(text: str, kws: list[str]) -> bool:
    return any(k in text for k in kws)


class MockPolicy(VisionPolicy):
    def __init__(self, config) -> None:
        super().__init__(config)
        self._plan: Optional[list[tuple[Action, str]]] = None

    def _build_plan(
        self, elements: list[ElementSpec], goal_hint: str
    ) -> list[tuple[Action, str]]:
        plan: list[tuple[Action, str]] = []
        kept = [e for e in elements if not _has(e.label + (e.hint or ""), _SKIP_KW)]
        skipped = [e for e in elements if e not in kept]

        first_key_done = False
        for e in kept:
            tag = e.label + (e.hint or "")
            plan.append(
                (
                    Action(type="see", target=ElementTarget(element_id=e.id), label=f"SEE {e.label}"),
                    f"扫到「{e.label}」，先看个大概。",
                )
            )
            if _has(tag, _KEY_KW):
                r = e.rect
                w, h = r.w * 0.45, r.h * 0.45
                detail = Rect(x=r.x + r.w / 2 - w / 2, y=r.y + r.h / 2 - h / 2, w=w, h=h)
                plan.append(
                    (
                        Action(type="zoom_in", target=RegionTarget(rect=detail), label=f"ZOOM-IN {e.label}"),
                        f"「{e.label}」是关键信息，放大看清细节。",
                    )
                )
                if not first_key_done:
                    first_key_done = True
                    plan.append(
                        (
                            Action(type="none", label="THINK"),
                            "再多看两眼，确认这里的读数没有看错。",
                        )
                    )

        if skipped:
            names = "、".join(e.label for e in skipped)
            plan.append(
                (
                    Action(type="snapshot", label="SNAPSHOT overview"),
                    f"其余区域（{names}）与意图无关，跳过，回看全局确认没有遗漏。",
                )
            )

        plan.append(
            (
                Action(type="eos", label="OUTPUT: 已获取关键信息"),
                f"信息已足够：{goal_hint}",
            )
        )
        return plan

    async def decide(self, inp: PolicyInput) -> PolicyDecision:
        if self._plan is None:
            self._plan = self._build_plan(inp.observation.elements, inp.goal_hint)
        if inp.step_index < len(self._plan):
            action, thought = self._plan[inp.step_index]
        else:
            action, thought = (
                Action(type="eos", label="OUTPUT: 结束"),
                "信息已足够，结束观察。",
            )
        return PolicyDecision(thought=thought, action=action, tokens=None, raw="(mock)")
