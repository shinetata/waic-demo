<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import type { Step } from "@ap/protocol";

const props = defineProps<{
  steps: Step[];
  currentIndex: number;
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

const ACT_TEXT: Record<string, string> = {
  see: "观察",
  zoom_in: "放大",
  zoom_out: "缩小",
  scroll: "移动",
  click: "进入",
  navigate: "回看",
  snapshot: "回到全局",
  none: "深度推演",
  eos: "输出结论",
};
</script>

<template>
  <div class="mind">
    <header class="mind-hd"><span class="dot" /> 模型思维路径</header>
    <ol ref="listEl" class="mind-list">
      <li
        v-for="s in visible"
        :key="s.index"
        :class="{ cur: s.index === currentIndex, think: s.action.type === 'none' }"
      >
        <p class="th">
          <span v-if="s.action.type === 'none'" class="pause">⏸</span>{{ s.thought }}
        </p>
        <span class="act" :data-type="s.action.type">{{
          ACT_TEXT[s.action.type] || s.action.type
        }}</span>
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
  flex: 1;
  min-height: 0;
}
.mind-hd {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}
.mind-hd .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ours);
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
  display: flex;
  flex-direction: column;
  gap: 5px;
  transition: background 0.2s;
}
.mind-list li.cur {
  background: var(--ours-soft);
  border-color: rgba(0, 102, 255, 0.25);
}
.mind-list li.think {
  background: #fff8e6;
  border-color: #ffe2a6;
}
.mind-list li.think.cur {
  background: #fff1cc;
  border-color: var(--gold);
}
.th {
  font-size: 13px;
  color: var(--ink);
  line-height: 1.55;
}
.th .pause {
  color: #b8860b;
  margin-right: 5px;
  font-weight: 700;
}
.act {
  align-self: flex-start;
  font-family: var(--mono);
  font-size: 10px;
  padding: 1px 8px;
  border-radius: 5px;
  background: var(--ours-soft);
  color: var(--ours);
}
.act[data-type="none"] {
  background: #fff1cc;
  color: #8a5a00;
}
.act[data-type="eos"] {
  background: #e7f9ef;
  color: var(--ok);
}
.act[data-type="zoom_in"],
.act[data-type="zoom_out"] {
  background: #fff3e0;
  color: #e67700;
}
</style>
