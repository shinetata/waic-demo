<script setup lang="ts">
import { onMounted, ref } from "vue";
import { getConfig } from "./api/client";
import D0View from "./scenes/d0-browser/D0View.vue";
import D4View from "./scenes/d4-investigation/D4View.vue";

const connected = ref(false);
type DemoKey = "d0" | "d4";
const demo = ref<DemoKey>("d0");
const tabs: { key: DemoKey; label: string; sub: string }[] = [
  { key: "d0", label: "浏览器主动感知", sub: "" },
  { key: "d4", label: "多源破案", sub: "" },
];

onMounted(async () => {
  try {
    await getConfig();
    connected.value = true;
  } catch {
    connected.value = false;
  }
});
</script>

<template>
  <div class="app">
    <header class="hd">
      <div class="brand">
        <div class="logo">AL</div>
        <div class="brand-txt">
          <h1>认知基模 · Active Lifting</h1>
          <p class="tag">不是在模仿人说话，是在建模人的思维 · Not fitting language. Modeling cognition.</p>
        </div>
      </div>
      <nav class="tabs">
        <button
          v-for="t in tabs"
          :key="t.key"
          class="tab"
          :class="{ on: demo === t.key }"
          @click="demo = t.key"
        >
          {{ t.label }}<small>{{ t.sub }}</small>
        </button>
      </nav>
      <div class="conn" :class="{ ok: connected }">
        {{ connected ? "引擎已连接" : "引擎未连接" }}
      </div>
    </header>

    <main>
      <D0View v-show="demo === 'd0'" />
      <D4View v-show="demo === 'd4'" />
    </main>
  </div>
</template>

<style scoped>
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  max-width: 1680px;
  margin: 0 auto;
  padding: 14px 24px 16px;
  overflow: hidden;
}
.hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-shrink: 0;
}
.brand {
  display: flex;
  gap: 14px;
  align-items: center;
}
.logo {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--ours), #4f8bff);
  color: #fff;
  font-weight: 800;
  display: grid;
  place-items: center;
  font-size: 17px;
}
h1 {
  font-size: 20px;
}
.tag {
  font-size: 12px;
  color: var(--ink-dim);
  margin-top: 3px;
}
.conn {
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--baseline-soft);
  color: var(--baseline);
}
.conn.ok {
  background: #e7f9ef;
  color: var(--ok);
}
.tabs {
  display: flex;
  gap: 8px;
  background: var(--surface-2);
  padding: 4px;
  border-radius: 12px;
  border: 1px solid var(--line);
}
.tab {
  border: none;
  background: transparent;
  border-radius: 9px;
  padding: 7px 16px;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink-dim);
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.2;
  transition: all 0.2s;
}
.tab small {
  font-size: 10px;
  font-weight: 600;
  opacity: 0.75;
  margin-top: 2px;
}
.tab.on {
  background: var(--ours);
  color: #fff;
  box-shadow: var(--shadow);
}
main {
  flex: 1;
  min-height: 0;
}
main > * {
  height: 100%;
}
</style>
