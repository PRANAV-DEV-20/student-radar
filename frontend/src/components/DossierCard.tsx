"use client";

import React, { useState } from "react";
import Link from "next/navigation";
import { ShieldCheck, Share2, Sparkles, ExternalLink, Check, Copy, ArrowRight, Code } from "lucide-react";

interface DossierCardProps {
  dossier: any;
  onOpenPeerReview?: () => void;
  onOpenPRStudio?: () => void;
}

export function DossierCard({ dossier, onOpenPeerReview, onOpenPRStudio }: DossierCardProps) {
  const [copied, setCopied] = useState(false);

  if (!dossier) return null;

  const handleCopyLink = () => {
    if (typeof window !== "undefined") {
      const url = `${window.location.origin}/p/${dossier.slug}`;
      navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const solution = dossier.solution_breakdown || {};
  const metrics = dossier.key_metrics || [];
  const stack = dossier.tech_stack || [];
  const links = dossier.external_links || {};

  return (
    <div className="w-full rounded-2xl bg-editorial-paper border border-white/20 p-6 sm:p-8 shadow-2xl text-editorial-ink relative">
      {/* Top Metadata Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 pb-4 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-xs uppercase font-mono px-2.5 py-1 rounded bg-gray-100 border border-gray-300 font-semibold text-gray-700">
            {dossier.domain_persona?.replace("_", " ").toUpperCase() || "TECH BUILDER"}
          </span>
          <span className="text-xs text-gray-500 font-mono">
            ID: {dossier.slug}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {dossier.verified_status ? (
            <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-100 border border-emerald-300 px-3 py-1 rounded-full shadow-xs">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              VERIFIED ARTIFACT
            </span>
          ) : (
            <span className="text-xs text-gray-500 bg-gray-100 px-2.5 py-1 rounded-full font-mono">
              Unverified Link
            </span>
          )}
          <button
            onClick={handleCopyLink}
            className="flex items-center gap-1 text-xs text-gray-600 hover:text-black border border-gray-300 bg-white hover:bg-gray-50 px-3 py-1 rounded-lg transition-all"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? "Copied" : "Share"}</span>
          </button>
        </div>
      </div>

      {/* Main Title & Tagline */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold font-serif text-gray-900 tracking-tight leading-tight mb-2">
          {dossier.title}
        </h1>
        <p className="text-sm sm:text-base text-gray-600 leading-relaxed font-normal">
          {dossier.tagline}
        </p>
      </div>

      {/* Quantitative Benchmarks Grid */}
      {metrics.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-8">
          {metrics.map((metric: any, i: number) => (
            <div key={i} className="p-4 rounded-xl bg-white border border-gray-200 shadow-xs">
              <span className="text-[11px] font-mono uppercase text-gray-500 tracking-wide block mb-1">
                {metric.label}
              </span>
              <span className="text-2xl font-bold font-mono text-gray-900 tracking-tight">
                {metric.value}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Core Technical Breakdown */}
      <div className="space-y-6 mb-8 text-sm leading-relaxed">
        {/* Problem Statement */}
        <div className="bg-white/80 p-5 rounded-xl border border-gray-200">
          <h3 className="text-xs font-mono uppercase tracking-wider font-bold text-gray-500 mb-2">
            // Problem Statement & Vulnerability
          </h3>
          <p className="text-gray-800">
            {dossier.problem_statement}
          </p>
        </div>

        {/* Architectural Breakdown */}
        <div className="bg-white/80 p-5 rounded-xl border border-gray-200 space-y-4">
          <h3 className="text-xs font-mono uppercase tracking-wider font-bold text-gray-500">
            // System Architecture & Execution
          </h3>
          
          {solution.architecture && (
            <div>
              <span className="font-semibold text-gray-900 text-xs uppercase font-mono block">Architecture:</span>
              <p className="text-gray-700 mt-0.5">{solution.architecture}</p>
            </div>
          )}

          {solution.core_algorithms && (
            <div>
              <span className="font-semibold text-gray-900 text-xs uppercase font-mono block">Core Algorithms:</span>
              <ul className="list-disc list-inside text-gray-700 mt-1 space-y-0.5">
                {Array.isArray(solution.core_algorithms) ? (
                  solution.core_algorithms.map((alg: string, idx: number) => (
                    <li key={idx} className="font-mono text-xs">{alg}</li>
                  ))
                ) : (
                  <li className="font-mono text-xs">{solution.core_algorithms}</li>
                )}
              </ul>
            </div>
          )}

          {solution.hardware_or_infra && (
            <div>
              <span className="font-semibold text-gray-900 text-xs uppercase font-mono block">Infrastructure / Hardware:</span>
              <p className="text-gray-700 mt-0.5 font-mono text-xs">{solution.hardware_or_infra}</p>
            </div>
          )}
        </div>
      </div>

      {/* Tech Stack Chips */}
      {stack.length > 0 && (
        <div className="mb-8">
          <span className="text-xs font-mono uppercase text-gray-500 block mb-2 font-bold">
            Artifact Dependencies & Stack:
          </span>
          <div className="flex flex-wrap gap-2">
            {stack.map((item: string) => (
              <span key={item} className="text-xs font-mono bg-white border border-gray-300 text-gray-800 px-3 py-1 rounded-md shadow-2xs">
                {item}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Verified External Links */}
      {links.github && (
        <div className="mb-8 flex items-center gap-2">
          <span className="text-xs text-gray-500 font-mono">External Repo:</span>
          <a
            href={links.github}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-mono text-indigo-600 hover:text-indigo-800 flex items-center gap-1 underline underline-offset-2"
          >
            {links.github} <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      )}

      {/* Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-6 border-t border-gray-200">
        <button
          onClick={onOpenPeerReview}
          className="flex items-center gap-1.5 bg-white hover:bg-gray-50 border border-gray-300 text-gray-800 text-xs font-semibold px-4 py-2.5 rounded-xl transition-all shadow-xs"
        >
          <Sparkles className="w-4 h-4 text-horizon-violet" />
          <span>Peer Review (+10⚡)</span>
        </button>

        <button
          onClick={onOpenPRStudio}
          className="flex items-center gap-2 bg-gradient-to-r from-horizon-indigo to-horizon-violet hover:from-indigo-600 hover:to-purple-600 text-white text-xs font-semibold px-5 py-2.5 rounded-xl shadow-md transition-all active:scale-95"
        >
          <span>Open in PR Studio</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

