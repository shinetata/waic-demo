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
# D0 长程深链（trader 专用）：财经列表 → 行情终端 → 财报 → 机构研报
_FINLIST_IMG, _FINLIST = _load_manifest("finance-list")
_MARKET_IMG, _MARKET = _load_manifest("market-data")
_REPORT_IMG, _REPORT = _load_manifest("report")
_CONSENSUS_IMG, _CONSENSUS = _load_manifest("consensus")

# D4 多源破案：3 个信息源 × 2 组案例（revenue 营收 / product 续航）
_ANNUAL_IMG, _ANNUAL = _load_manifest("src-annual")
_RESEARCH_IMG, _RESEARCH = _load_manifest("src-research")
_PRESS_IMG, _PRESS = _load_manifest("src-press")
_OFFICIAL_IMG, _OFFICIAL = _load_manifest("src-official")
_REVIEW_IMG, _REVIEW = _load_manifest("src-review")
_FORUM_IMG, _FORUM = _load_manifest("src-forum")


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
                prompt="帮我看看茅台明天还能不能加仓？",
                stages=[
                    _home_stage(
                        ["nav-finance", "banner", "section-finance", "item-finance", "market-card", "stock-mt", "hot-list"]
                    ),
                    StageSpec(
                        id="finance-list",
                        title="财经要闻列表",
                        image=_FINLIST_IMG,
                        elements=list(_FINLIST.values()),
                    ),
                    StageSpec(
                        id="detail",
                        title="财经详情页",
                        image=_TRADER_IMG,
                        elements=list(_TRADER.values()),
                    ),
                    StageSpec(
                        id="market-data",
                        title="专业行情终端",
                        image=_MARKET_IMG,
                        elements=list(_MARKET.values()),
                    ),
                    StageSpec(
                        id="report",
                        title="公司财报摘要",
                        image=_REPORT_IMG,
                        elements=list(_REPORT.values()),
                    ),
                    StageSpec(
                        id="consensus",
                        title="机构评级汇总",
                        image=_CONSENSUS_IMG,
                        elements=list(_CONSENSUS.values()),
                    ),
                ],
            ),
            "fan": RoleSpec(
                key="fan",
                persona="FAN · 球迷",
                prompt="国足今天踢日本了吧？帮我看看比分和进球情况。",
                stages=[
                    _home_stage(["nav-sports", "banner", "section-sports", "item-sports", "hot-list"]),
                    StageSpec(
                        id="detail",
                        title="体育详情页",
                        image=_FAN_IMG,
                        elements=list(_FAN.values()),
                    ),
                ],
            ),
        },
    ),
    # D4 多源破案：多源信息核查，source 间网状可回看（link.to 互相指向）
    "d4-investigation": SceneSpec(
        id="d4-investigation",
        title="多源破案 · D4",
        roles={
            "revenue": RoleSpec(
                key="revenue",
                persona="ANALYST · 财务分析师",
                prompt=(
                    "锐芯科技 2025 年的真实营收到底是多少？年报、券商研报、新闻报道三个来源"
                    "说法不一，请逐个核查每个来源的营收数字与口径，找出数字背后的真实口径，"
                    "并给出一致性解释。"
                ),
                stages=[
                    StageSpec(
                        id="src-annual",
                        title="证据 A · 年度报告",
                        image=_ANNUAL_IMG,
                        elements=list(_ANNUAL.values()),
                    ),
                    StageSpec(
                        id="src-research",
                        title="证据 B · 券商研报",
                        image=_RESEARCH_IMG,
                        elements=list(_RESEARCH.values()),
                    ),
                    StageSpec(
                        id="src-press",
                        title="证据 C · 新闻报道",
                        image=_PRESS_IMG,
                        elements=list(_PRESS.values()),
                    ),
                ],
            ),
            "product": RoleSpec(
                key="product",
                persona="REVIEWER · 产品评测编辑",
                prompt=(
                    "锐星 EV 的真实续航到底是多少？官网、媒体评测、车主论坛三个来源数据"
                    "差距很大，请逐个核查每个来源的续航数字与测试条件，找出差异原因，"
                    "并给出一致性解释。"
                ),
                stages=[
                    StageSpec(
                        id="src-official",
                        title="证据 A · 官方参数",
                        image=_OFFICIAL_IMG,
                        elements=list(_OFFICIAL.values()),
                    ),
                    StageSpec(
                        id="src-review",
                        title="证据 B · 媒体评测",
                        image=_REVIEW_IMG,
                        elements=list(_REVIEW.values()),
                    ),
                    StageSpec(
                        id="src-forum",
                        title="证据 C · 用户反馈",
                        image=_FORUM_IMG,
                        elements=list(_FORUM.values()),
                    ),
                ],
            ),
        },
    ),
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
