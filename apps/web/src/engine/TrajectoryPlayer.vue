<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from "vue";
import StageView from "./StageView.vue";
import MindStream from "./MindStream.vue";
import StatsPanel from "./StatsPanel.vue";
import { usePlayer } from "./usePlayer";
import { assetUrl } from "../api/client";

const props = defineProps<{
  side: "ours" | "baseline";
  scene: string;
  role: string;
  modelLabel?: string;
  autostart?: boolean;
}>();

const player = usePlayer(props.side);
const { steps, currentIndex, status, result, intent, model } = player;

const fullImage = computed(() => {
  const o = steps.value[0]?.observation;
  return o?.full_image ? assetUrl(o.full_image) : "";
});
const persona = computed(() => intent.value?.persona || props.role);
const label = computed(() => props.modelLabel || model.value?.name || props.side);
const statusText = computed(
  () =>
    ({ idle: "待运行", running: "观察中…", done: "完成", error: "出错" })[status.value],
);

function startLive() {
  player.startLive(props.scene, props.role);
}
function startReplay(id: string, ms = 1200) {
  player.startReplay(id, ms);
}
function reset() {
  player.reset();
}

const emit = defineEmits<{ (e: "done"): void }>();
watch(status, (s) => {
  if (s === "done" || s === "error") emit("done");
});

onMounted(() => {
  if (props.autostart) startLive();
});
onBeforeUnmount(() => player.reset());

defineExpose({ startLive, startReplay, reset, status, result, currentIndex });
</script>

<template>
  <div class="player" :class="side">
    <div class="phead">
      <span class="badge">{{ side === "ours" ? "OURS" : "BASELINE" }}</span>
      <span class="ml">{{ label }}</span>
      <span class="st" :data-s="status">{{ statusText }}</span>
    </div>
    <StageView
      :full-image="fullImage"
      :steps="steps"
      :current-index="currentIndex"
      :side="side"
    />
    <div class="lower">
      <MindStream
        :steps="steps"
        :current-index="currentIndex"
        :persona="persona"
        :model-label="label"
        :side="side"
      />
    </div>
    <StatsPanel :result="result" :side="side" />
  </div>
</template>

<style scoped>
.player {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.phead {
  display: flex;
  align-items: center;
  gap: 10px;
}
.badge {
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 6px;
  background: var(--ours);
  color: #fff;
}
.baseline .badge {
  background: var(--baseline);
}
.ml {
  font-size: 13px;
  font-weight: 600;
}
.st {
  margin-left: auto;
  font-size: 12px;
  color: var(--ink-dim);
}
.st[data-s="running"] {
  color: var(--ours);
}
.baseline .st[data-s="running"] {
  color: var(--baseline);
}
.st[data-s="done"] {
  color: var(--ok);
}
.lower {
  height: 240px;
}
</style>
