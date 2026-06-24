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
