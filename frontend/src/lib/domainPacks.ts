/**
 * Domain packs — the "one core engine, three domain packs" model.
 *
 * The backend keeps its original persona keys for API/data compatibility. The
 * UI presents exactly three packs: AI & Tech, Biotech & Life Sciences, and
 * Law & Policy. Every downstream surface (analysis, safety, content, radar,
 * outreach) reads from a pack so rules live in one place instead of being
 * scattered across prompts and components.
 */

export type DomainPackKey = "ai_tech" | "biotech" | "law_policy";

export interface DomainPack {
  /** Backend-compatible persona id (do not change without a migration). */
  id: string;
  key: DomainPackKey;
  label: string;
  shortLabel: string;
  badgeColor: string;
  description: string;

  /** What counts as credible evidence in this domain. */
  proof: string[];
  /** Where visibility actually happens. */
  channels: string[];
  /** Formats that land in this domain. */
  formats: string[];
  /** The single biggest credibility risk. */
  keyRisk: string;
  /** Non-negotiable guardrails shown before public posting. */
  safetyRules: string[];
  /** Opportunity types surfaced first by the radar. */
  opportunityTypes: string[];
  /** People worth contacting for feedback / collaboration. */
  outreachTargets: string[];
  /** Preferred retrieval sources (official APIs / open data first). */
  radarSources: string[];
  /** Claims the engine must verify before they can be published. */
  claimChecks: string[];
  /** Advice keyed by project stage. */
  stageAdvice: Record<string, string>;
  /** Default outreach tone for cold, high-trust contacts. */
  defaultTone: string;
}

export const DOMAIN_PACKS: DomainPack[] = [
  {
    id: "tech_builder",
    key: "ai_tech",
    label: "AI, Tech & Engineering",
    shortLabel: "AI & Tech",
    badgeColor: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
    description:
      "Models, agents, distributed systems, robotics, dev tools and open-source infrastructure.",
    proof: ["Live demo", "Public repo", "Benchmark vs. baseline", "Users or issues"],
    channels: ["GitHub", "X", "LinkedIn", "Hacker News", "Product Hunt"],
    formats: ["Demo video", "Build thread", "Show HN", "LinkedIn post"],
    keyRisk: "Overclaiming performance or accuracy without a reproducible baseline.",
    safetyRules: [
      "Flag any speed / accuracy / benchmark claim that has no baseline, dataset or run details.",
      "Check licence and dataset-usage terms before publishing code or model weights.",
      "Keep a public demo or repo link so reviewers can verify the claim themselves.",
    ],
    opportunityTypes: ["Hackathons", "Open-source programs", "Accelerators", "Grants"],
    outreachTargets: ["Maintainers", "Founders", "Researchers", "Developer-relations leads"],
    radarSources: ["GitHub API", "arXiv", "OpenAlex", "Hacker News API", "Product Hunt API"],
    claimChecks: ["benchmark", "accuracy", "latency", "scalability", "cost"],
    stageAdvice: {
      idea: "Validate the problem with 5 interviews and one measurable baseline before building.",
      prototype: "Ship a runnable demo and a README with a before/after comparison.",
      paper: "Publish a plain-language summary with the figure and the limitation stated up front.",
      shipped: "Publish the metric that changed, the method, and an open reproduction path.",
    },
    defaultTone: "founder",
  },
  {
    id: "design_biotech",
    key: "biotech",
    label: "Biotech & Life Sciences",
    shortLabel: "Biotech",
    badgeColor: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
    description:
      "Computational biology, genetics, therapeutics, diagnostics and accessible lab hardware.",
    proof: ["Replicated data", "Controls & methods", "Preprint", "Peer review"],
    channels: ["LinkedIn", "bioRxiv / medRxiv", "Conferences", "Lab & university channels"],
    formats: ["Plain-language explainer", "Figure-led carousel", "Poster summary", "Lab-blog note"],
    keyRisk: "Premature disclosure can destroy patentability; health claims and dual-use methods carry real harm.",
    safetyRules: [
      "Before ANY public draft: confirm the work is not unpublished supervisor/institute data and that patent timing has been considered.",
      "Never generate health-benefit, diagnostic or therapeutic claims.",
      "Flag dual-use or biosecurity-sensitive methods and refuse to publicise the method itself.",
      "Use 'analysis / research note, not medical advice' framing on public posts.",
    ],
    opportunityTypes: ["Grants", "Fellowships", "iGEM-style competitions", "Incubators", "Calls for papers"],
    outreachTargets: ["Principal investigators", "Lab heads", "Incubator managers", "Program officers"],
    radarSources: ["PubMed / Europe PMC", "bioRxiv / medRxiv", "OpenAlex", "ClinicalTrials.gov", "Grant databases"],
    claimChecks: ["efficacy", "cure", "clinical", "patient", "safe", "diagnos", "therapeutic"],
    stageAdvice: {
      idea: "Write the hypothesis and the control experiment first; check disclosure and patent timing.",
      prototype: "Prepare a figure-led explainer with methods and limitations — no benefit claims.",
      paper: "Post a plain-language summary that links the preprint and states what is NOT yet shown.",
      shipped: "Seek a supervisor-reviewed channel (lab page, conference, preprint) before broad social posting.",
    },
    defaultTone: "academic",
  },
  {
    id: "policy_law",
    key: "law_policy",
    label: "Law, Governance & Policy",
    shortLabel: "Law & Policy",
    badgeColor: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    description:
      "Regulation, competition, public policy, civic tech, legal research and governance analysis.",
    proof: ["Citation quality", "Primary sources", "Real-world applicability", "Peer review"],
    channels: ["LinkedIn", "SSRN", "Substack / blogs", "Policy forums", "Op-eds"],
    formats: ["Short analysis", "Policy brief", "Op-ed pitch", "Thread with sources"],
    keyRisk: "Reading as legal advice, using confidential matter, or asserting law without a citation.",
    safetyRules: [
      "Add 'analysis, not legal advice' framing to every public draft by default.",
      "Never include client, internship or confidential matter details without explicit written consent.",
      "Require a citation for every legal or statutory claim; link the primary text where possible.",
      "Distinguish hypotheticals from actual cases explicitly.",
    ],
    opportunityTypes: ["Fellowships", "Moot courts", "Writing competitions", "Think-tank internships", "Calls for papers"],
    outreachTargets: ["Professors", "Think-tank researchers", "Journal editors", "Policy programme leads"],
    radarSources: ["SSRN", "Court / legislation portals", "Government consultations", "Think-tank publications", "Journal CFPs"],
    claimChecks: ["illegal", "unconstitutional", "court held", "statute", "section", "mandate", "liability"],
    stageAdvice: {
      idea: "Anchor the question in a primary source and state the jurisdiction and date.",
      prototype: "Turn the analysis into a one-page brief with a clear, sourced recommendation.",
      paper: "Write an op-ed pitch that leads with the finding and links the full paper.",
      shipped: "Pitch the brief to a policy forum or newsletter with the 'not legal advice' note intact.",
    },
    defaultTone: "academic",
  },
];

/** Backward-compatible alias used by the rest of the UI. */
export const DOMAIN_PACK_IDS = DOMAIN_PACKS.map((pack) => pack.id);

export function getDomainPack(idOrKey?: string | null): DomainPack {
  return (
    DOMAIN_PACKS.find((pack) => pack.id === idOrKey || pack.key === idOrKey) ||
    DOMAIN_PACKS[0]
  );
}

export function isPackId(value: string): boolean {
  return DOMAIN_PACKS.some((pack) => pack.id === value);
}
