<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { getCases, type InvestigationCase } from "../../api/client";
import { MindStream, usePlayer } from "../../engine";
import EvidenceBoard from "./EvidenceBoard.vue";

const cases = ref<InvestigationCase[]>([]);
const caseId = ref("revenue");
const player = usePlayer("ours");
const { steps, currentIndex, status, result } = player;

const caseData = computed(() => cases.value.find((c) => c.id === caseId.value) ?? null);

onMounted(async () => {
  try {
    cases.value = await getCases();
    if (cases.value[0]) caseId.value = cases.value[0].id;
  } catch {
    /* 引擎未连接 */
  }
});

function run() {
  player.reset();
  player.startLive("d4-investigation", caseId.value);
}
</script>

<template>
  <div class="d4">
    <section class="ctl">
      <label>案件
        <select v-model="caseId">
          <option v-for="c in cases" :key="c.id" :value="c.id">{{ c.title }}</option>
        </select>
      </label>
      <p class="q">{{ caseData?.question }}</p>
      <button class="run" :disabled="status === 'running'" @click="run">▶ 开始破案</button>
    </section>

    <section class="body">
      <div class="left">
        <EvidenceBoard :case-data="caseData" :steps="steps" :current-index="currentIndex" />
      </div>
      <div class="right">
        <MindStream
          :steps="steps"
          :current-index="currentIndex"
          :persona="caseData?.title"
          model-label="Active Lifting"
          side="ours"
        />
      </div>
    </section>

    <transition name="fade">
      <div v-if="result && status === 'done'" class="verdict">
        <span class="tag">RESOLVED</span>{{ result.conclusion }}
      </div>
    </transition>
  </div>
</template>

<style scoped>
.ctl {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px 18px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 18px;
  align-items: center;
  margin-bottom: 18px;
}
label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--ink-dim);
}
select {
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  font-size: 14px;
  min-width: 180px;
}
.q {
  font-size: 15px;
  font-weight: 600;
}
.run {
  border: none;
  border-radius: 10px;
  padding: 10px 18px;
  font-weight: 600;
  font-size: 14px;
  background: var(--ours);
  color: #fff;
}
.run:disabled {
  opacity: 0.5;
}
.body {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 22px;
  align-items: start;
}
.right {
  height: 420px;
}
.verdict {
  margin-top: 18px;
  padding: 16px 18px;
  background: #e7f9ef;
  border-radius: var(--radius);
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}
.verdict .tag {
  font-family: var(--mono);
  font-size: 12px;
  background: var(--ok);
  color: #fff;
  padding: 3px 9px;
  border-radius: 6px;
  margin-right: 10px;
}
.fade-enter-active {
  transition: opacity 0.5s;
}
.fade-enter-from {
  opacity: 0;
}
@media (max-width: 1100px) {
  .body {
    grid-template-columns: 1fr;
  }
}
</style>
