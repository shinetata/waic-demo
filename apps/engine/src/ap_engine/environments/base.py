"""环境抽象层：把"自建页面 / 大图"表征为主动感知微环境。

约定：所有坐标为归一化 [0,1]，相对整页/大图。环境每步产出
  - 全局缩略图（标注当前视野红框）
  - 当前视野局部高清裁剪（小区域放大，模拟"凑近看清"）
作为"先全局后局部"的观测表示喂给策略模型。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ap_protocol import Action, Observation, Rect
from PIL import Image, ImageDraw

THUMB_WIDTH = 720
CROP_MIN_WIDTH = 720
CROP_MAX_UPSCALE = 4.0


# ── 几何工具 ────────────────────────────────────────────────


def clamp_rect(r: Rect, min_size: float = 0.04) -> Rect:
    """把归一化矩形夹到 [0,1] 且保证最小尺寸，避免越界 / 空裁剪。"""
    w = max(min(r.w, 1.0), min_size)
    h = max(min(r.h, 1.0), min_size)
    x = min(max(r.x, 0.0), 1.0 - w)
    y = min(max(r.y, 0.0), 1.0 - h)
    return Rect(x=round(x, 4), y=round(y, 4), w=round(w, 4), h=round(h, 4))


def crop_norm(img: Image.Image, r: Rect) -> Image.Image:
    w_img, h_img = img.size
    box = (
        int(r.x * w_img),
        int(r.y * h_img),
        int((r.x + r.w) * w_img),
        int((r.y + r.h) * h_img),
    )
    return img.crop(box)


def fit_crop(img: Image.Image) -> Image.Image:
    """小裁剪放大到可读尺寸（模拟 zoom-in 看清细节）。"""
    if img.width < CROP_MIN_WIDTH and img.width > 0:
        scale = min(CROP_MIN_WIDTH / img.width, CROP_MAX_UPSCALE)
        img = img.resize(
            (int(img.width * scale), int(img.height * scale)), Image.LANCZOS
        )
    return img.convert("RGB")


def thumbnail_with_box(img: Image.Image, r: Rect) -> Image.Image:
    """全局低分缩略图 + 当前视野红框（帮助模型做空间定位）。"""
    w_img, h_img = img.size
    scale = THUMB_WIDTH / w_img
    thumb = img.resize((THUMB_WIDTH, int(h_img * scale)), Image.LANCZOS).convert("RGB")
    draw = ImageDraw.Draw(thumb)
    tw, th = thumb.size
    box = (
        int(r.x * tw),
        int(r.y * th),
        int((r.x + r.w) * tw),
        int((r.y + r.h) * th),
    )
    draw.rectangle(box, outline=(255, 60, 60), width=4)
    return thumb


def zoom_level_of(r: Rect) -> float:
    """以视野面积估算缩放倍数：1=全局，越大越近。"""
    area = max(r.w * r.h, 1e-4)
    return round(1.0 / (area**0.5), 2)


# ── 数据结构 ────────────────────────────────────────────────


@dataclass
class ElementSpec:
    """页面/大图中的语义元素（grounding 锚点）。"""

    id: str
    label: str
    rect: Rect
    kind: str = "region"  # region | link
    hint: Optional[str] = None
    to: Optional[str] = None  # link 的导航目标 stage（可选语义标注）


@dataclass
class StageSpec:
    """一个 stage（页面/视图），含主图与语义元素清单。"""

    id: str
    title: str
    image: str  # assets/pages 下的文件名
    elements: list[ElementSpec] = field(default_factory=list)

    def element(self, element_id: str) -> Optional[ElementSpec]:
        return next((e for e in self.elements if e.id == element_id), None)


@dataclass
class RoleSpec:
    key: str
    persona: str
    prompt: str
    stages: list[StageSpec]


@dataclass
class SceneSpec:
    id: str
    title: str
    roles: dict[str, RoleSpec]


@dataclass
class EnvObservation:
    """环境产出的当前微环境。"""

    stage: str
    rect: Rect
    zoom_level: float
    full_url: str
    thumb_url: str
    crop_url: str
    full_path: Path
    thumb_path: Path
    crop_path: Path
    elements: list[ElementSpec]

    def to_protocol(self) -> Observation:
        return Observation(
            stage=self.stage,
            full_image=self.full_url,
            thumbnail=self.thumb_url,
            crop_image=self.crop_url,
            rect=self.rect,
            zoom_level=self.zoom_level,
        )


# ── 接口 ────────────────────────────────────────────────────


class Environment(ABC):
    """主动感知环境接口。reset 进入初始微环境，step 执行动作产出新微环境。"""

    @abstractmethod
    def reset(self) -> EnvObservation: ...

    @abstractmethod
    def step(self, action: Action) -> EnvObservation: ...

    @property
    @abstractmethod
    def stage(self) -> str: ...

    @property
    @abstractmethod
    def elements(self) -> list[ElementSpec]: ...
