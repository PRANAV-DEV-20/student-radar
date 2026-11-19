import { DOMAIN_PACKS, type DomainPack } from "./domainPacks";

export interface DomainPersona {
  id: string;
  label: string;
  shortLabel: string;
  badgeColor: string;
  description: string;
}

/**
 * Single source of truth for domain selection. Derived from the domain packs
 * so the dashboard, dock, radar and outreach can never drift apart.
 */
export const DOMAIN_PERSONAS: DomainPersona[] = DOMAIN_PACKS.map((pack: DomainPack) => ({
  id: pack.id,
  label: pack.label,
  shortLabel: pack.shortLabel,
  badgeColor: pack.badgeColor,
  description: pack.description,
}));

export interface DemoPreset {
  id: string;
  title: string;
  domain: string;
  type: "github" | "idea" | "pdf_text";
  snippet: string;
  rawContent: string;
}

export const DEMO_PRESETS: DemoPreset[] = [
  {
    id: "agent-eval",
    title: "Agent Eval Harness",
    domain: "tech_builder",
    type: "github",
    snippet: "Open-source eval harness comparing retrieval strategies on a fixed baseline.",
    rawContent: "https://github.com/student-radar/agent-eval-harness"
  },
  {
    id: "antitrust-auditor",
    title: "Algorithmic Antitrust",
    domain: "policy_law",
    type: "idea",
    snippet: "Difference-in-differences analysis of self-preferencing under the EU Digital Markets Act.",
    rawContent: "We built a causal-inference pipeline auditing self-preferencing search results on digital marketplaces under FTC Section 5 and the EU Digital Markets Act, with primary-source citations for every statutory claim."
  },
  {
    id: "crispr-epigenetic",
    title: "CRISPR Off-Target Study",
    domain: "design_biotech",
    type: "pdf_text",
    snippet: "Chromatin-aware off-target prediction with controls, limitations and a preprint link.",
    rawContent: "Epigenetic-Aware Off-Target Cleavage Prediction in CRISPR Therapeutics: integrating single-cell ATAC-seq chromatin states with sequence mismatch penalties. Methods, controls and limitations are reported; no clinical claims are made."
  }
];
