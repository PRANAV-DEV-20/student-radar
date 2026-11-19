"use client";

import React, { useMemo } from "react";
import { ExternalLink, AlertTriangle, ShieldCheck, Sparkles, Info } from "lucide-react";
import { buildProjectDNA } from "@/lib/projectDna";

interface ProjectDNACardProps {
  dossier: any;
  compact?: boolean;
}

export function ProjectDNACard({ dossier, compact = false }: ProjectDNACardProps) {
  const dna = useMemo(() => buildProjectDNA(dossier), [dossier]);
  const pack = dna.domainPack;

  return (
    <section className="space-y-4 rounded-2xl border border-horizon-indigo/20 bg-void-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-void-border pb-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-horizon-indigo">
            // PROJECT DNA — ONE CARD, EVERY STAGE
          </p>
          <h2 className="mt-1 text-sm font-bold text-white">Understand your project</h2>
          <p className="mt-1 max-w-2xl text-[11px] leading-relaxed text-gray-400">{dna.summary}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-void-border px-2.5 py-1 font-mono text-[10px] text-gray-400">
            {pack.shortLabel}
          </span>
          <span
            className={`rounded-full border px-2.5 py-1 font-mono text-[10px] ${
              dna.confidence === "high"
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                : dna.confidence === "medium"
                  ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                  : "border-gray-500/30 bg-gray-500/10 text-gray-400"
            }`}
          >
            {dna.confidence} confidence
          </span>
        </div>
      </div>

      {/* Readiness */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-void-border bg-void p-4">
          <div className="flex items-end justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-widest text-gray-500">Readiness</p>
              <p className="mt-1 text-3xl font-bold font-mono text-white">{dna.readiness.total}<span className="text-sm text-gray-500">/100</span></p>
            </div>
            <Sparkles className="h-5 w-5 text-horizon-indigo" />
          </div>
          <div className="mt-3 space-y-2">
            {dna.readiness.axes.map((axis) => (
              <div key={axis.key}>
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-gray-300">{axis.label}</span>
                  <span className="font-mono text-gray-500">{axis.score}</span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-void-subtle">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-horizon-indigo to-horizon-violet"
                    style={{ width: `${axis.score}%` }}
                  />
                </div>
                {axis.fix && <p className="mt-1 text-[10px] leading-snug text-amber-300/90">Fix: {axis.fix}</p>}
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-void-border bg-void p-4">
          <p className="font-mono text-[10px] uppercase tracking-widest text-gray-500">Stage-aware next step</p>
          <p className="mt-2 text-xs font-semibold text-white">{dna.stage}</p>
          <p className="mt-2 text-xs leading-relaxed text-gray-300">{dna.stageAdvice}</p>
          <div className="mt-3 border-t border-void-border pt-3">
            <p className="font-mono text-[10px] uppercase tracking-widest text-gray-500">What counts as proof here</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {pack.proof.map((item) => (
                <span key={item} className="rounded-full border border-void-border px-2 py-0.5 text-[10px] text-gray-300">
                  {item}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* DNA fields */}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {dna.fields.map((field) => (
          <div key={field.label} className="rounded-xl border border-void-border bg-void p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="font-mono text-[10px] uppercase tracking-widest text-gray-500">{field.label}</p>
              {field.basis === "missing" && <AlertTriangle className="h-3 w-3 text-amber-400" />}
            </div>
            <p className={`mt-1 text-xs leading-relaxed ${field.basis === "missing" ? "text-amber-200/80" : "text-gray-200"}`}>
              {field.value}
            </p>
          </div>
        ))}
      </div>

      {!compact && (
        <>
          {/* Claim verification */}
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-amber-400" />
              <p className="text-xs font-bold text-amber-200">
                Claim verification — {dna.claims.length ? `${dna.claims.length} to check` : "no unsupported claims detected"}
              </p>
            </div>
            {dna.claims.length ? (
              <div className="mt-3 space-y-2">
                {dna.claims.slice(0, 5).map((claim, index) => (
                  <div key={`${claim.text}-${index}`} className="rounded-lg border border-amber-500/20 bg-void/60 p-3">
                    <p className="text-[11px] font-semibold text-amber-200">
                      “{claim.text}” <span className="font-mono text-[9px] uppercase text-amber-400/70">{claim.severity}</span>
                    </p>
                    <p className="mt-1 text-[11px] text-gray-400">{claim.reason}</p>
                    <p className="mt-1 text-[11px] text-gray-300">Fix: {claim.fix}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-[11px] text-gray-400">
                No high-scrutiny wording found. Re-check after every update.
              </p>
            )}
          </div>

          {/* Safety rules from the domain pack */}
          <div className="rounded-xl border border-void-border bg-void p-4">
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-horizon-violet" />
              <p className="text-xs font-bold text-white">{pack.shortLabel} safety rules</p>
            </div>
            <ul className="mt-2 space-y-1.5">
              {pack.safetyRules.map((rule) => (
                <li key={rule} className="flex gap-2 text-[11px] leading-relaxed text-gray-400">
                  <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-horizon-violet" />
                  {rule}
                </li>
              ))}
            </ul>
          </div>

          {/* Evidence — only real retrieved links */}
          <div className="rounded-xl border border-void-border bg-void p-4">
            <p className="font-mono text-[10px] uppercase tracking-widest text-gray-500">
              Source-linked records ({dna.evidence.length})
            </p>
            {dna.evidence.length ? (
              <div className="mt-2 space-y-2">
                {dna.evidence.slice(0, 8).map((source, index) => (
                  <a
                    key={`${source.url}-${index}`}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start justify-between gap-3 rounded-lg border border-void-border bg-void-card p-2.5 text-[11px] text-gray-300 hover:border-horizon-indigo/40"
                  >
                    <span className="min-w-0">
                      <span className="block truncate font-semibold text-gray-200">{source.title}</span>
                      <span className="block font-mono text-[9px] uppercase text-gray-500">
                        {source.kind} · {source.platform}
                      </span>
                    </span>
                    <ExternalLink className="h-3 w-3 shrink-0 text-horizon-indigo" />
                  </a>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-[11px] text-gray-500">
                No external records retrieved yet. Refresh the reality check in the Dossier workspace.
              </p>
            )}
          </div>
        </>
      )}
    </section>
  );
}
