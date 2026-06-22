"""场景与角色定义（阶段一：基于真实实景大图的图像主动感知）。

注：dense 大图为实景照片（交易桌 / 足球赛）。这里据图像真实内容标注语义兴趣点，
作为 element grounding 锚点；真实模型也可自由用 region 坐标。
web 阶段会另建"新闻门户网页"并用 Playwright 截长图作为 d0 的核心叙事场景。
"""

from __future__ import annotations

from ap_engine.environments.base import ElementSpec, RoleSpec, SceneSpec, StageSpec
from ap_protocol import Rect


def _el(
    eid: str, label: str, x: float, y: float, w: float, h: float, hint: str | None = None
) -> ElementSpec:
    return ElementSpec(id=eid, label=label, rect=Rect(x=x, y=y, w=w, h=h), hint=hint)


TRADER_DESK = StageSpec(
    id="desk",
    title="交易桌实景",
    image="trader.jpg",
    elements=[
        _el("main_chart", "中央主屏 · K线主图", 0.30, 0.10, 0.29, 0.30, "日内分时/K线走势与放量"),
        _el("laptop_quotes", "左侧笔记本 · 行情涨跌表", 0.00, 0.12, 0.22, 0.30, "红绿涨跌的个股报价"),
        _el("order_panel", "主屏右侧 · 交易/盘口面板", 0.58, 0.10, 0.11, 0.30, "买卖盘口与下单区"),
        _el("right_screen", "右侧屏 · 行情列表(蓝光)", 0.67, 0.00, 0.30, 0.40, "自选股列表与指数"),
        _el("tablet_chart", "桌面平板 · K线(黄圈标注)", 0.34, 0.60, 0.30, 0.32, "被圈出的关键形态"),
        _el("keyboard", "键盘区", 0.40, 0.50, 0.30, 0.16, "操作输入区(无行情信息)"),
    ],
)

FAN_MATCH = StageSpec(
    id="match",
    title="足球比赛实景",
    image="fan.jpg",
    elements=[
        _el("attacker", "白衣持球球员(12号)", 0.33, 0.26, 0.21, 0.58, "正在带球突破的进攻球员"),
        _el("defender", "深色球衣防守球员", 0.55, 0.20, 0.18, 0.62, "上前逼抢的防守球员"),
        _el("ball", "地面足球", 0.45, 0.74, 0.13, 0.17, "比赛用球的位置"),
        _el("jersey12", "白衣球员号码(12)", 0.42, 0.45, 0.10, 0.11, "确认球员号码"),
        _el("captain", "右上 · 队长(袖标)", 0.82, 0.05, 0.15, 0.52, "远处接应球员"),
        _el("bench", "左侧 · 替补/训练衣球员", 0.00, 0.16, 0.17, 0.72, "场边粉色训练衣球员"),
    ],
)


SCENES: dict[str, SceneSpec] = {
    "d0-news-portal": SceneSpec(
        id="d0-news-portal",
        title="浏览器主动感知 · D0",
        roles={
            "trader": RoleSpec(
                key="trader",
                persona="TRADER · 短线交易员",
                prompt="盘后复盘我的交易桌：扫描各屏幕的行情与 K 线，判断今天的主线异动和资金强弱。",
                goal_hint="优先看中央主屏 K 线走势与放量，再核对左侧笔记本的涨跌表，必要时放大确认；跳过键盘等无信息区域。",
                stages=[TRADER_DESK],
            ),
            "fan": RoleSpec(
                key="fan",
                persona="FAN · 球迷",
                prompt="看这场足球比赛：找出持球进攻的球员、球衣号码、球的位置和攻防态势。",
                goal_hint="优先锁定持球的白衣球员并放大确认号码，再看防守球员与球的位置；跳过场边与远景。",
                stages=[FAN_MATCH],
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
