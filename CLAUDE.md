# WAIC Demo 项目知识

## 项目概览
waic-demo：Vue3+Vite 前端 + Python FastAPI 引擎，展示"认知基模·主动感知"。Monorepo（pnpm + uv）。
- 前端 `apps/web`（Vue3+Vite+TS），引擎组件 `src/engine/`，场景 `src/scenes/`
- 后端 `apps/engine`（FastAPI+uv），核心 `src/ap_engine/`
- 协议 `packages/protocol`（TS + Pydantic + JSON Schema 三方对齐）

## 启动
- 后端：`cd apps/engine && uv run uvicorn ap_engine.server:app --port 8000`
- 前端：`pnpm -F @ap/web dev`（5173）
- 素材：`cd apps/engine && uv run --with playwright python tools/render_pages.py`（首次需 `uv run --with playwright playwright install chromium`）
- 跑轨迹：`uv run python -m ap_engine.cli --scene <id> --role <role> --side ours|baseline`

## 场景扩展模式（新增 demo 场景的标准流程）
1. 写 HTML 模板到 `assets/site/{stage}.html`，关键元素加 `id`
2. `tools/render_pages.py` 的 `PAGESPEC` 注册 `id -> (file, elements{id:(label,kind,hint,to)})`
3. 跑脚本生成 `assets/pages/*.png` + `assets/manifests/*.json`
4. `environments/scenes.py` 加 `SceneSpec` + `RoleSpec`（`_load_manifest` 加载）
5. 前端 `App.vue` 加 tab + `scenes/{name}/XView.vue`（复制 D0View 结构，改 `SCENE` 常量）

## 关键设计点
- 协议：`Step = thought + action + observation`。Action: see/click/zoom_in/zoom_out/scroll/none/navigate/snapshot/eos
- `SelfPageEnvironment`：click/navigate 按 `link.to`（`NavTarget.to` 或 `ElementSpec.to`）跳转 stage，支持前进+回退；`to` 找不到 stage 时 fallback `+1`（D0 的 link.to 值与 stage id 不一致，靠此兼容，勿删）
- `prompts.py` 按 `PolicyInput.scene_id` 分流：D0 用 `_page_guide`（线性末页假设），D4 用 `_investigation_guide`（网状多源）
- `agent_loop.py` 软约束：进入 stage 后 `min_obs` 次观察才允许 click 跳走（D0=3, D4=2），navigate 主动回看不拦；卡死保护=连续相同动作≥3 收尾
- baseline = oneshot 整页问答：D0 单图（`build_oneshot_messages`），D4 多图（`build_oneshot_multisource_messages`）

## 场景清单
- `d0-news-portal`：浏览器主动感知（trader/fan），线性 stage 链
- `d4-investigation`：多源破案（revenue/product），3 source 网状可回看，高潮=回看+zoom脚注+一致性结论
