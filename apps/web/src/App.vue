<script setup lang="ts">
import { onMounted, ref } from "vue";
import { getConfig } from "./api/client";
import D0View from "./scenes/d0-browser/D0View.vue";
import D4View from "./scenes/d4-investigation/D4View.vue";

const connected = ref(false);
const tab = ref<"d0" | "d4">("d0");

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
        <button :class="{ on: tab === 'd0' }" @click="tab = 'd0'">D0 · 浏览器主动感知</button>
        <button :class="{ on: tab === 'd4' }" @click="tab = 'd4'">D4 · 多源破案</button>
      </nav>
      <div class="conn" :class="{ ok: connected }">
        {{ connected ? "引擎已连接" : "引擎未连接" }}
      </div>
    </header>

    <main>
      <D0View v-if="tab === 'd0'" />
      <D4View v-else />
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
  gap: 16px;
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
.tabs {
  display: flex;
  gap: 6px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 4px;
  box-shadow: var(--shadow);
}
.tabs button {
  border: none;
  background: transparent;
  color: var(--ink-dim);
  font-size: 14px;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 9px;
  cursor: pointer;
  white-space: nowrap;
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
  white-space: nowrap;
}
.conn.ok {
  background: #e7f9ef;
  color: var(--ok);
}
main {
  flex: 1;
  min-height: 0;
}
@media (max-width: 1200px) {
  .hd {
    flex-wrap: wrap;
  }
}
</style>
