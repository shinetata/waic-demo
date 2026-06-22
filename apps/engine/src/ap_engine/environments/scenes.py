"""场景与角色定义（D0：新闻门户网页多 stage 主动感知）。

页面长图与 element manifest 由 tools/render_pages.py 生成（assets/pages + assets/manifests）。
每角色含两个 stage：home（首页）→ detail（详情页）。
模型流程：首页扫描分区/热搜 → 点击目标新闻 → 进入详情页多区域 see/zoom → EOS 给出产出。
"""

from __future__ import annotations

import json
from pathlib import Path

from ap_engine.environments.base import ElementSpec, RoleSpec, SceneSpec, StageSpec
from ap_protocol import Rect

_MANIFEST_DIR = Path(__file__).resolve().parents[3] / "assets" / "manifests"


def _load_manifest(name: str) -> tuple[str, dict[str, ElementSpec]]:
    data = json.loads((_MANIFEST_DIR / f"{name}.json").read_text(encoding="utf-8"))
    by_id: dict[str, ElementSpec] = {}
    for e in data["elements"]:
        by_id[e["id"]] = ElementSpec(
            id=e["id"],
            label=e["label"],
            rect=Rect(**e["rect"]),
            kind=e.get("kind", "region"),
            hint=e.get("hint"),
            to=e.get("to"),
        )
    return data["image"], by_id


_HOME_IMG, _HOME = _load_manifest("home")
_TRADER_IMG, _TRADER = _load_manifest("detail-trader")
_FAN_IMG, _FAN = _load_manifest("detail-fan")


def _pick(pool: dict[str, ElementSpec], ids: list[str]) -> list[ElementSpec]:
    return [pool[i] for i in ids if i in pool]


def _home_stage(item_ids: list[str]) -> StageSpec:
    return StageSpec(id="home", title="新闻门户首页", image=_HOME_IMG, elements=_pick(_HOME, item_ids))


SCENES: dict[str, SceneSpec] = {
    "d0-news-portal": SceneSpec(
        id="d0-news-portal",
        title="浏览器主动感知 · D0",
        roles={
            "trader": RoleSpec(
                key="trader",
                persona="TRADER · 短线交易员",
                prompt="帮我看看茅台明天还能不能加仓，从新闻门户上找找最新的财经消息和行情数据。",
                goal_hint="",
                stages=[
                    _home_stage(
                        ["nav-finance", "banner", "section-finance", "item-finance", "market-card", "stock-mt", "hot-list"]
                    ),
                    StageSpec(
                        id="detail",
                        title="财经详情页",
                        image=_TRADER_IMG,
                        elements=list(_TRADER.values()),
                    ),
                ],
                output="明日操作：试探性加仓。依据：长阳放量突破 1825 / 主力净流入 +18.3 亿 / 归母净利 268.5 亿超预期。",
            ),
            "fan": RoleSpec(
                key="fan",
                persona="FAN · 球迷",
                prompt="国足今天踢日本了吧？帮我看看比分和进球情况。",
                goal_hint="",
                stages=[
                    _home_stage(["nav-sports", "banner", "section-sports", "item-sports", "hot-list"]),
                    StageSpec(
                        id="detail",
                        title="体育详情页",
                        image=_FAN_IMG,
                        elements=list(_FAN.values()),
                    ),
                ],
                output="赛果：中国 1:0 日本 · 武磊 #7 · 87' 补射破门 · 上海体育场。下一步：转发球迷群并查看进球集锦。",
            ),
        },
    )
}


def list_scenes() -> list[dict]:
    return [
        {
            "id": s.id,
            "title": s.title,
            "roles": [
                {"key": r.key, "persona": r.persona, "prompt": r.prompt}
                for r in s.roles.values()
            ],
        }
        for s in SCENES.values()
    ]


def get_scene(scene_id: str) -> SceneSpec:
    if scene_id not in SCENES:
        raise KeyError(f"unknown scene: {scene_id}")
    return SCENES[scene_id]


def get_role(scene_id: str, role_key: str) -> RoleSpec:
    scene = get_scene(scene_id)
    if role_key not in scene.roles:
        raise KeyError(f"unknown role '{role_key}' in scene '{scene_id}'")
    return scene.roles[role_key]
