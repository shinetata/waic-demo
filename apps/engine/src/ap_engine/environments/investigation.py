"""InvestigationEnvironment：D4 多源破案环境。

在 SelfPageEnvironment 之上，把多个信息源(stage)组织成可自由互跳的卷宗：
click/navigate 按目标 stage id 解析（支持回看已访问过的源），其余
see/zoom/scroll/snapshot/none 完全复用父类的"全局缩略图 + 局部高清"裁剪逻辑。

这是 D4 相对 D0 唯一的新机制——D0 是线性 idx+1 逐页深入，D4 需要"读到 B 发现
与 A 矛盾 → 主动 navigate 回 A → zoom 脚注"的回看高潮。
"""

from __future__ import annotations

from typing import Optional

from ap_engine.environments.self_page import FULL_RECT, SelfPageEnvironment
from ap_protocol import Action


class InvestigationEnvironment(SelfPageEnvironment):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # stage id → 索引（用于按 id 自由跳转/回看）
        self._stage_by_id: dict[str, int] = {
            s.id: i for i, s in enumerate(self.role.stages)
        }
        self._visited: set[str] = {self.stage}

    @property
    def visited(self) -> set[str]:
        return set(self._visited)

    def reset(self):
        obs = super().reset()
        self._visited = {self.stage}
        return obs

    def _target_stage_id(self, action: Action) -> Optional[str]:
        """从动作解析目标 stage id：nav 直接取 to；element 取其 link 的 to。"""
        t = action.target
        if t is None:
            return None
        kind = getattr(t, "kind", None)
        if kind == "nav":
            return t.to
        if kind == "element":
            spec = self.stage_spec.element(t.element_id)
            if spec is not None and spec.to:
                return spec.to
        return None

    def step(self, action: Action):
        if action.type in ("click", "navigate"):
            self._step_no += 1
            to = self._target_stage_id(action)
            if to is not None and to in self._stage_by_id:
                self._stage_idx = self._stage_by_id[to]
                self._rect = FULL_RECT
                self._visited.add(self.stage)
            # 未解析到合法目标：保持当前视野，不前进（等待模型重试更明确的目标）
            return self._observe()
        return super().step(action)
