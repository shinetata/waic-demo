"""轨迹落盘与读取（用于回放 / 现场兜底）。"""

from __future__ import annotations

import json
from pathlib import Path

from ap_protocol import Trajectory


def _dir(base_dir: str) -> Path:
    p = Path(base_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_trajectory(traj: Trajectory, base_dir: str) -> Path:
    out = _dir(base_dir) / f"{traj.id}.json"
    out.write_text(traj.model_dump_json(indent=2), encoding="utf-8")
    return out


def load_trajectory(traj_id: str, base_dir: str) -> Trajectory | None:
    path = _dir(base_dir) / f"{traj_id}.json"
    if not path.exists():
        return None
    return Trajectory.model_validate_json(path.read_text(encoding="utf-8"))


def list_trajectories(base_dir: str) -> list[dict]:
    items: list[dict] = []
    for path in sorted(_dir(base_dir).glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(
                {
                    "id": data.get("id"),
                    "scene": data.get("scene"),
                    "role": data.get("intent", {}).get("role"),
                    "side": data.get("model", {}).get("side"),
                    "status": data.get("status"),
                    "created_at": data.get("created_at"),
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    return items
