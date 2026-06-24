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

SYSTEM_PROMPT = """你是一个"主动感知"视觉智能体。你不会一次看清整页，而是每一步只观察当前视野，并主动决定下一步看哪里，围绕用户意图高效地找到关键信息、跳过无关区域。复杂任务往往需要跨多个页面、多个证据源逐步核查，请耐心走完整条信息链，不要过早下结论。

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

浏览策略（这是一个跨多页的长程任务）：关键证据往往分散在多个页面、多个信息源中，需要顺着页面间的链接逐页深入、交叉核对。每进入一个新页面，你必须先用 see 逐个查看本页 2~4 个关键语义区域，并对关键数字（读数/分位/目标价/脚注小字等）用 zoom-in 放大确认，把本页信息看明白后，才考虑下一步导航。严禁在没有 see/zoom 观察当前页面的情况下直接 click——连续 click 会错过所有关键证据，是错误行为。click 仅用于进入清单中明确标注 [链接·用 click 进入] 的元素：只有当你已看完本页、且清单里确实存在 [链接] 元素时，才用 click 进入下一页继续核查；如果当前页清单里没有任何 [链接] 元素，说明已到信息链末端，绝不要再 click，应在看完本页后用 eos 给出综合结论。不要对同一区域连续重复 see。

输出要求：每一步只输出一个 JSON 对象，不要任何多余文字、不要 markdown：
{"thought":"你此刻的判断/意图(一句话中文)","action":{"type":"see","target":{...},"label":"简短动作标签"}}

当你已经走到信息链末端（当前页不再有可点击的 [链接] 进入新页面）、并综合了沿途各页的关键证据后，再输出 {"thought":"<综合多源的结论>","action":{"type":"eos","label":"OUTPUT: <结论摘要>"}}。"""


ONESHOT_SYSTEM_PROMPT = """你是一个传统视觉问答模型。你会一次性看到整张页面截图，然后基于这一次性读入的全部内容，直接给出对用户问题的回答。你不能逐步放大、不能翻页、不能主动选择看哪里——只能依据这张整页图所能看清的信息作答。请用一段简短中文直接给出结论。"""


INVESTIGATION_SYSTEM_PROMPT = """你是一个"多源信息核查"视觉智能体。面对多个说法不一的信息源，你不会一次性读完所有材料就下结论，而是逐个来源主动观察、提取关键数字与口径，发现矛盾后主动回看、放大脚注小字找出差异原因，最终给出一致性解释。

每一步你会收到两张图：
1) 全局缩略图：当前来源整页的低清概览，红框标出你"当前视野"的位置；
2) 局部高清图：当前视野放大后的清晰画面。

可用动作 action.type：
- see：把视野移动到某区域查看（需 target）
- zoom_in：放大某个更小区域看清细节，尤其是数字、脚注、口径/测试条件等小字（需 target）
- zoom_out：缩小视野回到更大范围（可无 target）
- none：保持当前视野继续思考（连续思考，不移动视野）
- snapshot：回到整页全局视野
- click / navigate：在信息源之间跳转。每个来源底部有 [链接] 指向其它来源，用 click 进入；当你需要回看已读来源核对时，用 navigate 主动回到该来源
- eos：所有来源已核查、矛盾已解释清楚，结束并给出一致性结论

target 三选一：
- {"kind":"element","element_id":"<下方清单里的 id>"}：优先使用给定的语义元素
- {"kind":"region","rect":{"x":0~1,"y":0~1,"w":0~1,"h":0~1}}：归一化坐标，用于清单未覆盖的细节
- {"kind":"nav","to":"<来源 stage id>"}：仅用于 navigate 回看指定来源（如 src-annual）

核查策略（这是多源矛盾任务）：每个来源都要先用 see 看清关键数字，并用 zoom_in 放大脚注/口径说明小字确认其口径或测试条件。当发现不同来源的数字矛盾时，不要轻易判定谁对谁错——主动 navigate 回看相关来源，用 zoom_in 放大它的脚注小字，找出数字差异背后的真实口径（如合并/母公司口径、含/不含关联交易）或测试条件（如工况、温度、负载）。只有把每个来源的数字与口径都核对清楚、矛盾得到合理解释后，才用 eos 给出一致性结论。严禁只读一两个来源就下结论，也严禁对所有来源走马观花却不 zoom 脚注。

输出要求：每一步只输出一个 JSON 对象，不要任何多余文字、不要 markdown：
{"thought":"你此刻的判断/意图(一句话中文)","action":{"type":"see","target":{...},"label":"简短动作标签"}}

当所有来源均已核查、矛盾已解释清楚后，输出 {"thought":"<综合多源的一致性结论>","action":{"type":"eos","label":"OUTPUT: <结论摘要>"}}。"""


def build_oneshot_messages(intent, full_image_path) -> list[dict[str, Any]]:
    """现有做法对照：把整页图一次性喂入 + 直接问答（读完再想）。"""
    text = (
        f"【用户问题】{intent.prompt}\n\n"
        "下面是整张页面截图。请一次性通读后直接给出你的结论（一段简短中文）。"
    )
    return [
        {"role": "system", "content": ONESHOT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": image_data_url(full_image_path)}},
            ],
        },
    ]


def build_oneshot_multisource_messages(intent, image_paths: list) -> list[dict[str, Any]]:
    """多源破案对照：把多个来源的整页图一次性喂入 + 直接问答（读完再想）。

    期望 baseline 被多个矛盾数字迷惑，给出含糊或错误结论，反衬主动核查的价值。
    """
    text = (
        f"【用户问题】{intent.prompt}\n\n"
        "下面按顺序是各个信息来源的完整截图。请一次性通读全部来源后，"
        "直接给出你的结论（一段简短中文）。"
    )
    content: list[dict[str, Any]] = [{"type": "text", "text": text}]
    for p in image_paths:
        content.append({"type": "image_url", "image_url": {"url": image_data_url(p)}})
    return [
        {"role": "system", "content": ONESHOT_SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


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


def _page_guide(inp: PolicyInput) -> str:
    """按"本页核查进度"动态生成引导：缩略图看不清细节，必须 see/zoom 进入区域；
    中间页观察不足时禁止 click，末页则提示 eos，避免一路 click 穿页或末页反复纠结。"""
    obs = inp.observation
    cur_stage = obs.stage
    observe_types = ("see", "zoom_in", "zoom_out", "snapshot")
    n_observed = sum(
        1 for s in inp.history if s.stage == cur_stage and s.action.type in observe_types
    )
    has_link = any(e.kind == "link" for e in obs.elements)
    if not has_link:
        return (
            "【本页核查进度】本页是信息链的最后一页（清单中没有 [链接] 元素，无法再进入新页面）。"
            "请在看清本页关键区域后，综合此前各页收集到的全部证据，用 eos 给出最终结论；"
            "不要重复观察同一处区域。"
        )
    if n_observed < 3:
        return (
            f"【本页核查进度】本页（stage={cur_stage}）你只观察了 {n_observed} 次。缩略图看不清细节，"
            "请先用 see 逐个查看本页 3 个左右关键语义区域、并对关键数字用 zoom_in 放大确认，"
            "充分核查本页后再 click 进入下一页。本步请不要 click。"
        )
    return (
        f"【本页核查进度】本页已观察 {n_observed} 次。若关键信息（数字/图表/要点）均已看清，"
        "可 click 进入下一页继续核查；若仍有关键区域未看，请继续 see/zoom。"
    )


def _investigation_guide(inp: PolicyInput) -> str:
    """多源破案专用引导：按"已访问来源数 + 未读来源 + 当前来源观察数"动态生成。

    不假设线性末页（每个来源都有 [链接]），鼓励发现矛盾后主动 navigate 回看 + zoom 脚注。
    """
    obs = inp.observation
    observe_types = ("see", "zoom_in", "zoom_out", "snapshot")
    visited = {s.stage for s in inp.history}
    visited.add(obs.stage)
    n_visited = len(visited)
    n_observed_cur = sum(
        1 for s in inp.history if s.stage == obs.stage and s.action.type in observe_types
    )
    links = [e for e in obs.elements if e.kind == "link"]
    unvisited = [e.to for e in links if e.to and e.to not in visited]
    parts = [
        f"【核查进度】已访问 {n_visited} 个信息源；当前来源={obs.stage}，本来源已观察 {n_observed_cur} 次。"
    ]
    if unvisited:
        parts.append(
            f"仍有未核查的来源：{'、'.join(unvisited)}。请先看清当前来源的关键数字与脚注，"
            "再通过 [链接] 跳转核查未读来源，不要急于下结论。"
        )
    else:
        parts.append(
            "所有来源均已访问。若已发现数字矛盾，请主动 navigate 回看相关来源、"
            "用 zoom_in 放大脚注/口径小字找出差异原因；若矛盾已解释清楚，用 eos 给出一致性结论。"
        )
    if n_observed_cur < 2:
        parts.append("当前来源观察不足，请先 see 关键数字区、zoom_in 脚注小字确认口径/条件。")
    return " ".join(parts)


def build_messages(inp: PolicyInput) -> list[dict[str, Any]]:
    obs = inp.observation
    is_investigation = inp.scene_id == "d4-investigation"
    sys_prompt = INVESTIGATION_SYSTEM_PROMPT if is_investigation else SYSTEM_PROMPT
    guide = _investigation_guide(inp) if is_investigation else _page_guide(inp)
    text = f"""【用户意图】{inp.intent.prompt}
【进度】第 {inp.step_index + 1} 步 / 预算 {inp.max_steps} 步
【已观察轨迹】
{summarize_history(inp.history)}
【当前视野】stage={obs.stage}，zoom={obs.zoom_level}×，rect=({obs.rect.x},{obs.rect.y},{obs.rect.w},{obs.rect.h})
【当前可选语义元素】
{_elements_block(inp)}
{guide}

请结合下面两张图（第一张=全局缩略图含红框；第二张=当前视野局部高清）决定下一步动作。只输出一个 JSON。"""

    user_content: list[dict[str, Any]] = [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": image_data_url(obs.thumb_path)}},
        {"type": "image_url", "image_url": {"url": image_data_url(obs.crop_path)}},
    ]
    return [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_content},
    ]


class ParseError(ValueError):
    pass


def _repair_json(s: str) -> str:
    """修复模型常见 JSON 笔误：key 后漏冒号（如 "action"{ → "action":{ ；"target"[ → "target":[ ）。"""
    return re.sub(r'("[^"\\]*")\s*(?=[\[{])', r"\1:", s)


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
    # 用括号配对提取第一个完整 JSON 对象（容忍前后解释文字 / 多段输出 / Extra data）
    start = text.find("{")
    if start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        pass
                    try:  # 容错：修复 key 后漏冒号等常见笔误后重试
                        return json.loads(_repair_json(candidate))
                    except json.JSONDecodeError:
                        break
    raise ParseError(f"no JSON object found in output: {text[:120]!r}")


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
