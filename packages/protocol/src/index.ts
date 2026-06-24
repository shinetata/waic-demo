/**
 * Active Perception 轨迹协议 — TypeScript 类型
 *
 * 与 ../schema/trajectory.schema.json 一一对应，作为前端消费轨迹（实时流 / 回放）的契约。
 * 后端等价定义见 packages/protocol/py/ap_protocol/models.py。
 */

/** 归一化矩形 [0,1]，相对于所在 stage 的整页/大图坐标系 */
export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Active Lifting 动作空间。none = 连续思考（不移动视野），eos = 结束 rollout */
export type ActionType =
  | "see"
  | "click"
  | "zoom_in"
  | "zoom_out"
  | "scroll"
  | "none"
  | "navigate"
  | "snapshot"
  | "eos";

export const ACTION_TYPES: ActionType[] = [
  "see",
  "click",
  "zoom_in",
  "zoom_out",
  "scroll",
  "none",
  "navigate",
  "snapshot",
  "eos",
];

/** DOM 语义元素 grounding（首页/详情文字区，对通用模型可靠） */
export interface ElementTarget {
  kind: "element";
  element_id: string;
  stage?: string;
}

/** 归一化像素区域 grounding（dense 大图内部细节） */
export interface RegionTarget {
  kind: "region";
  rect: Rect;
  stage?: string;
}

/** 页面跳转目标 */
export interface NavTarget {
  kind: "nav";
  to: string;
}

/** 混合 grounding */
export type Target = ElementTarget | RegionTarget | NavTarget;

/** 动作 */
export interface Action {
  type: ActionType;
  target?: Target;
  label?: string;
  reason?: string;
}

/** 环境产出的当前微环境：全局缩略图 + 当前局部高清 + 视野位置 */
export interface Observation {
  stage: string;
  full_image?: string;
  thumbnail?: string;
  crop_image?: string;
  rect?: Rect;
  zoom_level?: number;
}

export interface Timing {
  started_at?: string;
  duration_ms?: number;
}

/** 一步主动感知：思考 + 动作 + 微环境 */
export interface Step {
  index: number;
  stage: string;
  thought: string;
  action: Action;
  observation?: Observation;
  timing?: Timing;
}

/** 驱动主动探索的角色意图 */
export interface Intent {
  role: string;
  persona?: string;
  prompt: string;
}

export type ModelSide = "ours" | "baseline";

export interface ModelInfo {
  provider?: string;
  name: string;
  side: ModelSide;
}

export interface ActionCounts {
  see?: number;
  click?: number;
  zoom_in?: number;
  zoom_out?: number;
  scroll?: number;
  none?: number;
  navigate?: number;
  snapshot?: number;
  eos?: number;
}

export interface TokenUsage {
  prompt?: number;
  completion?: number;
  total?: number;
}

/** 用于对比模式与数据面板的可量化指标 */
export interface TrajectoryStats {
  total_steps: number;
  action_counts?: ActionCounts;
  skipped_regions?: number;
  tokens?: TokenUsage;
  duration_ms?: number;
  /** true = 模型主动 EOS 终止；false = 被步数预算截断 */
  reached_eos: boolean;
}

export interface TrajectoryResult {
  conclusion?: string;
  output?: string;
  stats: TrajectoryStats;
}

export type TrajectoryStatus = "running" | "done" | "aborted" | "error";

/** 一条完整的主动感知轨迹 */
export interface Trajectory {
  id: string;
  scene: string;
  intent: Intent;
  model: ModelInfo;
  steps: Step[];
  result?: TrajectoryResult;
  status: TrajectoryStatus;
  created_at: string;
}

// ── 流式事件（WebSocket / SSE）──────────────────────────────

export interface TrajectoryStartEvent {
  type: "trajectory_start";
  trajectory: Trajectory;
}

export interface StepEvent {
  type: "step";
  step: Step;
}

export interface ThoughtDeltaEvent {
  type: "thought_delta";
  index: number;
  delta: string;
}

export interface TrajectoryEndEvent {
  type: "trajectory_end";
  result: TrajectoryResult;
  status: TrajectoryStatus;
}

export interface ErrorEvent {
  type: "error";
  message: string;
}

export type StreamEvent =
  | TrajectoryStartEvent
  | StepEvent
  | ThoughtDeltaEvent
  | TrajectoryEndEvent
  | ErrorEvent;
