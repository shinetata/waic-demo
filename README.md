# 主动感知 Demo

真实模型实时推理驱动的 **Active Lifting**（认知基模 · 主动感知）闭环演示：

- **D0 浏览器主动感知**：认知基模面对一整页信息，不一次性读入，而是逐步主动选择看哪里、凑近细看关键数字、跳过无关区域、拿不准就停下多想，信息够了主动收尾；右侧以"现有做法（一次性读入、读完再想）"作对照反衬。

## 架构（三层 + 闭环）

```
轨迹协议 (packages/protocol)  ← 前后端共享契约（JSON Schema + TS + Pydantic）
        │
主动感知引擎 (apps/engine, Python/FastAPI)
  环境层 Environment   ：自建页面/大图 → 按动作裁剪产出「全局缩略图 + 局部高清」微环境
  策略模型适配层        ：统一 VisionPolicy，OpenAI 兼容 provider（OpenRouter / vLLM / 自研基模）
  Agent Loop          ：意图 → 微环境 → 模型推 (思考, 动作) → 环境执行 → … → EOS（流式）
        │  WebSocket / SSE
前端播放引擎 (apps/web, Vue 3)
  注意力框 / 轨迹曲线 / 局部高清浮窗 / 思考流 / 三大能力讲解
```

动作空间：`see / click / zoom_in / zoom_out / scroll / none(停下多想) / navigate / snapshot / eos`。
grounding 混合：DOM 语义元素 id + dense 区归一化坐标。

## 快速开始

### 1. 引擎（Python，uv）

```bash
cd apps/engine
uv sync
cp .env.example .env          # 配置 OpenAI 兼容端点的 base_url / api_key / model
uv run uvicorn ap_engine.server:app --reload --port 8000
```

命令行跑一条真实轨迹：

```bash
uv run python -m ap_engine.cli --scene d0-news-portal --role trader --side ours
```

### 2. 前端（pnpm）

```bash
pnpm install                  # 在仓库根 demo/ 执行
pnpm -F @ap/web dev           # http://localhost:5173
```

## 模型配置（.env）

两侧（`ours` / `baseline`）独立配置，均经 OpenAI 兼容协议接入：

| 变量 | 说明 |
|------|------|
| `AP_OURS_*` / `AP_BASELINE_*` | 两侧的 provider / model / base_url / api_key / label |
| `AP_*_MODEL_NAME` | 模型 slug，如 `qwen/qwen3.5-vl-instruct` |
| `AP_*_BASE_URL` | OpenAI 兼容端点，如 OpenRouter `https://openrouter.ai/api/v1` |
| `AP_*_API_KEY` | 对应 Key |

- **认知基模（ours）**：主动感知逐步探索；前期 Qwen3.5-VL 代理，自研基模 ready 后改 `.env` 即可无缝替换。
- **现有做法（baseline）**：同样真实模型，但走"一次性整图问答"路径，体现一次性读入、读完再想。

## 目录

```
packages/protocol/   轨迹协议（schema + TS + Pydantic）
apps/engine/         主动感知引擎（environments / models / loop）
apps/web/            Vue 3 前端（engine 播放引擎 + scenes/d0-browser）
```

## 验证状态

- 引擎：协议 / 环境 / 真实模型适配 / Agent Loop / CLI / WebSocket 流式 均跑通。
- 前端：`vue-tsc` 类型检查 + `vite build` 通过；D0 页面用真实轨迹回放验证渲染。
- 现场：在 `.env` 配置 OpenAI 兼容端点的 Key 即可（认知基模走主动感知，现有做法走一次性整图问答），对比维度随真实模型自然显现。
