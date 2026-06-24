import type { StreamEvent, Trajectory } from "@ap/protocol";

const BASE = import.meta.env.VITE_ENGINE_URL || "http://127.0.0.1:8000";

export const engineBase = BASE;

/** 把引擎返回的资源路径（/assets/...）拼成可访问 URL */
export function assetUrl(path?: string): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return BASE + path;
}

export interface ModelMeta {
  label: string;
  name: string;
  provider: string;
}
export interface EngineConfig {
  max_steps: number;
  models: { ours: ModelMeta; baseline: ModelMeta };
}
export interface RoleMeta {
  key: string;
  persona: string;
  prompt: string;
}
export interface SceneMeta {
  id: string;
  title: string;
  roles: RoleMeta[];
}

export async function getConfig(): Promise<EngineConfig> {
  const r = await fetch(`${BASE}/api/config`);
  return r.json();
}

export async function getScenes(): Promise<SceneMeta[]> {
  const r = await fetch(`${BASE}/api/scenes`);
  const data = await r.json();
  return data.scenes ?? [];
}

export async function getTrajectory(id: string): Promise<Trajectory> {
  const r = await fetch(`${BASE}/api/trajectories/${id}`);
  return r.json();
}

export interface TrajItem {
  id: string;
  scene: string;
  role: string;
  side: string;
  status: string;
  created_at: string;
}

export async function listTrajectories(): Promise<TrajItem[]> {
  const r = await fetch(`${BASE}/api/trajectories`);
  const d = await r.json();
  return (d.items ?? []) as TrajItem[];
}

export async function getPreview(
  scene: string,
  role: string,
): Promise<{ image: string; stage: string }> {
  const r = await fetch(
    `${BASE}/api/preview?scene=${encodeURIComponent(scene)}&role=${encodeURIComponent(role)}`,
  );
  const d = await r.json();
  return { image: d.image ? assetUrl(d.image) : "", stage: d.stage || "" };
}

// ── D4 多源破案：证据板 case spec（与 engine cases.py case_to_dict 对齐）──
export interface HeadlineClaim {
  element_id: string;
  metric: string;
  value_text: string;
  caliber: string;
}
export interface SourceNode {
  id: string;
  title: string;
  kind: string;
  headline: HeadlineClaim;
}
export interface ConflictEdge {
  a: string;
  b: string;
  label: string;
}
export interface CaseResolver {
  element_id: string;
  source_id: string;
  insight: string;
}
export interface CaseSpec {
  id: string;
  title: string;
  question: string;
  index_stage: string;
  sources: SourceNode[];
  conflicts: ConflictEdge[];
  resolver: CaseResolver;
  baseline_hint: string;
}

export async function getCase(scene: string): Promise<CaseSpec> {
  const r = await fetch(`${BASE}/api/case?scene=${encodeURIComponent(scene)}`);
  return r.json();
}

export interface RunParams {
  scene: string;
  role: string;
  side: "ours" | "baseline";
}

/** 建立 WebSocket 实时拉取一条 rollout 的流式事件。返回停止函数。 */
export function runStream(
  params: RunParams,
  onEvent: (e: StreamEvent) => void,
  onClose?: () => void,
): () => void {
  const wsBase = BASE.replace(/^http/, "ws");
  const url = `${wsBase}/ws/run?scene=${encodeURIComponent(params.scene)}&role=${encodeURIComponent(params.role)}&side=${params.side}`;
  const ws = new WebSocket(url);
  ws.onmessage = (m) => {
    try {
      onEvent(JSON.parse(m.data) as StreamEvent);
    } catch {
      /* ignore malformed frame */
    }
  };
  ws.onclose = () => onClose?.();
  return () => ws.close();
}
