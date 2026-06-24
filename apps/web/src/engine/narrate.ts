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
      return label ? `主动回看「${label}」追溯原因` : "主动回看，追溯线索";
    case "none":
      return "这块拿不准，先停下来多想几步";
    case "eos":
      return "信息已经足够，主动收尾给出结论";
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
