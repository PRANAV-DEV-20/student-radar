/**
 * Project DNA — the single normalised structure every downstream stage uses.
 *
 * This is intentionally a client-side, deterministic derivation: it works with
 * a real API dossier and with the offline fallback, and it never invents a
 * competitor, metric or opportunity. If evidence is absent, the card says so.
 */

import { getDomainPack, type DomainPack } from "./domainPacks";

export interface DnaField {
  label: string;
  value: string;
  basis: "input" | "derived" | "missing";
}

export interface ReadinessAxis {
  key: "clarity" | "novelty" | "proof" | "impact";
  label: string;
  score: number; // 0-100
  fix: string | null;
}

export interface ClaimFlag {
  text: string;
  severity: "high" | "medium";
  reason: string;
  fix: string;
}

export interface EvidenceSource {
  title: string;
  url: string;
  platform: string;
  kind: "similar-work" | "upgrade" | "own-link" | "input";
}

export interface ProjectDNA {
  fields: DnaField[];
  readiness: { total: number; axes: ReadinessAxis[] };
  claims: ClaimFlag[];
  evidence: EvidenceSource[];
  gaps: string[];
  stageAdvice: string;
  stage: string;
  domainPack: DomainPack;
  confidence: "high" | "medium" | "low";
  summary: string;
}

function text(value: unknown): string {
  if (typeof value === "string") return value.trim();
  if (typeof value === "number") return String(value);
  return "";
}

function list(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((item) =>
        typeof item === "string"
          ? item
          : text((item as any)?.label || (item as any)?.value || (item as any)?.role || (item as any)?.name),
      )
      .filter(Boolean);
  }
  if (value && typeof value === "object") return Object.values(value as object).map(text).filter(Boolean);
  return [];
}

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

export function buildProjectDNA(dossier: any): ProjectDNA {
  const pack = getDomainPack(dossier?.domain_persona || dossier?.domain);
  const stage = text(dossier?.stage) || "Prototype";

  const problem = text(dossier?.problem_statement);
  const solution = text(dossier?.solution_breakdown?.architecture) || text(dossier?.solution_architecture);
  const algorithms = list(dossier?.solution_breakdown?.core_algorithms);
  const stack = list(dossier?.tech_stack || dossier?.technologies);
  const metrics: Array<{ label: string; value: string }> = Array.isArray(dossier?.key_metrics)
    ? dossier.key_metrics.map((m: any) => ({ label: text(m?.label), value: text(m?.value) })).filter((m: any) => m.label)
    : [];
  const gap = text(dossier?.whitespace_analysis?.market_gap) || text(dossier?.market_gap);
  const topVoices = list(dossier?.whitespace_analysis?.top_voices);
  const missingRoles = list(dossier?.missing_roles);
  const externalLinks: Record<string, unknown> = dossier?.external_links || {};
  const benchmark = dossier?.benchmark_analysis || {};

  const audience =
    text(dossier?.target_audience) ||
    text(dossier?.audience) ||
    "Not stated — add one sentence on who has this problem";

  const novelty =
    text(dossier?.novelty) ||
    gap ||
    "Not stated — add one sentence on what is genuinely new versus existing work";

  const evidenceParts = pack.proof.filter((item) =>
    JSON.stringify(dossier || {}).toLowerCase().includes(item.toLowerCase().split(" ")[0]),
  );

  const fields: DnaField[] = [
    { label: "Problem", value: problem || "Missing — describe the concrete problem", basis: problem ? "input" : "missing" },
    { label: "Solution", value: solution || algorithms.join(", ") || "Missing — describe how it works", basis: solution || algorithms.length ? "input" : "missing" },
    { label: "Audience", value: audience, basis: text(dossier?.target_audience || dossier?.audience) ? "input" : "missing" },
    { label: "Domain", value: pack.label, basis: "derived" },
    { label: "Stage", value: stage, basis: dossier?.stage ? "input" : "derived" },
    { label: "Tech / method", value: [...stack, ...algorithms].slice(0, 8).join(", ") || "Not stated", basis: stack.length || algorithms.length ? "input" : "missing" },
    { label: "Novelty", value: novelty, basis: gap || dossier?.novelty ? "input" : "missing" },
    {
      label: "Evidence",
      value: metrics.length ? metrics.map((m) => `${m.label}: ${m.value}`).join(" · ") : "No measurable evidence supplied",
      basis: metrics.length ? "input" : "missing",
    },
    {
      label: "Gaps",
      value: missingRoles.length ? missingRoles.join(", ") : "No gaps captured yet",
      basis: missingRoles.length ? "input" : "missing",
    },
  ];

  // ---- Readiness scoring (specific, explainable fixes) ----
  const clarity = clampScore(
    (problem ? 45 : 0) + (solution ? 25 : 0) + (audience.includes("Not stated") ? 0 : 20) + (stack.length ? 10 : 0),
  );
  const noveltyScore = clampScore(
    (gap ? 55 : 10) + (topVoices.length ? 20 : 0) + (benchmark?.similar_projects?.length ? 25 : 0),
  );
  const proofScore = clampScore(
    (metrics.length ? 35 : 0) +
      (Object.keys(externalLinks).length ? 25 : 0) +
      (benchmark?.similar_projects?.length ? 15 : 0) +
      (dossier?.verified_status ? 25 : 0),
  );
  const impactScore = clampScore(
    (missingRoles.length ? 25 : 0) + (gap ? 35 : 0) + (topVoices.length ? 20 : 0) + (metrics.length ? 20 : 0),
  );

  const axes: ReadinessAxis[] = [
    {
      key: "clarity",
      label: "Clarity",
      score: clarity,
      fix: problem ? (audience.includes("Not stated") ? "Name one specific audience." : null) : "Write a one-sentence problem statement.",
    },
    {
      key: "novelty",
      label: "Novelty",
      score: noveltyScore,
      fix: benchmark?.similar_projects?.length
        ? null
        : "Run the reality check to retrieve 3–5 real comparable projects and state how yours differs.",
    },
    {
      key: "proof",
      label: "Proof",
      score: proofScore,
      fix: !metrics.length
        ? pack.key === "biotech"
          ? "Add replicated data with controls (or a clearly labelled expected result)."
          : pack.key === "law_policy"
            ? "Add primary-source citations supporting the analysis."
            : "Add one baseline comparison or a runnable demo link."
        : !Object.keys(externalLinks).length
          ? "Attach a demo, repo, preprint or brief link so claims can be verified."
          : null,
    },
    {
      key: "impact",
      label: pack.key === "ai_tech" ? "Market / impact relevance" : "Impact relevance",
      score: impactScore,
      fix: missingRoles.length ? null : "State who benefits and interview 5 of them.",
    },
  ];

  const total = clampScore(axes.reduce((sum, axis) => sum + axis.score, 0) / axes.length);

  // ---- Claim verification: never assert, only flag ----
  const claimText = [problem, solution, ...metrics.map((m) => `${m.label} ${m.value}`), gap]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  const hasVerifiedLink = Object.keys(externalLinks).length > 0 || Boolean(dossier?.verified_status);
  const claims: ClaimFlag[] = [];

  for (const needle of pack.claimChecks) {
    if (!claimText.includes(needle)) continue;
    claims.push({
      text: needle,
      severity: hasVerifiedLink ? "medium" : "high",
      reason: hasVerifiedLink
        ? "This term appears in your copy but no verified source is attached to the specific number."
        : "This is a high-scrutiny claim with no attached evidence link.",
      fix: pack.key === "biotech"
        ? "Remove the claim or attach a supervisor-reviewed source; do not publish health-benefit language."
        : pack.key === "law_policy"
          ? "Attach a primary-source citation and keep the 'analysis, not legal advice' framing."
          : "Add a baseline, run details, and a link to the repo or demo before publishing.",
    });
  }

  // Metrics generated without a source are always flagged as needing evidence.
  if (metrics.length && !hasVerifiedLink) {
    claims.push({
      text: metrics.slice(0, 2).map((m) => m.label).join(" & "),
      severity: "high",
      reason: "Numbers are present in the dossier but no demo, repo, preprint or brief is attached.",
      fix: "Verify each number against a run or source, or replace it with a qualitative statement.",
    });
  }

  // ---- Evidence: only real, retrievable records ----
  const evidence: EvidenceSource[] = [];
  for (const project of benchmark?.similar_projects || []) {
    if (text(project?.url).startsWith("http")) {
      evidence.push({
        title: text(project?.name) || "Similar project",
        url: text(project.url),
        platform: text(project?.source_platform) || "source",
        kind: "similar-work",
      });
    }
  }
  for (const upgrade of benchmark?.advanced_upgrades || []) {
    if (text(upgrade?.reference_url).startsWith("http")) {
      evidence.push({
        title: text(upgrade?.upgrade_title) || "Related work",
        url: text(upgrade.reference_url),
        platform: text(upgrade?.inspired_by) || "reference",
        kind: "upgrade",
      });
    }
  }
  for (const [key, value] of Object.entries(externalLinks)) {
    const url = text(value);
    if (url.startsWith("http")) {
      evidence.push({ title: `${key} (your artifact)`, url, platform: key, kind: "own-link" });
    }
  }

  const confidence: ProjectDNA["confidence"] =
    evidence.length >= 3 && total >= 60 ? "high" : evidence.length >= 1 ? "medium" : "low";

  const summary =
    confidence === "low"
      ? "Grounded in your input only. No external records were retrieved, so treat comparisons as hypotheses."
      : `Grounded in your input plus ${evidence.length} source-linked record${evidence.length === 1 ? "" : "s"}. Claims without a source are flagged above.`;

  return {
    fields,
    readiness: { total, axes },
    claims,
    evidence,
    gaps: missingRoles,
    stageAdvice: pack.stageAdvice[stage.toLowerCase()] || pack.stageAdvice.idea,
    stage,
    domainPack: pack,
    confidence,
    summary,
  };
}

/** Human-readable stage-aware next step, used by the dashboard. */
export function stageAwareAdvice(dossier: any): string {
  return buildProjectDNA(dossier).stageAdvice;
}
