<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import type { Step } from "@ap/protocol";

const props = defineProps<{
  steps: Step[];
  currentIndex: number;
  persona?: string;
  modelLabel?: string;
  side: "ours" | "baseline";
}>();

const visible = computed(() => props.steps.slice(0, props.currentIndex + 1));
const listEl = ref<HTMLElement | null>(null);

watch(
  () => props.currentIndex,
  async () => {
    await nextTick();
    const el = listEl.value;
    if (el) el.scrollTop = el.scrollHeight;
  },
);
</script>

<template>
  <div class="mind" :class="side">
    <header v-if="persona" class="mind-hd">
      <span class="dot" />
      <span class="persona">{{ persona }}</span>
      <em v-if="modelLabel">{{ modelLabel }}</em>
    </header>
    <ol ref="listEl" class="mind-list">
      <li v-for="s in visible" :key="s.index" :class="{ cur: s.index === currentIndex }">
        <div class="line">
          <span class="idx">{{ s.index }}</span>
          <span class="act" :data-type="s.action.type">{{ s.action.type }}</span>
          <span class="lab">{{ s.action.label }}</span>
        </div>
        <p class="th">{{ s.thought }}</p>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.mind {
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
  height: 100%;
}
.mind-hd {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
  font-weight: 600;
}
.mind-hd .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ours);
}
.baseline .mind-hd .dot {
  background: var(--baseline);
}
.mind-hd em {
  margin-left: auto;
  font-style: normal;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ink-dim);
}
.mind-list {
  list-style: none;
  overflow-y: auto;
  padding: 8px;
  flex: 1;
  scroll-behavior: smooth;
}
.mind-list li {
  padding: 8px 10px;
  border-radius: 9px;
  margin-bottom: 4px;
  border: 1px solid transparent;
  transition: background 0.2s;
}
.mind-list li.cur {
  background: var(--ours-soft);
  border-color: rgba(0, 102, 255, 0.25);
}
.baseline .mind-list li.cur {
  background: var(--baseline-soft);
  border-color: rgba(255, 107, 53, 0.25);
}
.line {
  display: flex;
  align-items: center;
  gap: 8px;
}
.idx {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ink-mute);
  min-width: 16px;
}
.act {
  font-family: var(--mono);
  font-size: 10px;
  padding: 1px 7px;
  border-radius: 5px;
  background: var(--ours-soft);
  color: var(--ours);
}
.act[data-type="zoom_in"],
.act[data-type="zoom_out"] {
  background: #fff3e0;
  color: #e67700;
}
.act[data-type="none"] {
  background: #f0f0f3;
  color: #6e6e73;
}
.act[data-type="eos"] {
  background: #e7f9ef;
  color: var(--ok);
}
.act[data-type="snapshot"] {
  background: #e0f7fa;
  color: #00838f;
}
.lab {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ink-dim);
}
.th {
  font-size: 13px;
  margin-top: 4px;
  color: var(--ink);
  line-height: 1.5;
}
</style>
