/**
 * Outreach composer — one short, specific email per recipient.
 *
 * No bulk send, no invented claims, no sending from our domain. The output is
 * a draft the student copies into their own Gmail/Outlook, with a hard daily
 * cap and explicit consent recorded in the UI.
 */

import { getDomainPack } from "./domainPacks";

export type OutreachIntent =
  | "feedback"
  | "mentorship"
  | "collaboration"
  | "feature"
  | "internship"
  | "grant"
  | "intro";

export interface OutreachRecipient {
  name: string;
  role: string;
  organization: string;
  url?: string;
  context?: string;
}

export interface OutreachDraft {
  subject: string;
  body: string;
  ask: string;
  followUps: Array<{ day: number; subject: string; body: string }>;
  warnings: string[];
}

export const OUTREACH_INTENTS: Array<{ id: OutreachIntent; label: string; ask: string }> = [
  { id: "feedback", label: "Ask for feedback", ask: "20 minutes of critical feedback" },
  { id: "mentorship", label: "Ask for mentorship", ask: "a short call to sanity-check the direction" },
  { id: "collaboration", label: "Find a collaborator", ask: "a 15-minute call to explore working together" },
  { id: "feature", label: "Podcast / newsletter feature", ask: "whether this is relevant for your audience" },
  { id: "internship", label: "Internship / opportunity", ask: "a short conversation about opportunities" },
  { id: "grant", label: "Grant / programme", ask: "confirmation of eligibility and the next deadline" },
  { id: "intro", label: "Warm introduction", ask: "an introduction to the right person" },
];

export const OUTREACH_DAILY_CAP = 5;

function safe(text: unknown, fallback = ""): string {
  return typeof text === "string" && text.trim() ? text.trim() : fallback;
}

export function buildOutreachDraft(params: {
  dossier: any;
  recipient: OutreachRecipient;
  intent: OutreachIntent;
  senderName?: string;
}): OutreachDraft {
  const { dossier, recipient, intent } = params;
  const pack = getDomainPack(dossier?.domain_persona || dossier?.domain);
  const intentMeta = OUTREACH_INTENTS.find((item) => item.id === intent) || OUTREACH_INTENTS[0];

  const title = safe(dossier?.title, "my project");
  const tagline = safe(dossier?.tagline, "");
  const problem = safe(dossier?.problem_statement, "a problem I have been studying");
  const slug = safe(dossier?.slug, "project");
  const firstName = safe(recipient.name).split(" ")[0] || "there";
  const role = [safe(recipient.role), safe(recipient.organization)].filter(Boolean).join(" at ");
  const signature = safe(params.senderName, "A student builder");
  const pageLink = `https://studentradar.dev/p/${slug}`;
  const hook =
    safe(recipient.context) ||
    (role ? `I saw your work on ${role.split(" at ")[0]} and thought this might be relevant.` : "");

  const warnings: string[] = [
    "Analysis, not advice. Do not include confidential, client or unpublished supervisor data.",
  ];
  if (pack.key === "biotech") {
    warnings.push("Confirm patent/publication timing before sharing methods. Do not include health-benefit claims.");
  }
  if (pack.key === "law_policy") {
    warnings.push("Keep the 'analysis, not legal advice' framing and cite primary sources for legal claims.");
  }

  const subject = `${intent === "feature" ? "Story idea" : "Quick question"}: ${title.slice(0, 48)}`;

  const body = [
    `Hi ${firstName},`,
    "",
    hook || `I am working on ${title} and thought of you because of your work in ${pack.shortLabel}.`,
    `The short version: ${problem.slice(0, 180).replace(/\s+$/, "")}${tagline ? ` — ${tagline.slice(0, 120)}` : ""}.`,
    "",
    `I am reaching out to ask for ${intentMeta.ask}.`,
    `One-pager with the method, limitations and current evidence: ${pageLink}`,
    "",
    "If it is not relevant, no problem at all — a one-line reply is enough.",
    "",
    "Thanks,",
    signature,
  ]
    .filter((line, index, arr) => line !== "" || (arr[index - 1] !== "" && arr[index + 1] !== ""))
    .join("\n");

  const followUps = [
    {
      day: 4,
      subject: `Re: ${subject}`,
      body: `Hi ${firstName},\n\nJust bumping this once in case it got buried. Still happy to send the one-page summary if useful.\n\nThanks,\n${signature}`,
    },
    {
      day: 10,
      subject: `Closing the loop — ${title.slice(0, 40)}`,
      body: `Hi ${firstName},\n\nI will close the loop here. Thanks for your time either way — if the timing is better later, I would still value your view.\n\nBest,\n${signature}`,
    },
  ];

  return { subject, body, ask: intentMeta.ask, followUps, warnings };

  // `pageLink` is intentionally the project passport: every email points to
  // the same verifiable record, which is also the SEO/portfolio surface.
}
