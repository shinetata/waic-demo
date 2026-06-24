<script setup lang="ts">
import { computed } from "vue";
import type { Step } from "@ap/protocol";
import { assetUrl } from "../api/client";
import { narrate } from "./narrate";

const props = defineProps<{
  previewImage?: string;
  steps: Step[];
  currentIndex: number;
}>();

const visible = computed(() => props.steps.slice(0, props.currentIndex + 1));
const current = computed<Step | null>(() => props.steps[props.currentIndex] ?? null);
const curStage = computed(() => current.value?.stage ?? "");
const running = computed(() => props.currentIndex >= 0 && !!current.value);

const cropUrl = computed(() =>
  current.value?.observation?.crop_image ? assetUrl(current.value.observation.crop_image) : "",
);
const thumbUrl = computed(() =>
  current.value?.observation?.thumbnail ? assetUrl(current.value.observation.thumbnail) : "",
);
// 主视图：运行后=当前所见局部高清；运行前=整页首图占位
const mainImage = computed(() => cropUrl.value || props.previewImage || "");

const curType = computed(() => current.value?.action.type ?? "");
const curLabel = computed(() => {
  const l = current.value?.action.label ?? "";
  return l.replace(/^(SEE|ZOOM[-_ ]?IN|ZOOM[-_ ]?OUT|CLICK|NAVIGATE|OUTPUT:?)\s*/i, "").trim();
});
const curZoom = computed(() => current.value?.observation?.zoom_level ?? 1);
const narration = computed(() => narrate(current.value));

// 小地图轨迹：仅连当前 stage 内、有 rect 的步
interface Node {
  x: number;
  y: number;
  type: string;
}
const stageSteps = computed(() =>
  visible.value.filter((s) => s.stage === curStage.value && s.observation?.rect),
);
const nodes = computed<Node[]>(() =>
  stageSteps.value.map((s) => {
    const r = s.observation!.rect!;
    return { x: (r.x + r.w / 2) * 100, y: (r.y + r.h / 2) * 100, type: s.action.type };
  }),
);
const polyPoints = computed(() => nodes.value.map((n) => `${n.x},${n.y}`).join(" "));
</script>

<template>
  <div class="stage">
    <div class="main">
      <img v-if="mainImage" :src="mainImage" class="main-img" alt="模型当前所见" />

      <div v-if="running" class="cur-badge">
        <b :data-type="curType">{{ curType }}</b>
        <span v-if="curLabel">{{ curLabel }}</span>
        <em v-if="curZoom > 1.2">{{ curZoom }}×</em>
      </div>
      <div v-else class="idle-hint">点击「运行」，看认知基模如何主动观察</div>

      <figure v-if="running && thumbUrl" class="minimap">
        <img :src="thumbUrl" alt="全局位置" />
        <svg class="traj" viewBox="0 0 100 100" preserveAspectRatio="none">
          <polyline v-if="nodes.length > 1" :points="polyPoints" />
        </svg>
        <span
          v-for="(n, i) in nodes"
          :key="i"
          class="node"
          :data-type="n.type"
          :class="{ cur: i === nodes.length - 1 }"
          :style="{ left: n.x + '%', top: n.y + '%' }"
        />
        <figcaption>全局位置 · 探索路径</figcaption>
      </figure>
    </div>

    <div class="narration" :class="{ on: running }">
      <span class="nar-dot" />
      <span class="nar-text">{{ narration }}</span>
    </div>
  </div>
</template>

<style scoped>
.stage {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
}
.main {
  position: relative;
  flex: 1;
  min-height: 0;
  background: #0b0b0f;
  display: grid;
  place-items: center;
}
.main-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
}
.cur-badge {
  position: absolute;
  left: 14px;
  top: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.94);
  border-radius: 10px;
  padding: 6px 12px;
  box-shadow: var(--shadow);
  font-size: 13px;
}
.cur-badge b {
  font-family: var(--mono);
  font-size: 11px;
  color: #fff;
  background: var(--ours);
  padding: 2px 8px;
  border-radius: 6px;
}
.cur-badge b[data-type="zoom_in"],
.cur-badge b[data-type="zoom_out"] {
  background: var(--gold);
}
.cur-badge b[data-type="none"] {
  background: #8a8a90;
}
.cur-badge b[data-type="eos"] {
  background: var(--ok);
}
.cur-badge em {
  font-style: normal;
  font-family: var(--mono);
  color: var(--ink-dim);
}
.idle-hint {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #fff;
  opacity: 0.82;
  font-size: 15px;
}
.minimap {
  position: absolute;
  right: 14px;
  top: 14px;
  width: 26%;
  max-width: 240px;
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: var(--shadow-lg);
  line-height: 0;
}
.minimap img {
  width: 100%;
  display: block;
}
.minimap .traj {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.minimap .traj polyline {
  fill: none;
  stroke: var(--ours);
  stroke-width: 2;
  stroke-dasharray: 4 3;
  opacity: 0.85;
  vector-effect: non-scaling-stroke;
}
.node {
  position: absolute;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  background: var(--ours);
  border: 2px solid #fff;
}
.node[data-type="zoom_in"],
.node[data-type="zoom_out"] {
  background: var(--gold);
}
.node[data-type="none"] {
  background: #8a8a90;
}
.node[data-type="eos"] {
  background: var(--ok);
}
.node.cur {
  width: 13px;
  height: 13px;
  animation: pulse 1.1s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(0, 102, 255, 0.5);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(0, 102, 255, 0);
  }
}
.minimap figcaption {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  font-size: 10px;
  text-align: center;
  background: rgba(255, 255, 255, 0.92);
  color: var(--ink-dim);
  padding: 3px;
  line-height: 1.2;
}
.narration {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 18px;
  background: linear-gradient(90deg, #0a2a6b, var(--ours));
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  min-height: 54px;
  flex-shrink: 0;
}
.narration .nar-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #fff;
  opacity: 0.5;
  flex-shrink: 0;
}
.narration.on .nar-dot {
  opacity: 1;
  animation: blink 1s ease-in-out infinite;
}
@keyframes blink {
  50% {
    opacity: 0.3;
  }
}
</style>
