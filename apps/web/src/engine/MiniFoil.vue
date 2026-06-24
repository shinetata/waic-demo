<script setup lang="ts">
import { computed, ref } from "vue";
import type { Step, TrajectoryResult } from "@ap/protocol";
import { assetUrl } from "../api/client";

const props = defineProps<{
  steps: Step[];
  currentIndex: number;
  status: string;
  result: TrajectoryResult | null;
  previewImage?: string;
}>();

const open = ref(true);
const current = computed<Step | null>(() => props.steps[props.currentIndex] ?? null);
const fullImg = computed(() => {
  const f = current.value?.observation?.full_image;
  return f ? assetUrl(f) : props.previewImage || "";
});
const conclusion = computed(() => props.result?.output || props.result?.conclusion || "");
const running = computed(() => props.status === "running");
const done = computed(() => props.status === "done");
</script>

<template>
  <div class="foil" :class="{ collapsed: !open }">
    <header class="foil-hd" @click="open = !open">
      <span class="tag">现有做法</span>
      <span class="sub">一次性读入、读完再想</span>
      <span class="chev">{{ open ? "▾" : "▸" }}</span>
    </header>
    <div v-if="open" class="foil-body">
      <div class="foil-img">
        <img v-if="fullImg" :src="fullImg" alt="一次性读入整页" />
        <div class="flood">整页<br />一次性读入</div>
      </div>
      <div class="foil-out">
        <template v-if="done">{{ conclusion }}</template>
        <span v-else-if="running" class="muted">读完整页中…</span>
        <span v-else class="muted">等待运行</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.foil {
  background: var(--surface-2);
  border: 1px dashed var(--line);
  border-radius: var(--radius);
  overflow: hidden;
  flex-shrink: 0;
}
.foil-hd {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  cursor: pointer;
  user-select: none;
}
.foil-hd .tag {
  font-size: 11px;
  font-weight: 700;
  color: var(--ink-dim);
  background: #e9e9ee;
  padding: 2px 8px;
  border-radius: 6px;
}
.foil-hd .sub {
  font-size: 11px;
  color: var(--ink-mute);
}
.foil-hd .chev {
  margin-left: auto;
  color: var(--ink-mute);
  font-size: 12px;
}
.foil-body {
  display: flex;
  gap: 10px;
  padding: 0 12px 12px;
}
.foil-img {
  position: relative;
  width: 78px;
  height: 78px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
  background: #000;
}
.foil-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.5;
}
.foil-img .flood {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: 10px;
  color: #fff;
  text-align: center;
  line-height: 1.3;
  background: rgba(255, 107, 53, 0.34);
}
.foil-out {
  font-size: 12px;
  color: var(--ink);
  line-height: 1.5;
  flex: 1;
  max-height: 80px;
  overflow-y: auto;
}
.foil-out .muted {
  color: var(--ink-mute);
}
</style>
