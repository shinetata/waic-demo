"""FastAPI 服务：实时流式 rollout（WebSocket）+ 回放（REST）+ 静态资源。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ap_engine.config import get_settings
from ap_engine.storage import list_trajectories, load_trajectory

settings = get_settings()
app = FastAPI(title="Active Perception Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态资源（页面长图 / 裁剪图等）
_assets = Path(settings.assets_dir)
_assets.mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/config")
def api_config() -> dict:
    ours = settings.model_for("ours")
    base = settings.model_for("baseline")
    return {
        "max_steps": settings.max_steps,
        "models": {
            "ours": {"label": ours.label, "name": ours.model_name, "provider": ours.provider},
            "baseline": {"label": base.label, "name": base.model_name, "provider": base.provider},
        },
    }


@app.get("/api/scenes")
def api_scenes() -> dict:
    # 延迟 import，避免环境层尚未实现时阻断服务启动
    try:
        from ap_engine.environments import list_scenes

        return {"scenes": list_scenes()}
    except Exception as exc:  # noqa: BLE001
        return {"scenes": [], "note": f"environments not ready: {exc}"}


@app.get("/api/cases")
def api_cases() -> dict:
    try:
        from ap_engine.environments.investigation import list_cases

        return {"cases": list_cases()}
    except Exception as exc:  # noqa: BLE001
        return {"cases": [], "note": f"investigation not ready: {exc}"}


@app.get("/api/trajectories")
def api_trajectories() -> dict:
    return {"items": list_trajectories(settings.trajectories_dir)}


@app.get("/api/trajectories/{traj_id}")
def api_trajectory(traj_id: str):
    traj = load_trajectory(traj_id, settings.trajectories_dir)
    if traj is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return traj.model_dump()


@app.websocket("/ws/run")
async def ws_run(ws: WebSocket) -> None:
    await ws.accept()
    scene = ws.query_params.get("scene", "d0-news-portal")
    role = ws.query_params.get("role", "trader")
    side = ws.query_params.get("side", "ours")
    try:
        # 延迟 import：Agent Loop 在 loop 模块实现
        from ap_engine.loop.agent_loop import run_trajectory

        async for event in run_trajectory(scene=scene, role=role, side=side):
            await ws.send_text(event.model_dump_json())
    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        await ws.send_json({"type": "error", "message": str(exc)})
    finally:
        try:
            await ws.close()
        except RuntimeError:
            pass
