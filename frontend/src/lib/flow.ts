/**
 * The single promise, expressed as a guided loop:
 * Understand → Position → Publish → Connect → Track → Repeat
 *
 * Each stage maps to a real screen and to observable evidence that the stage
 * happened. The dashboard uses this to show what is done, what is next, and
 * what work/info sits behind every card.
 */

export type FlowStageId =
  | "understand"
  | "position"
  | "publish"
  | "connect"
  | "track"
  | "repeat";

export interface FlowStage {
  id: FlowStageId;
  label: string;
  tagline: string;
  route: string;
  description: string;
  /** Work shown when the stage is opened from the dashboard. */
  deliverables: string[];
}

export const FLOW_STAGES: FlowStage[] = [
  {
    id: "understand",
    label: "Understand",
    tagline: "Project DNA + honest reality check",
    route: "/dossier",
    description:
      "Normalise any input into one DNA card, score readiness and flag claims the evidence does not support.",
    deliverables: [
      "Project DNA card (problem, solution, audience, method, novelty, evidence, gaps)",
      "Readiness score with specific fixes",
      "Source-linked similar work and differences",
    ],
  },
  {
    id: "position",
    label: "Position",
    tagline: "Angles, formats and domain-safe tone",
    route: "/pr-studio",
    description:
      "Turn the DNA card into platform-specific copy using the rules of your domain pack.",
    deliverables: [
      "Content angles (problem, journey, result, collaborator call)",
      "LinkedIn / Instagram / X / Show-post format packs",
      "Pre-publish safety and claim checklist",
    ],
  },
  {
    id: "publish",
    label: "Publish",
    tagline: "Project passport + share kit",
    route: "/p",
    description:
      "Give every post a permanent, shareable project passport with summary, demo and tags.",
    deliverables: [
      "Public project passport link",
      "Cover / OG image and one-page summary",
      "Copy-ready share text",
    ],
  },
  {
    id: "connect",
    label: "Connect",
    tagline: "Personal outreach, never bulk send",
    route: "/pr-studio?tab=outreach",
    description:
      "Draft one short, specific email per recipient and send it through your own mail app.",
    deliverables: [
      "Per-recipient personalised draft",
      "Intent templates (feedback, mentorship, collaboration, feature, internship, grant, intro)",
      "Consent, daily-cap and follow-up reminders",
    ],
  },
  {
    id: "track",
    label: "Track",
    tagline: "Replies, reach and matched opportunities",
    route: "/radar",
    description:
      "See what actually happened: page views, copied posts, replies and matched opportunities.",
    deliverables: [
      "Visibility / reach totals",
      "Deadline and opportunity match feed",
      "Email reply statuses and follow-up dates",
    ],
  },
  {
    id: "repeat",
    label: "Repeat",
    tagline: "Re-analyse after every update",
    route: "/dashboard",
    description:
      "Update the project, re-run the analysis and let the next recommendation follow automatically.",
    deliverables: [
      "Refined dossier from new evidence",
      "Updated readiness score",
      "Next best action for the current stage",
    ],
  },
];

const STORAGE_KEY = "student_radar_flow_state";

type FlowState = Partial<Record<FlowStageId, { doneAt: string; note?: string }>>;

export function getFlowState(): FlowState {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") as FlowState;
  } catch {
    return {};
  }
}

export function markFlowStageDone(stage: FlowStageId, note?: string): void {
  if (typeof window === "undefined") return;
  const state = getFlowState();
  state[stage] = { doneAt: new Date().toISOString(), note };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  window.dispatchEvent(new CustomEvent("student-radar:flow", { detail: state }));
}

/** First stage that has no recorded evidence yet. */
export function getNextFlowStage(state: FlowState = getFlowState()): FlowStage {
  return FLOW_STAGES.find((stage) => !state[stage.id]) || FLOW_STAGES[FLOW_STAGES.length - 1];
}

export function flowProgress(state: FlowState = getFlowState()): number {
  return Math.round((FLOW_STAGES.filter((stage) => state[stage.id]).length / FLOW_STAGES.length) * 100);
}
