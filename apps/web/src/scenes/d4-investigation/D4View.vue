<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { getScenes, getPreview, listTrajectories, type SceneMeta } from "../../api/client";
import { usePlayer, StageView, MiniFoil } from "../../engine";

const SCENE = "d4-investigation";
const scenes = ref<SceneMeta[]>([]);
const role = ref("revenue");
const SOURCE_TITLES: Record<string, Record<string, string>> = {
  revenue: {
    "src-annual-pdf": "年报 PDF",
    "src-annual-notes": "财报附注",
    "src-research": "券商研报",
    "src-press": "新闻报道",
    "src-database": "数据库摘要",
  },
  product: {
    "src-official": "官方参数",
    "src-review": "媒体评测",
    "src-forum": "车主论坛",
  },
};
const CHECK_LABELS: Record<string, { text: string; field: string }> = {
  关键数字: { text: "数字", field: "seen_value" },
  口径: { text: "口径", field: "zoomed_footnote" },
  "版本/单位": { text: "版本", field: "checked_version_unit" },
  可信度: { text: "可信", field: "checked_credibility" },
};

const ours = usePlayer("ours");
const foil = usePlayer("baseline");
const {
  steps: ourSteps,
  currentIndex: ourIndex,
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
    const required = s?.required_labels?.length ? s.required_labels : ["关键数字", "口径"];
    const checks = required.map((label) => {
      const meta = CHECK_LABELS[label] ?? { text: label, field: "" };
      const value = meta.field ? Boolean((s as unknown as Record<string, unknown> | undefined)?.[meta.field]) : false;
      return { label: meta.text, on: value };
    });
    return {
      id,
      title: s?.title || titles[id] || id,
      seen: !!s?.seen_value,
      footnote: !!s?.zoomed_footnote,
      checks,
      verified: !!s?.verified,
    };
  });
});
const evidenceResolved = computed(
  () => sourceRows.value.length > 0 && sourceRows.value.every((s) => s.verified),
);
const revenueLedger = computed(() => ourResult.value?.diagnostics?.ledger?.sources ?? {});
const conflictItems = computed(() => {
  if (role.value === "product") {
    const s = revenueLedger.value;
    return [
      { value: "605 km", label: "官方 CLTC", state: s["src-official"]?.verified ? "实验室工况" : "冲突" },
      { value: "432 km", label: "媒体实测", state: s["src-review"]?.verified ? "夏季高速" : "冲突" },
      { value: "380 km", label: "车主论坛", state: s["src-forum"]?.verified ? "冬季满载" : "冲突" },
    ];
  }
  const s = revenueLedger.value;
  return [
    { value: "10.2 亿", label: "年报首页", state: s["src-annual-pdf"]?.verified ? "母公司口径" : "冲突" },
    { value: "15.0 亿", label: "附注/研报", state: s["src-annual-notes"]?.verified ? "审计合并口径" : "待核查" },
    { value: "12.6 亿", label: "新闻报道", state: s["src-press"]?.checked_credibility ? "分部误读" : "干扰" },
    { value: "14.7 亿", label: "数据库", state: s["src-database"]?.checked_version_unit ? "旧快报排除" : "版本冲突" },
  ];
});
const reasoningFrames = computed(() => {
  const hasZoom = ourSteps.value.some((step) => step.action.type === "zoom_in");
  const hasCredibility = Object.values(revenueLedger.value).some((s) => s.checked_credibility);
  return [
    { label: "发现数字冲突", on: ourSteps.value.length >= 3 },
    { label: "回看/放大角落小字", on: hasZoom },
    { label: role.value === "revenue" ? "排除误读与旧版本" : "解释测试条件差异", on: hasCredibility || evidenceResolved.value },
    { label: "RESOLVED", on: evidenceResolved.value },
  ];
});
const baselineGaps = computed(() => {
  if (role.value === "product") {
    return ["未逐源放大测试条件", "未区分 CLTC / 夏季高速 / 冬季满载", "无证据账本"];
  }
  return ["未放大财报附注", "未核对数据库版本/单位", "未排除新闻 12.6 亿误读", "无证据账本"];
});

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
        <section class="evidence" :class="{ resolved: evidenceResolved }">
          <header>
            <span class="dot" />
            <b>证据板</b>
            <em>{{ evidenceResolved ? "RESOLVED" : ourStatus === "running" ? "核查中" : "待核查" }}</em>
          </header>
          <div class="sources">
            <div v-for="s in sourceRows" :key="s.id" class="src" :class="{ ok: s.verified }">
              <strong>{{ s.title }}</strong>
              <span v-for="c in s.checks" :key="c.label" :class="{ on: c.on }">{{ c.label }}</span>
            </div>
          </div>
          <div class="conflicts" :class="{ resolved: evidenceResolved }">
            <div v-for="item in conflictItems" :key="item.value" class="conflict">
              <b>{{ item.value }}</b>
              <span>{{ item.label }}</span>
              <em>{{ item.state }}</em>
            </div>
          </div>
          <div class="reasoning">
            <span v-for="frame in reasoningFrames" :key="frame.label" :class="{ on: frame.on }">
              {{ frame.label }}
            </span>
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
        <section class="baseline-gap">
          <header>Baseline 未核查项</header>
          <p v-for="gap in baselineGaps" :key="gap">{{ gap }}</p>
        </section>
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
  display: flex;
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
  flex: 1;
  min-width: 0;
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
.conflicts {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}
.conflict {
  border: 1px solid rgba(255, 122, 61, 0.22);
  border-radius: 8px;
  padding: 7px;
  background: #fff7ed;
  display: grid;
  gap: 1px;
}
.conflicts.resolved .conflict {
  border-color: rgba(42, 168, 90, 0.22);
  background: #f0fbf4;
}
.conflict b {
  font-family: var(--mono);
  font-size: 13px;
}
.conflict span {
  font-size: 10px;
  color: var(--ink-mute);
}
.conflict em {
  font-style: normal;
  font-size: 11px;
  color: #b45309;
}
.conflicts.resolved .conflict em {
  color: var(--ok);
}
.reasoning {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.reasoning span {
  border-radius: 999px;
  padding: 2px 7px;
  font-size: 10px;
  color: var(--ink-mute);
  background: #ececf2;
}
.reasoning span.on {
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
.baseline-gap {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 12px;
  border: 1px dashed rgba(255, 122, 61, 0.45);
}
.baseline-gap header {
  font-size: 12px;
  font-weight: 800;
  margin-bottom: 8px;
  color: #b45309;
}
.baseline-gap p {
  font-size: 11px;
  color: var(--ink-dim);
  margin: 5px 0;
}
.baseline-gap p::before {
  content: "×";
  color: #b42318;
  font-family: var(--mono);
  font-weight: 800;
  margin-right: 6px;
}
@media (max-width: 1100px) {
  .main-row {
    grid-template-columns: 1fr;
  }
}
</style>
