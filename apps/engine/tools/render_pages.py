"""构建期脚本：用 Playwright 把自建新闻门户页面渲染成整页长图，
并按预定义语义 id 导出归一化 element manifest，供 D0 多 stage 主动感知环境使用。

用法：uv run --with playwright python tools/render_pages.py
产物：assets/pages/{home,detail-trader,detail-fan}.png + assets/manifests/*.json
（运行时引擎只读这些产物，不依赖 playwright）
"""

from __future__ import annotations

import json
import os
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
            "link-market": ("查看完整行情 · Level-2", "link", "点击进入专业行情终端页", "market-data"),
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
    # ── D0 长程深链新增页（trader 角色专用：财经列表→详情→行情终端→财报→机构研报） ──
    "finance-list": {
        "file": "finance-list.html",
        "elements": {
            "list-nav": ("频道导航 · 财经", "region", "频道入口", None),
            "list-title": ("财经要闻 标题", "region", "页面标题", None),
            "filter-bar": ("筛选/排序条", "region", "个股/宏观/板块筛选", None),
            "item-maotai": ("头条：茅台获5家券商上调评级", "link", "点击进入茅台详情页", "detail-trader"),
            "item-baijiu": ("白酒板块反弹3.1%", "region", "板块联动", None),
            "item-rrr": ("央行降准0.5%", "region", "宏观新闻", None),
            "item-northbound": ("北向资金净买入120亿", "region", "资金面新闻", None),
            "item-cpi": ("4月CPI同比+0.6%", "region", "数据新闻", None),
            "side-calendar": ("侧栏 · 财经日历", "region", "本周重要事件", None),
            "side-ranking": ("侧栏 · 个股人气榜", "region", "热门个股", None),
        },
    },
    "market-data": {
        "file": "market-data.html",
        "elements": {
            "md-header": ("标题 · 行情终端", "region", "页面标题", None),
            "md-kline": ("日K线图", "region", "近3月日线+均线+量能", None),
            "md-capital": ("资金流向明细表", "region", "主力/超大单/北向分项", None),
            "md-mainflow": ("主力净额 +18.33亿", "region", "关键资金数字，放大确认", None),
            "md-indicators": ("技术指标面板", "region", "MACD/RSI/KDJ/BOLL", None),
            "md-valuation": ("估值卡", "region", "PE/PB/股息率/市值", None),
            "md-pe-pct": ("PE历史分位 34.2%", "region", "关键估值小字，放大确认", None),
            "link-report": ("查看公司财报与公告", "link", "点击进入财报页", "report"),
        },
    },
    "report": {
        "file": "report.html",
        "elements": {
            "rp-header": ("标题 · 2026一季报", "region", "财报标题", None),
            "rp-table": ("主要财务数据表", "region", "营收/净利/毛利/现金流", None),
            "rp-revenue": ("营业收入 514.6亿 +12.4%", "region", "营收行", None),
            "rp-profit": ("归母净利 268.5亿 +11.6%", "region", "净利行", None),
            "rp-margin": ("毛利率 91.8%", "region", "毛利率行", None),
            "rp-cashflow": ("经营现金流 -36.5%", "region", "现金流异常项", None),
            "rp-footnote": ("脚注 · 口径说明", "region", "关键小字：合并口径/非经常性损益，放大看清", None),
            "link-consensus": ("查看机构评级汇总", "link", "点击进入机构研报页", "consensus"),
        },
    },
    "consensus": {
        "file": "consensus.html",
        "elements": {
            "cs-header": ("标题 · 机构评级汇总", "region", "页面标题", None),
            "cs-overview": ("评级总览四宫格", "region", "一致预期/最高/空间/分布", None),
            "cs-target-avg": ("一致预期目标价 2005", "region", "一致预期", None),
            "cs-target-high": ("最高目标价 2150", "region", "关键数字，放大确认", None),
            "cs-rating-dist": ("评级分布 买入12", "region", "评级统计", None),
            "cs-table": ("各机构研报对比表", "region", "中金/中信/华泰目标价", None),
            "cs-latest": ("最新研报摘要", "region", "中金05-03研报", None),
            "cs-risk": ("风险提示小字", "region", "关键小字：现金流风险/免责，放大看清", None),
        },
    },
    # ── D4 多源破案：revenue 升级为 5 源复杂证据链；product 保持 3 源续航案例 ──
    # source 间用 link 互相指向，形成可主动回看的网状证据池。
    "src-annual-pdf": {
        "file": "src-annual-pdf.html",
        "elements": {
            "annpdf-toolbar": ("PDF 工具栏 · 年报第18页", "region", "来源身份：公司年报PDF截图", None),
            "annpdf-header": ("标题 · 锐芯科技 2025 年报摘要", "region", "法定披露文件头部", None),
            "annpdf-keyvalue": ("母公司收入 10.2 亿", "region", "关键数字：母公司主营口径，放大确认", None),
            "annpdf-table": ("主要会计数据表", "region", "母公司口径摘要表", None),
            "annpdf-footnote": ("脚注 · 母公司/合并口径说明", "region", "关键小字：10.2为母公司口径/合并口径15.0亿，放大看清", None),
            "annpdf-trap": ("误读提示 · 大号数字不是最终答案", "region", "干扰说明：只看大数字会误判", None),
            "annpdf-to-notes": ("跳转 · 财报附注", "link", "主动查看合并范围与关联交易附注", "src-annual-notes"),
            "annpdf-to-research": ("跳转 · 查看券商研报", "link", "主动核查研报是否采用合并口径", "src-research"),
            "annpdf-to-press": ("跳转 · 查看新闻报道", "link", "主动核查媒体12.6亿是否可靠", "src-press"),
            "annpdf-to-database": ("跳转 · 查看数据库摘要", "link", "主动核查数据库修订版与单位", "src-database"),
        },
    },
    "src-annual-notes": {
        "file": "src-annual-notes.html",
        "elements": {
            "notes-toolbar": ("PDF 工具栏 · 年报附注页", "region", "来源身份：年报附注截图", None),
            "notes-header": ("标题 · 财报附注", "region", "附注七/八说明", None),
            "notes-consolidated": ("附注七 · 合并范围表", "region", "关键表格：10.2+4.8=15.0", None),
            "notes-footnote": ("脚注 · 审计合并口径 15.0 亿", "region", "关键小字：真实营收优先采用审计合并口径15.0亿，放大看清", None),
            "notes-related": ("附注八 · 关联交易与分部收入", "region", "解释4.8亿与12.6亿分部收入", None),
            "notes-distractor": ("误导点 · 新闻与数据库混淆", "region", "排除干扰：12.6为分部收入/14.7为旧快报", None),
            "notes-to-annual": ("回看 · 年报PDF首页", "link", "回看10.2亿母公司口径", "src-annual-pdf"),
            "notes-to-research": ("跳转 · 查看券商研报", "link", "核查研报是否复核15.0亿", "src-research"),
            "notes-to-press": ("跳转 · 查看新闻报道", "link", "核查12.6亿是否误读分部收入", "src-press"),
            "notes-to-database": ("跳转 · 查看数据库摘要", "link", "核查14.7/15.0版本差异", "src-database"),
        },
    },
    "src-annual": {
        "file": "src-annual.html",
        "elements": {
            "ann-header": ("标题 · 锐芯科技 2025 年报摘要", "region", "来源身份：法定年报披露", None),
            "ann-table": ("主要财务数据表", "region", "母公司口径财务表", None),
            "ann-keyvalue": ("营业收入 10.2 亿", "region", "关键数字：母公司主营口径，放大确认", None),
            "ann-footnote": ("脚注 · 口径与关联交易说明", "region", "关键小字：母公司口径/含关联方4.8亿/合并15.0亿，放大看清", None),
            "ann-to-research": ("跳转 · 查看券商研报", "link", "主动核查研报营收是否一致", "src-research"),
            "ann-to-press": ("跳转 · 查看新闻报道", "link", "主动核查媒体报道营收是否一致", "src-press"),
        },
    },
    "src-research": {
        "file": "src-research.html",
        "elements": {
            "res-header": ("标题 · 中金公司深度研报", "region", "来源身份：券商研报", None),
            "res-table": ("盈利预测表", "region", "合并口径预测表", None),
            "res-keyvalue": ("营业收入 15.0 亿", "region", "关键数字：合并报表口径，放大确认", None),
            "res-footnote": ("脚注 · 合并口径说明", "region", "关键小字：合并口径/本部10.2亿+关联4.8亿，放大看清", None),
            "res-to-annual": ("回看 · 年报PDF首页", "link", "主动回看10.2亿母公司口径", "src-annual-pdf"),
            "res-to-notes": ("跳转 · 财报附注", "link", "主动查看附注七核对合并口径", "src-annual-notes"),
            "res-to-press": ("跳转 · 查看新闻报道", "link", "主动核查媒体报道营收", "src-press"),
            "res-to-database": ("跳转 · 查看数据库摘要", "link", "主动核查修订版与单位", "src-database"),
        },
    },
    "src-press": {
        "file": "src-press.html",
        "elements": {
            "prs-header": ("标题 · 财经媒体报道", "region", "来源身份：转引报道", None),
            "prs-keyvalue": ("报道营收 12.6 亿", "region", "关键数字：口径未注明，放大确认", None),
            "prs-wrong-sum": ("报道整理口径 · 分部收入误读", "region", "干扰项：12.6亿疑似车规芯片分部收入", None),
            "prs-footnote": ("脚注 · 数据来源说明", "region", "关键小字：口径未明确/12.6疑似分部收入/以年报附注为准，放大看清", None),
            "prs-to-annual": ("回看 · 年报PDF首页", "link", "主动回看年报核对母公司口径", "src-annual-pdf"),
            "prs-to-notes": ("跳转 · 财报附注", "link", "主动核查12.6是否为分部收入", "src-annual-notes"),
            "prs-to-research": ("跳转 · 查看券商研报", "link", "主动核查研报营收", "src-research"),
            "prs-to-database": ("跳转 · 查看数据库摘要", "link", "主动核查审计版字段", "src-database"),
        },
    },
    "src-database": {
        "file": "src-database.html",
        "elements": {
            "db-header": ("标题 · 第三方数据库摘要", "region", "来源身份：金融数据库自动抓取", None),
            "db-terminal": ("数据库终端面板", "region", "深色数据库摘要界面", None),
            "db-keyvalue": ("数据库摘要 14.7/15.0/10.2", "region", "关键数字：快报/年报修订/母公司口径并列，放大确认", None),
            "db-version-table": ("版本表 · 快报与年报修订", "region", "单位为百万元，含14.7旧快报与15.0审计版", None),
            "db-version-note": ("脚注 · 版本与单位说明", "region", "关键小字：1500.0百万元=15.0亿元/审计年报修订版，放大看清", None),
            "db-unit-trap": ("误读提示 · 单位与版本混淆", "region", "干扰项：14.7旧快报和百万元单位容易误读", None),
            "db-to-annual": ("回看 · 年报PDF首页", "link", "主动回看年报首页10.2亿口径", "src-annual-pdf"),
            "db-to-notes": ("跳转 · 财报附注", "link", "主动核查审计版15.0亿来源", "src-annual-notes"),
            "db-to-research": ("跳转 · 查看券商研报", "link", "主动核查研报是否采纳审计版", "src-research"),
            "db-to-press": ("跳转 · 查看新闻报道", "link", "主动排除12.6亿媒体误读", "src-press"),
        },
    },
    "src-official": {
        "file": "src-official.html",
        "elements": {
            "off-header": ("标题 · 锐星 EV 官方参数", "region", "来源身份：官网规格", None),
            "off-quad": ("核心参数四宫格", "region", "续航/加速/快充/质量", None),
            "off-keyvalue": ("CLTC 续航 605 km", "region", "关键数字：官方CLTC续航，放大确认", None),
            "off-footnote": ("脚注 · CLTC 测试工况条件", "region", "关键小字：CLTC工况/25℃/空调关闭，放大看清", None),
            "off-to-review": ("跳转 · 查看媒体评测", "link", "主动核查媒体实测续航", "src-review"),
            "off-to-forum": ("跳转 · 查看用户反馈", "link", "主动核查车主实测续航", "src-forum"),
        },
    },
    "src-review": {
        "file": "src-review.html",
        "elements": {
            "rev-header": ("标题 · 媒体实测评测", "region", "来源身份：汽车媒体长测", None),
            "rev-keyvalue": ("实测续航 432 km", "region", "关键数字：夏季高速实测，放大确认", None),
            "rev-footnote": ("脚注 · 实测条件说明", "region", "关键小字：35℃夏季/空调/高速80%，放大看清", None),
            "rev-to-official": ("回看 · 官方参数", "link", "主动回看官网CLTC工况条件", "src-official"),
            "rev-to-forum": ("跳转 · 查看用户反馈", "link", "主动核查车主冬季续航", "src-forum"),
        },
    },
    "src-forum": {
        "file": "src-forum.html",
        "elements": {
            "frm-header": ("标题 · 车主论坛续航汇总", "region", "来源身份：真实车主口碑", None),
            "frm-keyvalue": ("冬季实测续航 380 km", "region", "关键数字：冬季车主实测，放大确认", None),
            "frm-footnote": ("脚注 · 车主实测条件", "region", "关键小字：-5℃冬季/暖风/拥堵满载，放大看清", None),
            "frm-to-official": ("回看 · 官方参数", "link", "主动回看官网CLTC工况条件", "src-official"),
            "frm-to-review": ("跳转 · 查看媒体评测", "link", "主动核查媒体夏季实测", "src-review"),
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
        # 可选：通过 AP_CHROMIUM 显式指定 chromium 可执行文件，绕过 playwright 架构自动发现
        _launch_kwargs: dict = {"args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        _exe = os.environ.get("AP_CHROMIUM")
        if _exe:
            _launch_kwargs["executable_path"] = _exe
        browser = p.chromium.launch(**_launch_kwargs)
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
