"""构建期脚本：用 Playwright 把自建新闻门户页面渲染成整页长图，
并按预定义语义 id 导出归一化 element manifest，供 D0 多 stage 主动感知环境使用。

用法：uv run --with playwright python tools/render_pages.py
产物：assets/pages/{home,detail-trader,detail-fan}.png + assets/manifests/*.json
（运行时引擎只读这些产物，不依赖 playwright）
"""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "assets" / "site"
PAGES = ROOT / "assets" / "pages"
MANIFESTS = ROOT / "assets" / "manifests"
PAGES.mkdir(parents=True, exist_ok=True)
MANIFESTS.mkdir(parents=True, exist_ok=True)

# 每页：源文件 + 语义元素清单 (id -> (label, kind, hint, to))
# kind: link=可点击导航(to=目标stage) / region=可观察区域
PAGESPEC: dict[str, dict] = {
    "home": {
        "file": "home.html",
        "elements": {
            "nav-finance": ("导航 · 财经", "region", "频道入口", None),
            "nav-sports": ("导航 · 体育", "region", "频道入口", None),
            "banner": ("顶部推广 banner", "region", "广告，与意图无关", None),
            "section-finance": ("财经要闻 分区", "region", "财经新闻聚集区", None),
            "item-finance": ("头条：茅台大涨3.2%", "link", "点击进入财经详情页", "detail-trader"),
            "section-sports": ("体育快讯 分区", "region", "体育新闻聚集区", None),
            "item-sports": ("头条：国足1:0日本", "link", "点击进入体育详情页", "detail-fan"),
            "item-tech": ("科技：GPT-5 发布", "link", "科技新闻", None),
            "market-card": ("侧栏 · 实时行情", "region", "指数与个股报价", None),
            "stock-mt": ("行情行 · 贵州茅台 +3.21%", "region", "个股报价核对", None),
            "hot-list": ("侧栏 · 热搜榜", "region", "实时热点话题", None),
        },
    },
    "detail-trader": {
        "file": "trader.html",
        "elements": {
            "trader-chart": ("K线主图", "region", "日内分时走势与放量", None),
            "indicator-strip": ("指标条 MA/RSI/MACD/主力净流入", "region", "密集技术指标", None),
            "l2-book": ("五档盘口 LV2", "region", "买卖盘价量", None),
            "breakout-label": ("标注：长阳放量突破", "region", "关键形态信号", None),
            "price-box": ("实时价格卡", "region", "现价/开高低/成交额", None),
            "lead-inflow": ("正文：主力净流入18亿", "region", "资金面线索", None),
            "para-eps": ("正文：归母净利268.5亿", "region", "基本面线索", None),
        },
    },
    "detail-fan": {
        "file": "fan.html",
        "elements": {
            "scoreboard": ("比分卡 中国1:0日本", "region", "比分与赛事", None),
            "match-stats": ("全场技术统计", "region", "控球/射门/传球等", None),
            "pitch": ("迷你球场 · 进球示意", "region", "传球路线与进球点", None),
            "goal-flash": ("GOAL 标注", "region", "进球瞬间", None),
            "player-card": ("武磊人物卡", "region", "球员信息与数据", None),
            "jersey7": ("球衣号码 7", "region", "确认进球者号码", None),
            "timeline": ("90分钟事件轴", "region", "23'黄/67'换/87'进球", None),
            "score-box": ("正文比分卡 1:0", "region", "比分确认", None),
            "result": ("正文：1:0力克日本", "region", "赛果", None),
            "goal-detail": ("正文：87'武磊补射破门", "region", "进球者/时间", None),
        },
    },
}

_BBOX_JS = """(sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return { x: r.left + window.scrollX, y: r.top + window.scrollY, w: r.width, h: r.height };
}"""


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        for name, spec in PAGESPEC.items():
            page = browser.new_page(viewport={"width": 1120, "height": 900}, device_scale_factor=2)
            page.goto((SITE / spec["file"]).as_uri(), wait_until="networkidle")
            page.wait_for_timeout(600)  # 等待 K线等内联脚本渲染
            dims = page.evaluate(
                "() => ({ w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight })"
            )
            full_w, full_h = float(dims["w"]), float(dims["h"])
            page.screenshot(path=str(PAGES / f"{name}.png"), full_page=True)

            elements = []
            for sel, (label, kind, hint, to) in spec["elements"].items():
                box = page.evaluate(_BBOX_JS, f"#{sel}")
                if not box or box["w"] <= 0:
                    print(f"  [warn] {name}: #{sel} not found / zero size")
                    continue
                rect = {
                    "x": round(box["x"] / full_w, 4),
                    "y": round(box["y"] / full_h, 4),
                    "w": round(box["w"] / full_w, 4),
                    "h": round(box["h"] / full_h, 4),
                }
                el = {"id": sel, "label": label, "kind": kind, "hint": hint, "rect": rect}
                if to:
                    el["to"] = to
                elements.append(el)

            manifest = {
                "stage": name,
                "image": f"{name}.png",
                "width": int(full_w),
                "height": int(full_h),
                "elements": elements,
            }
            (MANIFESTS / f"{name}.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"  rendered {name}.png ({int(full_w)}x{int(full_h)}) + {len(elements)} elements")
            page.close()
        browser.close()
    print("done.")


if __name__ == "__main__":
    main()
