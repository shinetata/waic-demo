<script setup lang="ts">
import { computed } from "vue";
import type { Step } from "@ap/protocol";
import { abilityOf, type AbilityKey } from "./narrate";

const props = defineProps<{
  current: Step | null;
  forceActive?: AbilityKey | null;
  horizontal?: boolean;
}>();
// forceActive 显式传入时优先（D4 多源破案据 resolver/eos 高亮分布逼近）；否则按动作类型推断
const active = computed<AbilityKey | null>(() =>
  props.forceActive !== undefined ? props.forceActive : abilityOf(props.current),
);

const items: { key: AbilityKey; idx: string; title: string; desc: string }[] = [
  { key: "explore", idx: "①", title: "主动探索", desc: "自主聚焦关键信息，智能过滤无关内容" },
  { key: "sampling", idx: "②", title: "隐空间采样效率", desc: "不确定时深度推演，以更少步数确保准确性" },
  { key: "approx", idx: "③", title: "分布逼近", desc: "更少数据逼近底层的规律" },
];
</script>

<template>
  <div class="legend">
    <header class="lg-hd"><span class="dot" /> 核心能力</header>
    <div class="lg-list" :class="{ row: horizontal }">
      <div
        v-for="it in items"
        :key="it.key"
        class="lg-item"
        :class="{ on: active === it.key }"
      >
        <div class="lg-top"><span class="idx">{{ it.idx }}</span>{{ it.title }}</div>
        <div class="lg-desc">{{ it.desc }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.legend {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
  flex-shrink: 0;
}
.lg-hd {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
  font-weight: 700;
}
.lg-hd .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ours);
}
.lg-list {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.lg-list.row {
  flex-direction: row;
}
.lg-list.row .lg-item {
  flex: 1;
  min-width: 0;
}
.lg-item {
  padding: 8px 11px;
  border-radius: 9px;
  border: 1px solid var(--line);
  background: var(--surface-2);
  transition: all 0.25s;
}
.lg-item.on {
  background: var(--ours);
  border-color: var(--ours);
  transform: translateX(2px);
}
.lg-item.on .lg-top,
.lg-item.on .lg-desc {
  color: #fff;
}
.lg-top {
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
  display: flex;
  gap: 6px;
  align-items: center;
}
.lg-top .idx {
  font-family: var(--mono);
}
.lg-desc {
  font-size: 11px;
  color: var(--ink-dim);
  margin-top: 2px;
}
</style>
