<script setup lang="ts">
import { onMounted, ref } from "vue";
import { getConfig } from "./api/client";
import D0View from "./scenes/d0-browser/D0View.vue";
import InvestigationView from "./scenes/d4-investigation/InvestigationView.vue";

const tab = ref<"d0" | "d4">("d0");
const connected = ref(false);

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
        <div>
          <h1>Active Lifting · 主动感知</h1>
          <p class="tag">Not fitting language. Modeling cognition.</p>
        </div>
      </div>
      <div class="right">
        <nav class="tabs">
          <button :class="{ on: tab === 'd0' }" @click="tab = 'd0'">D0 浏览器主动感知</button>
          <button :class="{ on: tab === 'd4' }" @click="tab = 'd4'">D4 多源破案</button>
        </nav>
        <div class="conn" :class="{ ok: connected }">
          {{ connected ? "引擎已连接" : "引擎未连接" }}
        </div>
      </div>
    </header>

    <main>
      <D0View v-if="tab === 'd0'" />
      <InvestigationView v-else />
    </main>
  </div>
</template>

<style scoped>
.app {
  max-width: 1480px;
  margin: 0 auto;
  padding: 20px 28px 44px;
}
.hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}
.brand {
  display: flex;
  gap: 14px;
  align-items: center;
}
.logo {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--ours), #4f8bff);
  color: #fff;
  font-weight: 800;
  display: grid;
  place-items: center;
  font-size: 17px;
}
h1 {
  font-size: 19px;
}
.tag {
  font-size: 12px;
  color: var(--ink-dim);
  margin-top: 2px;
}
.right {
  display: flex;
  align-items: center;
  gap: 14px;
}
.tabs {
  display: flex;
  gap: 6px;
  background: var(--surface-2);
  padding: 4px;
  border-radius: 11px;
  border: 1px solid var(--line);
}
.tabs button {
  border: none;
  background: transparent;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-dim);
}
.tabs button.on {
  background: var(--ours);
  color: #fff;
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
</style>
