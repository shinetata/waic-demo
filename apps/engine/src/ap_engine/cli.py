"""命令行：跑一条主动感知轨迹并输出符合协议的 JSON（同时落盘到 trajectories/）。"""

from __future__ import annotations

import argparse
import asyncio
import sys

from ap_engine.loop.agent_loop import run_trajectory_collect


def main() -> None:
    parser = argparse.ArgumentParser(description="跑一条主动感知轨迹")
    parser.add_argument("--scene", default="d0-news-portal")
    parser.add_argument("--role", default="trader")
    parser.add_argument("--side", default="ours", choices=["ours", "baseline"])
    args = parser.parse_args()

    traj = asyncio.run(run_trajectory_collect(args.scene, args.role, args.side))
    print(traj.model_dump_json(indent=2, exclude_none=True))
    s = traj.result.stats if traj.result else None
    print(
        f"\n[saved] trajectories/{traj.id}.json  steps={len(traj.steps)}"
        f"  reached_eos={s.reached_eos if s else '?'}"
        f"  skipped_regions={s.skipped_regions if s else '?'}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
