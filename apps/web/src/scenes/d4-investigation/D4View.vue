<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { getScenes, getPreview, listTrajectories, type SceneMeta } from "../../api/client";
import { usePlayer, StageView, AbilityLegend, MiniFoil } from "../../engine";

const SCENE = "d4-investigation";
const scenes = ref<SceneMeta[]>([]);
const role = ref("revenue");
const SOURCE_TITLES: Record<string, Record<string, string>> = {
  revenue: {
    "src-annual": "年度报告",
    "src-research": "券商研报",
    "src-press": "新闻报道",
  },
  product: {
    "src-official": "官方参数",
    "src-review": "媒体评测",
    "src-forum": "车主论坛",
  },
};

const ours = usePlayer("ours");
const foil = usePlayer("baseline");
const {
  steps: ourSteps,
  currentIndex: ourIndex,
  currentStep: ourCurrent,
  status: ourStatus,
  result: ourResult,
  errorMsg: ourError,
} = ours;
const { steps: foilSteps, currentIndex: foilIndex, status: foilStatus, result: foilResult } = foil;

const roleOptions = computed(() => scenes.value.find((s) => s.id === SCENE)?.roles ?? []);
const prompt = computed(() => roleOptions.value.find((r) => r.key === role.value)?.prompt ?? "");
const previewImage = ref("");
const running = computed(() => ourStatus.value === "running" || foilStatus.value === "running");
const ourConclusion = computed(() => ourResult.value?.output || ourResult.value?.conclusion || "");
const terminationText = computed(() => {
  const reason = ourResult.value?.termination_reason;
  const map: Record<string, string> = {
    all_verified: "三源核查完成，主动收尾",
    cycle_finalized: "检测到重复回看，证据已足够后收尾",
    budget_finalized: "接近步数上限，基于已核查证据收尾",
    model_eos: "模型主动输出结论",
    repeat_guard: "重复动作保护触发",
    max_steps: "达到最大步数",
  };
  return reason ? map[reason] || reason : "";
});
const sourceRows = computed(() => {
  const titles = SOURCE_TITLES[role.value] ?? {};
  const ledger = ourResult.value?.diagnostics?.ledger;
  const ids = ledger?.order?.length ? ledger.order : Object.keys(titles);
  return ids.map((id) => {
    const s = ledger?.sources?.[id];
    return {
      id,
      title: s?.title || titles[id] || id,
      seen: !!s?.seen_value,
      footnote: !!s?.zoomed_footnote,
      verified: !!s?.verified,
    };
  });
});
const evidenceResolved = computed(
  () => sourceRows.value.length > 0 && sourceRows.value.every((s) => s.verified),
);

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
  if (running.value) return;
  ours.reset();
  foil.reset();
  const items = await listTrajectories();
  const pick = (side: string) =>
    items
      .filter((t) => t.scene === SCENE && t.role === role.value && t.side === side)
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
      <label>核查案例
        <select v-model="role">
          <option v-for="r in roleOptions" :key="r.key" :value="r.key">{{ r.persona }}</option>
        </select>
      </label>
      <p class="prompt">“{{ prompt }}”</p>
      <button class="ghost" :disabled="running" @click="replayLatest">回放最近</button>
      <button class="run" :disabled="running" @click="runLive">▶ 运行</button>
    </section>

    <section class="main-row">
      <div class="stage-col">
        <div class="col-hd">
          <span class="badge">多源破案</span> 主动找证据、快速推理、从脚注推出一致性解释
        </div>
        <StageView
          :steps="ourSteps"
          :current-index="ourIndex"
          :preview-image="previewImage"
        />
      </div>

      <aside class="side-col">
        <AbilityLegend :current="ourCurrent" />
        <section class="evidence" :class="{ resolved: evidenceResolved }">
          <header>
            <span class="dot" />
            <b>证据板</b>
            <em>{{ evidenceResolved ? "RESOLVED" : ourStatus === "running" ? "核查中" : "待核查" }}</em>
          </header>
          <div class="sources">
            <div v-for="s in sourceRows" :key="s.id" class="src" :class="{ ok: s.verified }">
              <strong>{{ s.title }}</strong>
              <span :class="{ on: s.seen }">数字</span>
              <span :class="{ on: s.footnote }">脚注</span>
            </div>
          </div>
          <p v-if="ourConclusion" class="final">{{ ourConclusion }}</p>
          <p v-else-if="ourError" class="final warn">{{ ourError }}</p>
          <p v-else class="hint">运行后展示主动核查结论</p>
          <footer v-if="terminationText">
            {{ terminationText }} · {{ ourResult?.stats.total_steps ?? 0 }} 步
          </footer>
        </section>
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
.ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
.evidence {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 12px;
  flex-shrink: 0;
  border: 1px solid transparent;
}
.evidence.resolved {
  border-color: rgba(42, 168, 90, 0.35);
}
.evidence header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  margin-bottom: 10px;
}
.evidence header .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ours);
}
.evidence.resolved header .dot {
  background: var(--ok);
}
.evidence header em {
  margin-left: auto;
  font-style: normal;
  font-family: var(--mono);
  font-size: 10px;
  color: var(--ink-mute);
}
.sources {
  display: grid;
  gap: 6px;
}
.src {
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: center;
  gap: 6px;
  padding: 7px 8px;
  border-radius: 8px;
  background: var(--surface-2);
  font-size: 12px;
}
.src.ok {
  background: #e7f9ef;
}
.src strong {
  font-weight: 700;
}
.src span {
  border-radius: 5px;
  padding: 1px 6px;
  color: var(--ink-mute);
  background: #ececf2;
  font-size: 10px;
}
.src span.on {
  color: var(--ok);
  background: #d9f4e5;
}
.final {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.55;
  color: var(--ink);
}
.final.warn {
  color: #b42318;
}
.hint {
  margin-top: 10px;
  font-size: 12px;
  color: var(--ink-mute);
}
.evidence footer {
  margin-top: 8px;
  font-size: 11px;
  color: var(--ink-mute);
}
@media (max-width: 1100px) {
  .main-row {
    grid-template-columns: 1fr;
  }
}
</style>
