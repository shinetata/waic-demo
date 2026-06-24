# ap-engine · 主动感知引擎

真实模型实时推理驱动的 Active Lifting 闭环：意图 → 微环境 → 模型推 (思考, 动作) → 环境执行 → 新微环境 → … → EOS，流式产出符合 `@ap/protocol` 的轨迹。

## 安装

```bash
cd apps/engine
uv sync                 # 创建 .venv 并安装依赖（含路径依赖 ap-protocol）
cp .env.example .env    # 配置 OpenAI 兼容端点（base_url / api_key / model）
```

## 命令行跑一条轨迹

```bash
uv run python -m ap_engine.cli --scene d0-news-portal --role trader --side ours
# 输出符合协议的 JSON，并落盘到 trajectories/
```

## 启动服务

```bash
uv run uvicorn ap_engine.server:app --reload --port 8000
```

- `GET  /health` 健康检查
- `GET  /api/config` 两侧模型信息
- `GET  /api/scenes` 可用场景与角色
- `WS   /ws/run?scene=&role=&side=` 实时流式 rollout（StreamEvent）
- `GET  /api/trajectories/{id}` 回放
- `/assets/...` 页面长图等静态资源

## 模型配置

通过 `.env` 配置 OpenAI 兼容 provider（OpenRouter / 本地 vLLM / 未来自研基模），两侧（认知基模 ours / 现有做法 baseline）独立。认知基模走主动感知逐步探索；现有做法走一次性整图问答（读完再想）。
