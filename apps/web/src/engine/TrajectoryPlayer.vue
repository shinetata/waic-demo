<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from "vue";
import StageView from "./StageView.vue";
import MindStream from "./MindStream.vue";
import StatsPanel from "./StatsPanel.vue";
import { usePlayer } from "./usePlayer";

const props = defineProps<{
  side: "ours" | "baseline";
  scene: string;
  role: string;
  modelLabel?: string;
  previewImage?: string;
  autostart?: boolean;
}>();

const player = usePlayer(props.side);
const { steps, currentIndex, status, result, intent, model } = player;

const persona = computed(() => intent.value?.persona || props.role);
const label = computed(() => props.modelLabel || model.value?.name || props.side);
const statusText = computed(
  () => ({ idle: "待运行", running: "观察中…", done: "完成", error: "出错" })[status.value],
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
      :preview-image="previewImage"
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

    <transition name="ocard">
      <div v-if="status === 'done' && result?.output" class="output-card" :class="side">
        <span class="oc-tag">产出</span>
        <div class="oc-text">
          <div class="oc-main">{{ result.output }}</div>
          <div v-if="result.conclusion" class="oc-sub">{{ result.conclusion }}</div>
        </div>
      </div>
    </transition>
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
.output-card {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  background: var(--ours-soft);
  border: 1px solid rgba(0, 102, 255, 0.25);
  border-radius: var(--radius);
  padding: 14px 16px;
}
.baseline .output-card {
  background: var(--baseline-soft);
  border-color: rgba(255, 107, 53, 0.3);
}
.oc-tag {
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  background: var(--ours);
  padding: 4px 10px;
  border-radius: 6px;
  white-space: nowrap;
}
.baseline .oc-tag {
  background: var(--baseline);
}
.oc-main {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1.55;
}
.oc-sub {
  font-size: 12px;
  color: var(--ink-dim);
  margin-top: 5px;
  line-height: 1.5;
}
.ocard-enter-active {
  transition: all 0.5s ease;
}
.ocard-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
</style>
