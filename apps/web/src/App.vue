<script setup lang="ts">
import { onMounted, ref } from "vue";
import { getConfig } from "./api/client";
import D0View from "./scenes/d0-browser/D0View.vue";

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
        <div class="brand-txt">
          <h1>认知基模 · Active Lifting</h1>
          <p class="tag">不是在模仿人说话，是在建模人的思维 · Not fitting language. Modeling cognition.</p>
        </div>
      </div>
      <div class="conn" :class="{ ok: connected }">
        {{ connected ? "引擎已连接" : "引擎未连接" }}
      </div>
    </header>

    <main>
      <D0View />
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
main {
  flex: 1;
  min-height: 0;
}
</style>
