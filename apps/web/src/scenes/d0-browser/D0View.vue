<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { TrajectoryPlayer } from "../../engine";
import {
  getConfig,
  getPreview,
  getScenes,
  listTrajectories,
  type EngineConfig,
  type SceneMeta,
} from "../../api/client";

const SCENE = "d0-news-portal";
const config = ref<EngineConfig | null>(null);
const scenes = ref<SceneMeta[]>([]);
const role = ref("trader");
const autoplay = ref(false);

const ourRef = ref<InstanceType<typeof TrajectoryPlayer> | null>(null);
const baseRef = ref<InstanceType<typeof TrajectoryPlayer> | null>(null);

const roleOptions = computed(() => scenes.value[0]?.roles ?? []);
const prompt = computed(() => roleOptions.value.find((r) => r.key === role.value)?.prompt ?? "");

const previewImage = ref("");
let doneCount = 0;

async function loadPreview() {
  try {
    previewImage.value = (await getPreview(SCENE, role.value)).image;
  } catch {
    /* ignore */
  }
}

onMounted(async () => {
  try {
    config.value = await getConfig();
    scenes.value = await getScenes();
  } catch {
    /* 引擎未连接，由 App header 提示 */
  }
  await loadPreview();
});

// 切换角色：清空两侧运行结果并刷新首图（不再维持旧案例图像）
watch(role, async () => {
  ourRef.value?.reset();
  baseRef.value?.reset();
  doneCount = 0;
  await loadPreview();
});

function runLive() {
  doneCount = 0;
  ourRef.value?.reset();
  baseRef.value?.reset();
  ourRef.value?.startLive();
  baseRef.value?.startLive();
}

async function replayLatest() {
  doneCount = 0;
  const items = await listTrajectories();
  const pick = (side: string) =>
    items
      .filter((t) => t.role === role.value && t.side === side)
      .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))[0];
  const ours = pick("ours");
  const base = pick("baseline");
  if (ours) ourRef.value?.startReplay(ours.id);
  if (base) baseRef.value?.startReplay(base.id);
}

function onDone() {
  doneCount++;
  if (doneCount >= 2 && autoplay.value) window.setTimeout(runLive, 3500);
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
      <div class="actions">
        <label class="chk"><input type="checkbox" v-model="autoplay" /> 自动循环</label>
        <button class="ghost" @click="replayLatest">回放最近</button>
        <button class="run" @click="runLive">▶ 实时运行对比</button>
      </div>
    </section>

    <section class="compare">
      <TrajectoryPlayer
        ref="ourRef"
        side="ours"
        :scene="SCENE"
        :role="role"
        :model-label="config?.models.ours.label"
        :preview-image="previewImage"
        @done="onDone"
      />
      <TrajectoryPlayer
        ref="baseRef"
        side="baseline"
        :scene="SCENE"
        :role="role"
        :model-label="config?.models.baseline.label"
        :preview-image="previewImage"
        @done="onDone"
      />
    </section>

    <footer class="ft">
      对比维度：观察步数 / 放大次数 / 跳过区域 / 连续思考 / 自主终止
    </footer>
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
.prompt {
  font-size: 14px;
  font-style: italic;
}
.actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.chk {
  flex-direction: row;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--ink);
}
button {
  border: none;
  border-radius: 10px;
  padding: 10px 18px;
  font-weight: 600;
  font-size: 14px;
}
.run {
  background: var(--ours);
  color: #fff;
}
.ghost {
  background: var(--surface-2);
  border: 1px solid var(--line);
  color: var(--ink);
}
.compare {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 22px;
}
.ft {
  margin-top: 22px;
  text-align: center;
  font-size: 12px;
  color: var(--ink-mute);
  font-family: var(--mono);
}
@media (max-width: 1100px) {
  .compare {
    grid-template-columns: 1fr;
  }
}
</style>
