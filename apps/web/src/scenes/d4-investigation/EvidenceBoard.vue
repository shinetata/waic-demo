<script setup lang="ts">
import { computed } from "vue";
import type { Step } from "@ap/protocol";
import type { InvestigationCase } from "../../api/client";

const props = defineProps<{
  caseData: InvestigationCase | null;
  steps: Step[];
  currentIndex: number;
}>();

const visible = computed(() => props.steps.slice(0, props.currentIndex + 1));
const current = computed<Step | null>(() => props.steps[props.currentIndex] ?? null);

const curStage = computed(() => {
  const stage = current.value?.observation?.stage;
  if (stage) return stage;
  const t = current.value?.action.target;
  return t && t.kind === "element" ? t.element_id : "";
});
const focusId = computed(() => curStage.value.replace("_footnote", ""));
const footnoteOpen = computed(() => curStage.value.endsWith("_footnote"));
const conflictActive = computed(() =>
  visible.value.some((s) => (s.action.label || "").startsWith("CONFLICT")),
);
const resolved = computed(() =>
  visible.value.some((s) => s.action.type === "eos" || (s.action.label || "") === "RESOLVED"),
);
const conflict = computed(() => props.caseData?.conflict ?? []);
</script>

<template>
  <div class="board">
    <div class="sources">
      <div
        v-for="s in caseData?.sources ?? []"
        :key="s.id"
        class="src"
        :class="{ focus: focusId === s.id, inconflict: conflict.includes(s.id) }"
      >
        <div class="src-hd">
          <span class="sid">{{ s.id }}</span>{{ s.title }}
        </div>
        <div class="val">{{ s.value }}</div>
        <div class="detail">{{ s.detail }}</div>
        <div
          v-if="s.footnote"
          class="footnote"
          :class="{ open: footnoteOpen && focusId === s.id }"
        >
          {{ s.footnote }}
        </div>
      </div>
    </div>

    <div class="relation" :class="{ active: conflictActive, resolved }">
      <template v-if="resolved">
        ✓ {{ conflict[0] }} 与 {{ conflict[1] }} 口径不同，矛盾已解释
      </template>
      <template v-else-if="conflictActive">
        ⚠ {{ conflict[0] }} ↔ {{ conflict[1] }} 数字对不上
      </template>
      <template v-else>等待逐源比对…</template>
    </div>
  </div>
</template>

<style scoped>
.board {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.sources {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.src {
  background: var(--surface);
  border-radius: var(--radius);
  padding: 14px;
  box-shadow: var(--shadow);
  border: 2px solid transparent;
  transition:
    border-color 0.3s,
    transform 0.3s;
}
.src.focus {
  border-color: var(--ours);
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}
.src-hd {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}
.sid {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: var(--ink);
  color: #fff;
  display: grid;
  place-items: center;
  font-family: var(--mono);
  font-size: 12px;
}
.val {
  font-family: var(--mono);
  font-size: 26px;
  font-weight: 800;
  margin: 8px 0 4px;
  color: var(--ours);
}
.detail {
  font-size: 12px;
  color: var(--ink-dim);
}
.footnote {
  margin-top: 10px;
  font-size: 11px;
  color: var(--ink-mute);
  padding: 6px 8px;
  border-radius: 7px;
  background: var(--surface-2);
  border: 1px dashed var(--line);
  transition: all 0.4s;
}
.footnote.open {
  color: #7a4f00;
  background: #fff3d6;
  border: 1px solid var(--gold);
  font-size: 13px;
  font-weight: 600;
  transform: scale(1.04);
  box-shadow: 0 4px 16px rgba(245, 166, 35, 0.3);
}
.relation {
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  padding: 12px;
  border-radius: var(--radius);
  background: var(--surface-2);
  color: var(--ink-mute);
  border: 1px solid var(--line);
  transition: all 0.4s;
}
.relation.active {
  background: #fff0ee;
  color: var(--warn);
  border-color: #ffd0c8;
}
.relation.resolved {
  background: #e7f9ef;
  color: var(--ok);
  border-color: #b6ecca;
}
</style>
