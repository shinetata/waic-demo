import { computed, ref } from "vue";
import type { Intent, ModelInfo, Step, TrajectoryResult } from "@ap/protocol";
import { getTrajectory, runStream } from "../api/client";

export type PlayerStatus = "idle" | "running" | "done" | "error";
export type ModelSide = "ours" | "baseline";

/** 管理单条轨迹的播放：支持实时流(live，边收边播) 与 回放(replay，定时推进)。 */
export function usePlayer(side: ModelSide) {
  const steps = ref<Step[]>([]);
  const currentIndex = ref(-1);
  const status = ref<PlayerStatus>("idle");
  const result = ref<TrajectoryResult | null>(null);
  const intent = ref<Intent | null>(null);
  const model = ref<ModelInfo | null>(null);
  const errorMsg = ref<string | null>(null);

  let stopStream: (() => void) | null = null;
  let replayTimer: number | null = null;

  const currentStep = computed<Step | null>(() =>
    currentIndex.value >= 0 ? steps.value[currentIndex.value] ?? null : null,
  );
  const visibleSteps = computed<Step[]>(() => steps.value.slice(0, currentIndex.value + 1));

  function reset() {
    stopStream?.();
    stopStream = null;
    if (replayTimer) {
      clearTimeout(replayTimer);
      replayTimer = null;
    }
    steps.value = [];
    currentIndex.value = -1;
    status.value = "idle";
    result.value = null;
    errorMsg.value = null;
  }

  function startLive(scene: string, role: string) {
    reset();
    status.value = "running";
    stopStream = runStream(
      { scene, role, side },
      (e) => {
        if (e.type === "trajectory_start") {
          intent.value = e.trajectory.intent;
          model.value = e.trajectory.model;
        } else if (e.type === "step") {
          steps.value.push(e.step);
          currentIndex.value = steps.value.length - 1; // 边收边播
        } else if (e.type === "trajectory_end") {
          result.value = e.result;
          status.value = "done";
        } else if (e.type === "error") {
          errorMsg.value = e.message;
          status.value = "error";
        }
      },
      () => {
        if (status.value === "running") status.value = "done";
      },
    );
  }

  async function startReplay(id: string, stepMs = 1200) {
    reset();
    try {
      const traj = await getTrajectory(id);
      intent.value = traj.intent;
      model.value = traj.model;
      steps.value = traj.steps;
      result.value = traj.result ?? null;
      status.value = "running";
      const tick = () => {
        if (currentIndex.value < steps.value.length - 1) {
          currentIndex.value++;
          replayTimer = window.setTimeout(tick, stepMs);
        } else {
          status.value = "done";
        }
      };
      tick();
    } catch (err) {
      errorMsg.value = String(err);
      status.value = "error";
    }
  }

  /** 用一个已加载的轨迹做受控播放（由外部统一驱动节奏，用于双侧同步）。 */
  function loadSteps(s: Step[], i: number, intentV?: Intent, modelV?: ModelInfo) {
    steps.value = s;
    currentIndex.value = i;
    if (intentV) intent.value = intentV;
    if (modelV) model.value = modelV;
  }

  return {
    side,
    steps,
    currentIndex,
    currentStep,
    visibleSteps,
    status,
    result,
    intent,
    model,
    errorMsg,
    reset,
    startLive,
    startReplay,
    loadSteps,
  };
}
