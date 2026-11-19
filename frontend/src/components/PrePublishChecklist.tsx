"use client";

import React, { useMemo, useState } from "react";
import { ShieldCheck, Check, Lock } from "lucide-react";
import { buildProjectDNA } from "@/lib/projectDna";
import { getDomainPack } from "@/lib/domainPacks";
import { markFlowStageDone } from "@/lib/flow";

interface PrePublishChecklistProps {
  dossier: any;
  onConfirmed?: () => void;
}

/** Domain-specific gate shown before any public copy is generated. */
export function PrePublishChecklist({ dossier, onConfirmed }: PrePublishChecklistProps) {
  const dna = useMemo(() => buildProjectDNA(dossier), [dossier]);
  const pack = getDomainPack(dossier?.domain_persona || dossier?.domain);
  const [checked, setChecked] = useState<Record<number, boolean>>({});

  const items = [
    ...pack.safetyRules,
    "I confirm this work is not confidential, supervisor-owned, or under NDA — or I have permission to share it.",
    ...dna.claims.slice(0, 2).map((claim) => `I have verified or removed the claim: “${claim.text}”.`),
  ];
  const done = items.every((_, index) => checked[index]);

  const toggle = (index: number) => {
    setChecked((previous) => ({ ...previous, [index]: !previous[index] }));
    if (!done) markFlowStageDone("position", "Pre-publish safety check reviewed");
  };

  return (
    <section className="rounded-2xl border border-horizon-violet/25 bg-horizon-violet/5 p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-horizon-violet" />
          <div>
            <p className="text-xs font-bold text-white">Pre-publish safety check · {pack.shortLabel}</p>
            <p className="text-[10px] text-gray-400">Required before copy is publishable. Drafts stay private until you copy them.</p>
          </div>
        </div>
        <span className="font-mono text-[10px] text-gray-400">
          {Object.values(checked).filter(Boolean).length}/{items.length}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
        {items.map((item, index) => (
          <label
            key={`${item}-${index}`}
            className={`flex cursor-pointer items-start gap-2 rounded-lg border p-2.5 text-[11px] leading-relaxed transition-colors ${
              checked[index]
                ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-100"
                : "border-void-border bg-void text-gray-400 hover:text-gray-200"
            }`}
          >
            <input
              type="checkbox"
              checked={Boolean(checked[index])}
              onChange={() => toggle(index)}
              className="mt-0.5 h-3.5 w-3.5 shrink-0 accent-emerald-500"
            />
            <span>{item}</span>
          </label>
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between gap-3 border-t border-void-border pt-3">
        <span className="flex items-center gap-1.5 text-[10px] text-gray-500">
          <Lock className="h-3 w-3" /> Nothing publishes automatically.
        </span>
        <button
          disabled={!done}
          onClick={() => {
            markFlowStageDone("position", "Pre-publish safety check completed");
            onConfirmed?.();
          }}
          className="flex items-center gap-1.5 rounded-lg bg-horizon-indigo px-3 py-1.5 text-[11px] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Check className="h-3 w-3" /> Confirm & continue
        </button>
      </div>
    </section>
  );
}
