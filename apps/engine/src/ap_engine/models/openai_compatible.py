"""OpenAICompatiblePolicy：OpenAI 兼容协议的真实多模态模型适配。

覆盖 OpenRouter（Gemma 4 31B / Qwen3.5-VL）、本地 vLLM、各家兼容端点、未来自研基模。
通过 .env 的 base_url / api_key / model_name 配置。
"""

from __future__ import annotations

from typing import Optional

from ap_engine.models.base import PolicyDecision, PolicyInput, VisionPolicy
from ap_engine.models.prompts import ParseError, build_messages, parse_decision
from ap_protocol import Action, TokenUsage


class OpenAICompatiblePolicy(VisionPolicy):
    def __init__(self, config) -> None:
        super().__init__(config)
        if not config.base_url:
            raise ValueError("provider=openai_compatible 需要配置 base_url（如 OpenRouter）")
        # 延迟 import，避免无该 provider 时强依赖
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key or "EMPTY",
            default_headers={"X-Title": "WAIC Active Perception"},
        )

    @staticmethod
    def _tokens(resp) -> Optional[TokenUsage]:
        u = getattr(resp, "usage", None)
        if not u:
            return None
        return TokenUsage(
            prompt=getattr(u, "prompt_tokens", 0) or 0,
            completion=getattr(u, "completion_tokens", 0) or 0,
            total=getattr(u, "total_tokens", 0) or 0,
        )

    async def decide(self, inp: PolicyInput) -> PolicyDecision:
        messages = build_messages(inp)
        valid_ids = {e.id for e in inp.observation.elements}
        last_err: Optional[Exception] = None

        for attempt in range(2):
            try:
                resp = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=512,
                )
            except Exception as exc:  # noqa: BLE001 - 网络/鉴权错误
                raise RuntimeError(f"模型调用失败({self.model_name}): {exc}") from exc

            text = resp.choices[0].message.content or ""
            tokens = self._tokens(resp)
            try:
                thought, action = parse_decision(text, valid_ids)
                return PolicyDecision(thought=thought, action=action, tokens=tokens, raw=text)
            except ParseError as exc:
                last_err = exc
                messages = messages + [
                    {"role": "assistant", "content": text},
                    {
                        "role": "user",
                        "content": '上一步输出无法解析。请仅输出一个 JSON：{"thought":...,"action":{...}}，不要任何多余文字。',
                    },
                ]

        return PolicyDecision(
            thought=f"(无法解析模型输出，结束观察：{last_err})",
            action=Action(type="eos", label="OUTPUT: 结束"),
            tokens=None,
            raw="parse-failed",
        )
