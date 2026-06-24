<script setup lang="ts">
import { computed } from "vue";
import type { Step } from "@ap/protocol";
import { abilityOf, type AbilityKey } from "./narrate";

const props = defineProps<{ current: Step | null }>();
const active = computed<AbilityKey | null>(() => abilityOf(props.current));

const items: { key: AbilityKey; idx: string; title: string; desc: string }[] = [
  { key: "explore", idx: "①", title: "知道该看哪里", desc: "主动选择看哪里、跳过无关" },
  { key: "sampling", idx: "②", title: "想得少但想得对", desc: "拿不准就停下多想，更快想对" },
  { key: "approx", idx: "③", title: "学得少但学得准", desc: "更少数据逼近背后的规律" },
];
</script>

<template>
  <div class="legend">
    <header class="lg-hd"><span class="dot" /> 三大能力</header>
    <div class="lg-list">
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
