<script setup lang="ts">
import { computed } from "vue";
import type { Step } from "@ap/protocol";
import { assetUrl } from "../api/client";

const props = defineProps<{
  previewImage?: string;
  steps: Step[];
  currentIndex: number;
  side: "ours" | "baseline";
}>();

interface Node {
  x: number;
  y: number;
  type: string;
}

const visible = computed(() => props.steps.slice(0, props.currentIndex + 1));
const current = computed<Step | null>(() => props.steps[props.currentIndex] ?? null);
const curStage = computed(() => current.value?.stage ?? "");

// 当前 stage 主图：运行后随 step 切换(home→detail)，运行前回退到首图
const fullImage = computed(() => {
  const f = current.value?.observation?.full_image;
  return f ? assetUrl(f) : props.previewImage || "";
});

// 轨迹折线/节点只连当前 stage 内的步（不同 stage 图坐标系不同）
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

const attnRect = computed(() => current.value?.observation?.rect ?? null);
const attnStyle = computed(() => {
  const r = attnRect.value;
  if (!r) return {};
  return {
    left: `${r.x * 100}%`,
    top: `${r.y * 100}%`,
    width: `${r.w * 100}%`,
    height: `${r.h * 100}%`,
  };
});

const cropUrl = computed(() =>
  current.value?.observation?.crop_image ? assetUrl(current.value.observation.crop_image) : "",
);
const curType = computed(() => current.value?.action.type ?? "");
const curLabel = computed(() => current.value?.action.label ?? "");
const curZoom = computed(() => current.value?.observation?.zoom_level ?? 1);
</script>

<template>
  <div class="stage" :class="side">
    <img v-if="fullImage" class="base" :src="fullImage" alt="scene" />

    <svg class="traj" viewBox="0 0 100 100" preserveAspectRatio="none">
      <polyline v-if="nodes.length > 1" :points="polyPoints" />
    </svg>

    <div
      v-for="(n, i) in nodes"
      :key="i"
      class="node"
      :data-type="n.type"
      :class="{ cur: i === nodes.length - 1 }"
      :style="{ left: n.x + '%', top: n.y + '%' }"
    />

    <div v-if="attnRect" class="attn" :style="attnStyle">
      <span class="attn-tag">{{ curType }}</span>
    </div>

    <figure v-if="cropUrl" class="peek">
      <div class="peek-hd">模型当前所见 · {{ curZoom }}×</div>
      <img :src="cropUrl" alt="local view" />
      <figcaption><b :data-type="curType">{{ curType }}</b> {{ curLabel }}</figcaption>
    </figure>
  </div>
</template>

<style scoped>
.stage {
  position: relative;
  width: 100%;
  line-height: 0;
  border-radius: var(--radius);
  overflow: hidden;
  background: #000;
  box-shadow: var(--shadow);
}
.base {
  width: 100%;
  height: auto;
  display: block;
  opacity: 0.96;
}
.traj {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.traj polyline {
  fill: none;
  stroke: var(--ours);
  stroke-width: 2;
  stroke-linejoin: round;
  stroke-linecap: round;
  opacity: 0.75;
  vector-effect: non-scaling-stroke;
  stroke-dasharray: 4 3;
}
.baseline .traj polyline {
  stroke: var(--baseline);
}
.node {
  position: absolute;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  background: var(--ours);
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.15);
}
.node[data-type="zoom_in"],
.node[data-type="zoom_out"] {
  background: #f5a623;
}
.node[data-type="none"] {
  background: #9e9e9e;
}
.node[data-type="eos"] {
  background: var(--ok);
}
.node[data-type="snapshot"] {
  background: #00bcd4;
}
.node.cur {
  width: 15px;
  height: 15px;
  animation: pulse 1.1s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(0, 102, 255, 0.5);
  }
  50% {
    box-shadow: 0 0 0 9px rgba(0, 102, 255, 0);
  }
}
.attn {
  position: absolute;
  border: 2.5px solid var(--ours);
  border-radius: 6px;
  background: rgba(0, 102, 255, 0.08);
  box-shadow: 0 0 0 9999px rgba(255, 255, 255, 0.02);
  transition:
    left 0.55s cubic-bezier(0.22, 0.61, 0.36, 1),
    top 0.55s cubic-bezier(0.22, 0.61, 0.36, 1),
    width 0.55s cubic-bezier(0.22, 0.61, 0.36, 1),
    height 0.55s cubic-bezier(0.22, 0.61, 0.36, 1);
}
.baseline .attn {
  border-color: var(--baseline);
  background: rgba(255, 107, 53, 0.08);
}
.attn-tag {
  position: absolute;
  top: -20px;
  left: -2px;
  font-family: var(--mono);
  font-size: 10px;
  color: #fff;
  background: var(--ours);
  padding: 1px 6px;
  border-radius: 4px;
  line-height: 1.6;
}
.baseline .attn-tag {
  background: var(--baseline);
}
.peek {
  position: absolute;
  right: 12px;
  top: 12px;
  width: 38%;
  max-width: 280px;
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: var(--shadow-lg);
  line-height: 1.4;
}
.peek-hd {
  font-size: 10px;
  font-family: var(--mono);
  color: var(--ink-dim);
  padding: 5px 8px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--line);
}
.peek img {
  width: 100%;
  height: auto;
  display: block;
}
.peek figcaption {
  font-size: 11px;
  padding: 6px 8px;
  color: var(--ink);
}
.peek figcaption b {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--ours);
  margin-right: 4px;
}
.peek figcaption b[data-type="zoom_in"] {
  color: #e67700;
}
</style>
