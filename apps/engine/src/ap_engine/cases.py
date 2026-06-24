"""D4 多源破案 · 证据板 case spec。

独立于轨迹协议：描述各信息源的标志性数字、矛盾对、解谜(resolver)元素，供前端把
实时 steps（观察到的 stage + element_id）关联成证据板动画（矛盾红线 → 绿线 RESOLVED）。
通过 /api/case?scene= 下发。结构预留多案例扩展。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HeadlineClaim:
    """某信息源的标志性数字（证据板上点亮的核心声明）。"""

    element_id: str
    metric: str
    value_text: str
    caliber: str  # 口径标签，如 合并口径 / 主营口径


@dataclass
class SourceNode:
    id: str  # 对应 stage id
    title: str
    kind: str  # annual_report / broker_report / press_release
    headline: HeadlineClaim


@dataclass
class ConflictEdge:
    """两个声明之间的矛盾连线（两端均被观察到后变红）。"""

    a: str  # element_id
    b: str  # element_id
    label: str


@dataclass
class Resolver:
    """解谜元素：被观察/放大后，矛盾连线变绿 + RESOLVED。"""

    element_id: str
    source_id: str
    insight: str


@dataclass
class CaseSpec:
    id: str  # 对应 scene id
    title: str
    question: str
    index_stage: str  # 案件卷宗着陆 stage
    sources: list[SourceNode]
    conflicts: list[ConflictEdge]
    resolver: Resolver
    baseline_hint: str = ""


CASES: dict[str, CaseSpec] = {
    "d4-revenue-probe": CaseSpec(
        id="d4-revenue-probe",
        title="云图智能 2025 营收交叉核查",
        question="云图智能 2025 全年真实营业收入到底是多少？",
        index_stage="case-index",
        sources=[
            SourceNode(
                id="src-report",
                title="公司年报（PDF）",
                kind="annual_report",
                headline=HeadlineClaim(
                    element_id="a-revenue",
                    metric="营业收入",
                    value_text="152.3 亿",
                    caliber="合并口径",
                ),
            ),
            SourceNode(
                id="src-broker",
                title="券商研报",
                kind="broker_report",
                headline=HeadlineClaim(
                    element_id="b-revenue",
                    metric="主营业务收入",
                    value_text="104.2 亿",
                    caliber="主营口径 · 剔除关联交易",
                ),
            ),
            SourceNode(
                id="src-press",
                title="新闻门户报道",
                kind="news_report",
                headline=HeadlineClaim(
                    element_id="c-revenue",
                    metric="营收宣传",
                    value_text="超 150 亿",
                    caliber="对外宣传口径",
                ),
            ),
        ],
        conflicts=[
            ConflictEdge(a="a-revenue", b="b-revenue", label="152.3 vs 104.2 · 差约 48 亿"),
        ],
        resolver=Resolver(
            element_id="a-footnote",
            source_id="src-report",
            insight="年报脚注：合并口径含关联交易约 48.1 亿；剔除后母公司主营约 104.2 亿。104.2 + 48.1 ≈ 152.3 —— 三个数字是口径不同，并非互相矛盾。",
        ),
        baseline_hint="一次性读入各源整页缩略图后，常被新闻里抓眼球的宣传大数字（超 150 亿）带偏、看不清年报脚注口径，误答“约 150 亿”或“数字互相矛盾、无法确定”。",
    ),
}


def get_case(scene_id: str) -> CaseSpec:
    if scene_id not in CASES:
        raise KeyError(f"unknown case: {scene_id}")
    return CASES[scene_id]


def list_cases() -> list[str]:
    return list(CASES.keys())


def case_to_dict(c: CaseSpec) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "question": c.question,
        "index_stage": c.index_stage,
        "sources": [
            {
                "id": s.id,
                "title": s.title,
                "kind": s.kind,
                "headline": {
                    "element_id": s.headline.element_id,
                    "metric": s.headline.metric,
                    "value_text": s.headline.value_text,
                    "caliber": s.headline.caliber,
                },
            }
            for s in c.sources
        ],
        "conflicts": [{"a": e.a, "b": e.b, "label": e.label} for e in c.conflicts],
        "resolver": {
            "element_id": c.resolver.element_id,
            "source_id": c.resolver.source_id,
            "insight": c.resolver.insight,
        },
        "baseline_hint": c.baseline_hint,
    }
