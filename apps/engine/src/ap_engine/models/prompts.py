"""策略模型的 system prompt、用户消息构造与输出解析（结构化约束）。"""

from __future__ import annotations

import json
import re
from typing import Any

from ap_engine.models.base import PolicyInput, image_data_url, summarize_history
from ap_protocol import (
    Action,
    ElementTarget,
    NavTarget,
    Rect,
    RegionTarget,
)

SYSTEM_PROMPT = """你是一个"主动感知"视觉智能体。你不会一次看清整页，而是每一步只观察当前视野，并主动决定下一步看哪里，用尽量少的步数围绕用户意图找到关键信息、跳过无关区域。

每一步你会收到两张图：
1) 全局缩略图：整页/整图的低清概览，红框标出你"当前视野"的位置；
2) 局部高清图：当前视野放大后的清晰画面。

可用动作 action.type：
- see：把视野移动到某区域查看（需 target）
- click：点击一条链接/新闻（清单中标注 [链接] 的元素），跳转进入它的详情页（需 target=该元素 id）
- zoom_in：放大某个更小区域看清细节，如读数字/号码（需 target）
- zoom_out：缩小视野回到更大范围（可无 target）
- none：保持当前视野继续思考（连续思考，不移动视野）
- snapshot：回到整页全局视野
- eos：信息已足够，结束观察

target 二选一：
- {"kind":"element","element_id":"<下方清单里的 id>"}：优先使用给定的语义元素
- {"kind":"region","rect":{"x":0~1,"y":0~1,"w":0~1,"h":0~1}}：归一化坐标，用于清单未覆盖的细节

浏览策略：当前页面若是列表/首页，目标信息通常在某条新闻的详情页里——先扫看几个关键区域，再对目标新闻用 click 进入其详情页。进入详情页后，请依次查看清单中的多个关键区域（如 K线/指标条/五档盘口/价格卡/正文，或比分/球场/球员卡/技术统计/事件轴），对关键数字用 zoom-in 放大确认，收集足够证据后再 eos——不要只看一两处就匆忙结束，也不要对同一区域连续重复 see。

输出要求：每一步只输出一个 JSON 对象，不要任何多余文字、不要 markdown：
{"thought":"你此刻的判断/意图(一句话中文)","action":{"type":"see","target":{...},"label":"简短动作标签"}}

当信息足够回答用户意图时，输出 {"thought":"<结论>","action":{"type":"eos","label":"OUTPUT: <结论摘要>"}}。"""


def _elements_block(inp: PolicyInput) -> str:
    els = inp.observation.elements
    if not els:
        return "（本视图无预定义语义元素，请用 region 坐标）"
    lines = []
    for e in els:
        hint = f"（{e.hint}）" if e.hint else ""
        mark = " [链接·用 click 进入详情]" if e.kind == "link" else ""
        lines.append(f"  - id={e.id}：{e.label}{hint}{mark}")
    return "\n".join(lines)


def build_messages(inp: PolicyInput) -> list[dict[str, Any]]:
    obs = inp.observation
    text = f"""【用户意图】{inp.intent.prompt}
【进度】第 {inp.step_index + 1} 步 / 预算 {inp.max_steps} 步
【已观察轨迹】
{summarize_history(inp.history)}
【当前视野】stage={obs.stage}，zoom={obs.zoom_level}×，rect=({obs.rect.x},{obs.rect.y},{obs.rect.w},{obs.rect.h})
【当前可选语义元素】
{_elements_block(inp)}

请结合下面两张图（第一张=全局缩略图含红框；第二张=当前视野局部高清）决定下一步动作。只输出一个 JSON。"""

    user_content: list[dict[str, Any]] = [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": image_data_url(obs.thumb_path)}},
        {"type": "image_url", "image_url": {"url": image_data_url(obs.crop_path)}},
    ]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class ParseError(ValueError):
    pass


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    # 去掉 ```json ... ``` 包裹
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = _JSON_RE.search(text)
    if not m:
        raise ParseError(f"no JSON object found in output: {text[:120]!r}")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        raise ParseError(f"invalid JSON: {exc}") from exc


def parse_decision(text: str, valid_element_ids: set[str]) -> tuple[str, Action]:
    """把模型输出解析为 (thought, Action)，并对 grounding 做校验与容错。"""
    data = _extract_json(text)
    thought = str(data.get("thought", "")).strip()
    act = data.get("action")
    if not isinstance(act, dict):
        raise ParseError("missing 'action' object")

    atype = act.get("type")
    label = act.get("label")
    reason = act.get("reason")

    target = None
    raw_target = act.get("target")
    if isinstance(raw_target, dict):
        kind = raw_target.get("kind")
        if kind == "element":
            eid = raw_target.get("element_id")
            if eid in valid_element_ids:
                target = ElementTarget(element_id=eid)
            else:
                # 容错：未知 element_id 时丢弃 target（环境保持当前视野）
                target = None
        elif kind == "region":
            rect = raw_target.get("rect", {})
            try:
                target = RegionTarget(
                    rect=Rect(
                        x=float(rect["x"]),
                        y=float(rect["y"]),
                        w=float(rect["w"]),
                        h=float(rect["h"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                target = None
        elif kind == "nav":
            to = raw_target.get("to")
            if to:
                target = NavTarget(to=str(to))

    try:
        action = Action(type=atype, target=target, label=label, reason=reason)
    except Exception as exc:  # noqa: BLE001  - pydantic 校验失败（非法 type 等）
        raise ParseError(f"invalid action: {exc}") from exc

    return thought, action
