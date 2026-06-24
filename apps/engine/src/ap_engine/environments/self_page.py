"""SelfPageEnvironment：基于自建页面/大图资产的主动感知环境。

把一张整页长图/大图按动作裁剪/缩放，产出"全局缩略图(带视野框) + 当前局部高清"的微环境。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ap_engine.environments.base import (
    Environment,
    EnvObservation,
    StageSpec,
    clamp_rect,
    crop_norm,
    fit_crop,
    thumbnail_with_box,
    zoom_level_of,
)
from ap_engine.environments.scenes import get_role
from ap_protocol import Action, Rect
from PIL import Image

FULL_RECT = Rect(x=0.0, y=0.0, w=1.0, h=1.0)


class SelfPageEnvironment(Environment):
    def __init__(
        self,
        scene_id: str,
        role_key: str,
        *,
        assets_dir: str | Path,
        runtime_dir: str | Path,
        asset_base_url: str = "/assets",
        traj_id: str = "traj",
    ) -> None:
        self.scene_id = scene_id
        self.role_key = role_key
        self.role = get_role(scene_id, role_key)
        self.assets_dir = Path(assets_dir)
        self.pages_dir = self.assets_dir / "pages"
        self.asset_base_url = asset_base_url.rstrip("/")
        self.traj_id = traj_id

        self._stage_idx = 0
        self._rect = FULL_RECT
        self._step_no = 0
        self._img_cache: dict[Path, Image.Image] = {}

        self._run_dir = Path(runtime_dir) / traj_id
        self._run_dir.mkdir(parents=True, exist_ok=True)

    # ── 状态 ──
    @property
    def stage_spec(self) -> StageSpec:
        return self.role.stages[self._stage_idx]

    @property
    def stage(self) -> str:
        return self.stage_spec.id

    @property
    def elements(self):
        return self.stage_spec.elements

    @property
    def intent_prompt(self) -> str:
        return self.role.prompt

    # ── 图像 ──
    def _load(self) -> Image.Image:
        path = self.pages_dir / self.stage_spec.image
        if path not in self._img_cache:
            self._img_cache[path] = Image.open(path).convert("RGB")
        return self._img_cache[path]

    def _resolve_target_rect(self, action: Action) -> Optional[Rect]:
        t = action.target
        if t is None:
            return None
        if t.kind == "element":
            spec = self.stage_spec.element(t.element_id)
            return spec.rect if spec else None
        if t.kind == "region":
            return t.rect
        return None

    def _resolve_nav_target(self, action: Action) -> Optional[str]:
        """解析 click/navigate 的目标 stage id：优先 NavTarget.to，其次 link 元素的 to。

        用于多源破案的网状跳转/回看。D0 的 link.to 与 stage id 不一致时返回 None，
        由 step 回退到“前进下一页”逻辑，保持 D0 行为不变。
        """
        t = action.target
        if t is None:
            return None
        if t.kind == "nav":
            return t.to or None
        if t.kind == "element":
            spec = self.stage_spec.element(t.element_id)
            if spec is not None and spec.kind == "link" and spec.to:
                return spec.to
        return None

    # ── 闭环 ──
    def reset(self) -> EnvObservation:
        self._stage_idx = 0
        self._rect = FULL_RECT
        self._step_no = 0
        return self._observe()

    def step(self, action: Action) -> EnvObservation:
        self._step_no += 1
        a = action.type

        if a == "see":
            r = self._resolve_target_rect(action)
            if r:
                self._rect = clamp_rect(r)
        elif a == "zoom_in":
            r = self._resolve_target_rect(action)
            if r:
                self._rect = clamp_rect(r)
            else:  # 无 target：向当前视野中心收缩一半
                self._rect = clamp_rect(
                    Rect(
                        x=self._rect.x + self._rect.w * 0.25,
                        y=self._rect.y + self._rect.h * 0.25,
                        w=self._rect.w * 0.5,
                        h=self._rect.h * 0.5,
                    )
                )
        elif a == "zoom_out":
            r = self._resolve_target_rect(action)
            if r:
                self._rect = clamp_rect(r)
            else:  # 无 target：以当前中心放大一倍视野
                cx = self._rect.x + self._rect.w / 2
                cy = self._rect.y + self._rect.h / 2
                nw = min(self._rect.w * 2, 1.0)
                nh = min(self._rect.h * 2, 1.0)
                self._rect = clamp_rect(Rect(x=cx - nw / 2, y=cy - nh / 2, w=nw, h=nh))
        elif a == "scroll":
            r = self._resolve_target_rect(action)
            if r:  # 保持视野尺寸，平移到目标
                self._rect = clamp_rect(
                    Rect(x=r.x, y=r.y, w=self._rect.w, h=self._rect.h)
                )
        elif a == "snapshot":
            self._rect = FULL_RECT
        elif a in ("click", "navigate"):
            target_stage = self._resolve_nav_target(action)
            jumped = False
            if target_stage is not None:
                # 多源网状跳转：按 stage id 查找，支持前进与回退
                for idx, st in enumerate(self.role.stages):
                    if st.id == target_stage:
                        self._stage_idx = idx
                        self._rect = FULL_RECT
                        jumped = True
                        break
            # 无显式目标 / 目标 stage 未找到 → 回退到前进下一页（兼容 D0）
            if not jumped and self._stage_idx + 1 < len(self.role.stages):
                self._stage_idx += 1
                self._rect = FULL_RECT
        # a == "none": 连续思考，不改变视野
        # a == "eos": 终止由 loop 处理

        return self._observe()

    def _observe(self) -> EnvObservation:
        img = self._load()
        rect = self._rect
        crop = fit_crop(crop_norm(img, rect))
        thumb = thumbnail_with_box(img, rect)

        stem = f"{self.stage}_{self._step_no:02d}"
        crop_path = self._run_dir / f"{stem}_crop.jpg"
        thumb_path = self._run_dir / f"{stem}_thumb.jpg"
        crop.save(crop_path, quality=88)
        thumb.save(thumb_path, quality=85)

        def runtime_url(p: Path) -> str:
            return f"{self.asset_base_url}/runtime/{self.traj_id}/{p.name}"

        return EnvObservation(
            stage=self.stage,
            rect=rect,
            zoom_level=zoom_level_of(rect),
            full_url=f"{self.asset_base_url}/pages/{self.stage_spec.image}",
            thumb_url=runtime_url(thumb_path),
            crop_url=runtime_url(crop_path),
            full_path=self.pages_dir / self.stage_spec.image,
            thumb_path=thumb_path,
            crop_path=crop_path,
            elements=self.elements,
        )
