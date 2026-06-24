<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { Step } from "@ap/protocol";
import { getCase, getPreview, listTrajectories, type CaseSpec } from "../../api/client";
import {
  usePlayer,
  StageView,
  MindStream,
  AbilityLegend,
  MiniFoil,
  investigationAbility,
  targetElementId,
} from "../../engine";

const SCENE = "d4-revenue-probe";
const ROLE = "investigator";

const caseSpec = ref<CaseSpec | null>(null);
const previewImage = ref("");

const ours = usePlayer("ours");
const foil = usePlayer("baseline");
const {
  steps: ourSteps,
  currentIndex: ourIndex,
  currentStep: ourCurrent,
  status: ourStatus,
  result: ourResult,
} = ours;
const {
  steps: foilSteps,
  currentIndex: foilIndex,
  status: foilStatus,
  result: foilResult,
} = foil;

const running = computed(() => ourStatus.value === "running" || foilStatus.value === "running");
const resolverId = computed(() => caseSpec.value?.resolver.element_id);
const abilityActive = computed(() => investigationAbility(ourCurrent.value, resolverId.value));
const conclusion = computed(() => ourResult.value?.output || ourResult.value?.conclusion || "");
const question = computed(
  () => caseSpec.value?.question || "云图智能 2025 全年真实营业收入到底是多少？",
);

onMounted(async () => {
  try {
    const c = await getCase(SCENE);
    caseSpec.value = c && Array.isArray((c as { sources?: unknown }).sources) ? c : null;
  } catch {
    /* 引擎未连接 */
  }
  try {
    previewImage.value = (await getPreview(SCENE, ROLE)).image;
  } catch {
    /* 引擎未连接 */
  }
});

function runLive() {
  ours.reset();
  foil.reset();
  ours.startLive(SCENE, ROLE);
  foil.startLive(SCENE, ROLE);
}

// 导演式变速回放：铺垫快放、回看/放大脚注/结论高潮慢放
function pace(step: Step): number {
  const t = step.action.type;
  if (t === "zoom_in" && resolverId.value && targetElementId(step) === resolverId.value) return 3000;
  if (t === "eos") return 2600;
  if (t === "navigate" || t === "click") return 2200;
  if (t === "none") return 1800;
  if (t === "zoom_in") return 1500;
  return 1050;
}

async function replayLatest() {
  ours.reset();
  foil.reset();
  const items = await listTrajectories();
  const pick = (side: string) =>
    items
      .filter((t) => t.scene === SCENE && t.side === side)
      .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))[0];
  const o = pick("ours");
  const b = pick("baseline");
  if (o) ours.startReplay(o.id, pace);
  if (b) foil.startReplay(b.id, 1400);
}
</script>

<template>
  <div class="d4">
    <section class="ctl">
      <div class="task">
        <span class="task-label">核查任务</span>
        <p class="q">“{{ question }}”</p>
      </div>
      <button class="ghost" @click="replayLatest">回放最近</button>
      <button class="run" :disabled="running" @click="runLive">▶ 运行</button>
    </section>

    <section class="main-row">
      <div class="stage-col">
        <div class="col-hd">
          <span class="badge">认知基模</span> 跨异构信息源主动核查
        </div>
        <StageView :steps="ourSteps" :current-index="ourIndex" :preview-image="previewImage" />
        <div class="conclusion" :class="{ show: ourStatus === 'done' && !!conclusion }">
          <span class="cc-badge">结论</span>
          <span class="cc-txt">{{ conclusion || "运行后，给出能同时解释三个来源数字的一致性结论" }}</span>
        </div>
      </div>

      <aside class="side-col">
        <MindStream :steps="ourSteps" :current-index="ourIndex" />
        <AbilityLegend :current="ourCurrent" :force-active="abilityActive" />
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
.d4 {
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
  gap: 16px;
  flex-shrink: 0;
}
.task {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.task-label {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  background: var(--ours);
  padding: 3px 9px;
  border-radius: 6px;
  flex-shrink: 0;
}
.q {
  font-size: 15px;
  font-style: italic;
  font-weight: 600;
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
.conclusion {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 16px;
  border-radius: var(--radius);
  background: var(--surface-2);
  border: 1px dashed var(--line);
  color: var(--ink-mute);
  transition: all 0.4s ease;
}
.conclusion.show {
  background: linear-gradient(90deg, #0a2a6b, var(--ours));
  border: none;
  color: #fff;
}
.cc-badge {
  font-size: 12px;
  font-weight: 800;
  padding: 4px 11px;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.2);
  color: inherit;
  flex-shrink: 0;
}
.conclusion:not(.show) .cc-badge {
  background: #e9e9ee;
  color: var(--ink-dim);
}
.cc-txt {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
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
