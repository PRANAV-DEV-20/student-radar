"use client";

import React, { useMemo, useState } from "react";
import {
  Mail,
  Copy,
  Check,
  ExternalLink,
  ShieldAlert,
  CalendarClock,
  UserPlus,
} from "lucide-react";
import {
  buildOutreachDraft,
  OUTREACH_DAILY_CAP,
  OUTREACH_INTENTS,
  type OutreachIntent,
} from "@/lib/outreach";
import { markFlowStageDone } from "@/lib/flow";

const SENT_KEY = "student_radar_outreach_log";

function readSentLog(): Record<string, number> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(SENT_KEY) || "{}");
  } catch {
    return {};
  }
}

interface OutreachComposerProps {
  dossier: any;
}

export function OutreachComposer({ dossier }: OutreachComposerProps) {
  const [recipient, setRecipient] = useState({ name: "", role: "", organization: "", url: "", context: "" });
  const [intent, setIntent] = useState<OutreachIntent>("feedback");
  const [senderName, setSenderName] = useState("");
  const [consent, setConsent] = useState(false);
  const [copied, setCopied] = useState(false);
  const [sentLog, setSentLog] = useState<Record<string, number>>(() => readSentLog());

  const today = new Date().toISOString().slice(0, 10);
  const sentToday = sentLog[today] || 0;
  const atCap = sentToday >= OUTREACH_DAILY_CAP;

  const draft = useMemo(
    () =>
      recipient.name.trim().length > 0
        ? buildOutreachDraft({ dossier, recipient, intent, senderName })
        : null,
    [dossier, recipient, intent, senderName],
  );

  const recordSend = () => {
    const next = { ...readSentLog(), [today]: (readSentLog()[today] || 0) + 1 };
    localStorage.setItem(SENT_KEY, JSON.stringify(next));
    setSentLog(next);
    markFlowStageDone("connect", `${intent} email prepared for ${recipient.name}`);
  };

  const handleCopy = async () => {
    if (!draft) return;
    try {
      await navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`);
      setCopied(true);
      recordSend();
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard may be blocked; the mail-app action still works.
    }
  };

  const mailto = draft
    ? `mailto:?subject=${encodeURIComponent(draft.subject)}&body=${encodeURIComponent(draft.body)}`
    : "#";

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
      {/* Recipient + intent */}
      <div className="space-y-4 rounded-2xl border border-void-border bg-void-card p-5 lg:col-span-5">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-horizon-indigo">// CONNECT</p>
          <h2 className="mt-1 text-sm font-bold text-white">One recipient. One specific ask.</h2>
          <p className="mt-1 text-[11px] leading-relaxed text-gray-400">
            Paste a person, not a list. We draft the email; you send it from your own mail app. No bulk sending, ever.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {[
            { key: "name", label: "Name", placeholder: "Dr. Asha Rao" },
            { key: "role", label: "Role", placeholder: "Principal Investigator" },
            { key: "organization", label: "Organisation", placeholder: "University / lab" },
            { key: "url", label: "Profile URL (optional)", placeholder: "https://…" },
          ].map((field) => (
            <label key={field.key} className="block">
              <span className="mb-1 block text-[10px] font-mono uppercase text-gray-500">{field.label}</span>
              <input
                value={(recipient as any)[field.key]}
                onChange={(event) =>
                  setRecipient((previous) => ({ ...previous, [field.key]: event.target.value }))
                }
                placeholder={field.placeholder}
                className="w-full rounded-lg border border-void-border bg-void px-3 py-2 text-xs text-white placeholder-gray-600 focus:border-horizon-indigo focus:outline-none"
              />
            </label>
          ))}
        </div>

        <label className="block">
          <span className="mb-1 block text-[10px] font-mono uppercase text-gray-500">
            Why this person? (one line — makes the email specific)
          </span>
          <input
            value={recipient.context}
            onChange={(event) => setRecipient((previous) => ({ ...previous, context: event.target.value }))}
            placeholder="They published the benchmark our project builds on"
            className="w-full rounded-lg border border-void-border bg-void px-3 py-2 text-xs text-white placeholder-gray-600 focus:border-horizon-indigo focus:outline-none"
          />
        </label>

        <label className="block">
          <span className="mb-1 block text-[10px] font-mono uppercase text-gray-500">Intent</span>
          <select
            value={intent}
            onChange={(event) => setIntent(event.target.value as OutreachIntent)}
            className="w-full rounded-lg border border-void-border bg-void px-3 py-2 text-xs text-white focus:border-horizon-indigo focus:outline-none"
          >
            {OUTREACH_INTENTS.map((item) => (
              <option key={item.id} value={item.id}>{item.label}</option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1 block text-[10px] font-mono uppercase text-gray-500">Your name (signature)</span>
          <input
            value={senderName}
            onChange={(event) => setSenderName(event.target.value)}
            placeholder="Your name"
            className="w-full rounded-lg border border-void-border bg-void px-3 py-2 text-xs text-white placeholder-gray-600 focus:border-horizon-indigo focus:outline-none"
          />
        </label>

        <div className="rounded-xl border border-amber-500/25 bg-amber-500/5 p-3">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-amber-400" />
            <p className="text-[11px] font-bold text-amber-200">Consent & rate limit</p>
          </div>
          <label className="mt-2 flex cursor-pointer items-start gap-2 text-[11px] leading-relaxed text-gray-300">
            <input
              type="checkbox"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
              className="mt-0.5 h-3.5 w-3.5 accent-emerald-500"
            />
            I have a legitimate reason to contact this person and will not send unsolicited bulk email.
          </label>
          <p className="mt-2 font-mono text-[10px] text-gray-400">
            {OUTREACH_DAILY_CAP - sentToday} of {OUTREACH_DAILY_CAP} daily drafts remaining · day 4 & day 10 follow-ups included
          </p>
        </div>
      </div>

      {/* Draft */}
      <div className="space-y-4 lg:col-span-7">
        <div className="rounded-2xl border border-void-border bg-void-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-void-border pb-3">
            <p className="font-mono text-[10px] uppercase tracking-widest text-gray-400">Generated draft</p>
            <div className="flex gap-2">
              <button
                onClick={handleCopy}
                disabled={!draft || !consent || atCap}
                className="flex items-center gap-1.5 rounded-lg bg-white/10 px-3 py-1.5 text-[11px] font-semibold text-white disabled:opacity-40"
              >
                {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                {copied ? "Copied" : "Copy draft"}
              </button>
              <a
                href={!draft || !consent || atCap ? undefined : mailto}
                onClick={() => draft && consent && !atCap && recordSend()}
                className={`flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-horizon-indigo to-horizon-violet px-3 py-1.5 text-[11px] font-semibold text-white ${
                  !draft || !consent || atCap ? "pointer-events-none opacity-40" : ""
                }`}
              >
                <Mail className="h-3 w-3" /> Open in my mail app <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          </div>

          {draft ? (
            <div className="space-y-3 pt-4">
              <p className="text-xs font-bold text-white">Subject: {draft.subject}</p>
              <textarea
                readOnly
                rows={13}
                value={draft.body}
                className="w-full resize-none rounded-xl border border-void-border bg-void p-3.5 text-xs leading-relaxed text-gray-200 focus:outline-none"
              />
              <div className="rounded-lg border border-void-border bg-void p-3">
                <p className="font-mono text-[10px] uppercase text-gray-500">The single ask</p>
                <p className="mt-1 text-xs text-white">{draft.ask}</p>
              </div>
              <div className="space-y-1.5">
                {draft.warnings.map((warning) => (
                  <p key={warning} className="flex gap-2 text-[11px] leading-relaxed text-amber-200/90">
                    <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-amber-400" /> {warning}
                  </p>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex h-64 flex-col items-center justify-center gap-2 text-gray-500">
              <UserPlus className="h-6 w-6" />
              <p className="text-xs">Add a recipient to generate a personalised draft.</p>
            </div>
          )}
        </div>

        {draft && (
          <div className="rounded-2xl border border-void-border bg-void-card p-5">
            <div className="flex items-center gap-2">
              <CalendarClock className="h-4 w-4 text-horizon-indigo" />
              <p className="text-xs font-bold text-white">Follow-up schedule</p>
            </div>
            <div className="mt-3 space-y-2">
              {draft.followUps.map((followUp) => (
                <div key={followUp.day} className="rounded-lg border border-void-border bg-void p-3">
                  <p className="font-mono text-[10px] uppercase text-horizon-indigo">Day {followUp.day} nudge</p>
                  <p className="mt-1 text-[11px] font-semibold text-white">{followUp.subject}</p>
                  <p className="mt-1 whitespace-pre-line text-[11px] leading-relaxed text-gray-400">{followUp.body}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
