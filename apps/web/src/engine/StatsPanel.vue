<script setup lang="ts">
import { computed } from "vue";
import type { TrajectoryResult } from "@ap/protocol";

const props = defineProps<{
  result: TrajectoryResult | null;
  side: "ours" | "baseline";
}>();

const stats = computed(() => props.result?.stats ?? null);
const zoomCount = computed(() => {
  const c = stats.value?.action_counts;
  return c ? (c.zoom_in ?? 0) + (c.zoom_out ?? 0) : 0;
});
const noneCount = computed(() => stats.value?.action_counts?.none ?? 0);
</script>

<template>
  <div class="stats" :class="side">
    <div class="kv">
      <span>观察步数</span><b>{{ stats?.total_steps ?? "–" }}</b>
    </div>
    <div class="kv">
      <span>放大次数</span><b>{{ stats ? zoomCount : "–" }}</b>
    </div>
    <div class="kv">
      <span>跳过区域</span><b>{{ stats?.skipped_regions ?? "–" }}</b>
    </div>
    <div class="kv">
      <span>连续思考</span><b>{{ stats ? noneCount : "–" }}</b>
    </div>
    <div class="kv">
      <span>自主终止</span>
      <b :class="{ ok: stats?.reached_eos }">{{
        stats ? (stats.reached_eos ? "✓ EOS" : "截断") : "–"
      }}</b>
    </div>
    <div v-if="stats?.tokens" class="kv">
      <span>Token</span><b>{{ stats.tokens.total }}</b>
    </div>
    <div v-if="stats?.duration_ms" class="kv">
      <span>耗时</span><b>{{ (stats.duration_ms / 1000).toFixed(1) }}s</b>
    </div>
  </div>
</template>

<style scoped>
.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.kv {
  flex: 1;
  min-width: 72px;
  background: var(--surface);
  border-radius: 10px;
  padding: 8px 10px;
  box-shadow: var(--shadow);
  border-top: 3px solid var(--ours);
}
.baseline .kv {
  border-top-color: var(--baseline);
}
.kv span {
  display: block;
  font-size: 11px;
  color: var(--ink-dim);
  margin-bottom: 3px;
}
.kv b {
  font-family: var(--mono);
  font-size: 18px;
  font-weight: 700;
}
.kv b.ok {
  color: var(--ok);
}
</style>
