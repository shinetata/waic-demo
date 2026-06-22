# WAIC 主动感知 Demo

真实模型实时推理驱动的 **Active Lifting**（主动感知）闭环，以及两个展示场景：

- **D0 浏览器主动感知**：同一画面、不同意图 → 完全不同的观察路径（我们 vs Gemma 4 31B 对比）。
- **D4 多源破案**：面对矛盾信息源，主动选择阅读、发现矛盾、回看脚注、推出一致性解释。

## 架构（三层 + 闭环）

```
轨迹协议 (packages/protocol)  ← 前后端共享契约（JSON Schema + TS + Pydantic）
        │
主动感知引擎 (apps/engine, Python/FastAPI)
  环境层 Environment   ：自建页面/大图 → 按动作裁剪产出「全局缩略图 + 局部高清」微环境
  策略模型适配层        ：统一 VisionPolicy，.env 可插拔 provider（mock / OpenAI 兼容）
  Agent Loop          ：意图 → 微环境 → 模型推 (心语 wₜ, 动作 aₜ) → 环境执行 → … → EOS（流式）
        │  WebSocket / SSE
前端播放引擎 (apps/web, Vue 3)
  注意力框 / 轨迹曲线 / 局部高清浮窗 / 心语流 / 数据面板 / 证据板
```

动作空间：`see / click / zoom_in / zoom_out / scroll / none(连续思考) / navigate / snapshot / eos`。
grounding 混合：DOM 语义元素 id + dense 区归一化坐标。

## 快速开始

### 1. 引擎（Python，uv）

```bash
cd apps/engine
uv sync
cp .env.example .env          # 默认 provider=mock，可零依赖跑通
uv run uvicorn ap_engine.server:app --reload --port 8000
```

命令行跑一条真实轨迹：

```bash
uv run python -m ap_engine.cli --scene d0-news-portal --role trader --side baseline
```

### 2. 前端（pnpm）

```bash
pnpm install                  # 在仓库根 demo/ 执行
pnpm -F @ap/web dev           # http://localhost:5173
```

## 模型可插拔（.env）

两侧（`ours` / `baseline`）独立配置，运行时按 `provider` 切换：

| 变量 | 说明 |
|------|------|
| `AP_OURS_PROVIDER` / `AP_BASELINE_PROVIDER` | `mock` 或 `openai_compatible` |
| `AP_*_MODEL_NAME` | 模型 slug，如 `google/gemma-4-31b-it`、`qwen/qwen3.5-vl-instruct` |
| `AP_*_BASE_URL` | OpenAI 兼容端点，如 OpenRouter `https://openrouter.ai/api/v1` |
| `AP_*_API_KEY` | 对应 Key |

- **baseline**：Gemma 4 31B（经 OpenRouter 接入，本机无需部署）。
- **ours（前期）**：Qwen3.5-VL 代理；自研基模 ready 后改 `.env` 即可无缝替换。
- `mock`：无网络/Key 的确定性策略，用于跑通闭环、前端联调与现场离线兜底。

## 目录

```
packages/protocol/   轨迹协议（schema + TS + Pydantic）
apps/engine/         主动感知引擎（environments / models / loop）
  tools/run_shot.sh  起服务 + Playwright 截图（前端可视化验证）
apps/web/            Vue 3 前端（engine 播放引擎 + scenes/d0-browser + scenes/d4-investigation）
```

## 验证状态

- 引擎：协议 / 环境 / 可插拔模型 / Agent Loop / CLI / WebSocket 流式 均跑通（mock）。
- 前端：`vue-tsc` 类型检查 + `vite build` 通过；D0 与 D4 页面已用 Playwright 实拍验证渲染。
- 现场用真实模型：在 `.env` 配置 OpenRouter Key 即可（ours=Qwen-VL / baseline=Gemma），对比维度（步数 / 放大 / 跳过 / 连续思考 / EOS）随真实模型自然显现差异。
