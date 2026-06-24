<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { getScenes, getPreview, listTrajectories, type SceneMeta } from "../../api/client";
import { usePlayer, StageView, MindStream, AbilityLegend, MiniFoil } from "../../engine";

const SCENE = "d0-news-portal";
const scenes = ref<SceneMeta[]>([]);
const role = ref("trader");

const ours = usePlayer("ours");
const foil = usePlayer("baseline");
const { steps: ourSteps, currentIndex: ourIndex, currentStep: ourCurrent, status: ourStatus } = ours;
const { steps: foilSteps, currentIndex: foilIndex, status: foilStatus, result: foilResult } = foil;

const roleOptions = computed(() => scenes.value[0]?.roles ?? []);
const prompt = computed(() => roleOptions.value.find((r) => r.key === role.value)?.prompt ?? "");
const previewImage = ref("");
const running = computed(() => ourStatus.value === "running" || foilStatus.value === "running");

async function loadPreview() {
  try {
    previewImage.value = (await getPreview(SCENE, role.value)).image;
  } catch {
    /* 引擎未连接，由 App header 提示 */
  }
}

onMounted(async () => {
  try {
    scenes.value = await getScenes();
  } catch {
    /* 引擎未连接 */
  }
  await loadPreview();
});

watch(role, async () => {
  ours.reset();
  foil.reset();
  await loadPreview();
});

function runLive() {
  ours.reset();
  foil.reset();
  ours.startLive(SCENE, role.value);
  foil.startLive(SCENE, role.value);
}

// 回放最近一条已落盘轨迹（现场离线兜底 / 无 Key 调试）
async function replayLatest() {
  ours.reset();
  foil.reset();
  const items = await listTrajectories();
  const pick = (side: string) =>
    items
      .filter((t) => t.role === role.value && t.side === side)
      .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))[0];
  const o = pick("ours");
  const b = pick("baseline");
  if (o) ours.startReplay(o.id);
  if (b) foil.startReplay(b.id);
}
</script>

<template>
  <div class="d0">
    <section class="ctl">
      <label>角色意图
        <select v-model="role">
          <option v-for="r in roleOptions" :key="r.key" :value="r.key">{{ r.persona }}</option>
        </select>
      </label>
      <p class="prompt">“{{ prompt }}”</p>
      <button class="ghost" @click="replayLatest">回放最近</button>
      <button class="run" :disabled="running" @click="runLive">▶ 运行</button>
    </section>

    <section class="main-row">
      <div class="stage-col">
        <div class="col-hd">
          <span class="badge">认知基模</span> 认知基模在做什么
        </div>
        <StageView
          :steps="ourSteps"
          :current-index="ourIndex"
          :preview-image="previewImage"
        />
      </div>

      <aside class="side-col">
        <MindStream :steps="ourSteps" :current-index="ourIndex" />
        <AbilityLegend :current="ourCurrent" />
        <MiniFoil
          :steps="foilSteps"
          :current-index="foilIndex"
          :status="foilStatus"
          :result="foilResult"
          :preview-image="previewImage"
        />
      </aside>
    </section>
  </div>
</template>

<style scoped>
.d0 {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ctl {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 18px;
  flex-shrink: 0;
}
.ctl label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: var(--ink-dim);
}
.ctl select {
  padding: 7px 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  font-size: 14px;
  min-width: 170px;
}
.prompt {
  flex: 1;
  font-size: 15px;
  font-style: italic;
  color: var(--ink);
}
.run {
  border: none;
  border-radius: 10px;
  padding: 10px 22px;
  font-weight: 700;
  font-size: 15px;
  background: var(--ours);
  color: #fff;
}
.run:disabled {
  opacity: 0.5;
}
.ghost {
  border: 1px solid var(--line);
  background: var(--surface-2);
  color: var(--ink);
  border-radius: 10px;
  padding: 10px 16px;
  font-weight: 600;
  font-size: 14px;
}
.main-row {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 16px;
}
.stage-col {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}
.col-hd {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}
.col-hd .badge {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  background: var(--ours);
  padding: 2px 9px;
  border-radius: 6px;
}
.stage-col :deep(.stage) {
  flex: 1;
  min-height: 0;
}
.side-col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
@media (max-width: 1100px) {
  .main-row {
    grid-template-columns: 1fr;
  }
}
</style>
