import type { Step } from "@ap/protocol";

/** 把一步的动作翻译成"认知行为"旁白，让观众看懂模型此刻在做什么。 */
export function narrate(step: Step | null): string {
  if (!step) return "点击运行，看认知基模如何主动观察…";
  const a = step.action;
  const label = (a.label || "")
    .replace(/^(SEE|ZOOM[-_ ]?IN|ZOOM[-_ ]?OUT|CLICK|NAVIGATE|RE-?EXAMINE|OUTPUT:?|THINK|INSIGHT)\s*/i, "")
    .trim();
  switch (a.type) {
    case "see":
      return label ? `锁定「${label}」，凑近看清` : "扫一眼全局，寻找相关线索";
    case "zoom_in":
      return label ? `放大确认「${label}」的关键细节` : "放大确认关键数字，先看清再判断";
    case "zoom_out":
      return "退回更大范围，重新把握全局";
    case "scroll":
      return "移动视野，继续查看相关区域";
    case "click":
      return label ? `信息还不够，深入「${label}」继续查证` : "信息还不够，深入下一页继续查证";
    case "snapshot":
      return "回到整页全局，重新规划看哪里";
    case "navigate":
      return label ? `数字对不上，回看「${label}」追溯口径差异` : "数字对不上，主动回看相关来源追溯原因";
    case "none":
      return "这块拿不准，先停下来多想几步";
    case "eos":
      return "线索齐了，给出能同时解释各源数字的结论";
    default:
      return step.thought || "";
  }
}

/** 三大能力 key。 */
export type AbilityKey = "explore" | "sampling" | "approx";

/** 当前动作命中哪一项能力（用于三大能力实时高亮）。approx 为解说项，不实时命中。 */
export function abilityOf(step: Step | null): AbilityKey | null {
  if (!step) return null;
  switch (step.action.type) {
    case "see":
    case "zoom_in":
    case "zoom_out":
    case "scroll":
    case "click":
    case "snapshot":
    case "navigate":
      return "explore";
    case "none":
    case "eos":
      return "sampling";
    default:
      return null;
  }
}

/** 取一步动作的 element 目标 id（若有）。 */
export function targetElementId(step: Step | null): string | undefined {
  const t = step?.action.target;
  if (t && (t as { kind?: string }).kind === "element") {
    return (t as { element_id: string }).element_id;
  }
  return undefined;
}

/** D4 多源破案的能力高亮：
 * - 放大解谜脚注 / 给出结论 = 从一行小字推出全局一致性解释 → 分布逼近(approx)
 * - 停下多想 = 隐空间采样效率(sampling)
 * - 其余观察 / 回看 / 跳转 = 主动探索(explore)
 */
export function investigationAbility(
  step: Step | null,
  resolverElementId?: string,
): AbilityKey | null {
  if (!step) return null;
  const a = step.action;
  if (a.type === "eos") return "approx";
  if (a.type === "zoom_in" && resolverElementId && targetElementId(step) === resolverElementId) {
    return "approx";
  }
  if (a.type === "none") return "sampling";
  return "explore";
}
