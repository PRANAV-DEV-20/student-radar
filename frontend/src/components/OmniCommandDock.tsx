"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Github, FileText, Sparkles, Loader2, Link as LinkIcon, AlertCircle, CheckCircle2 } from "lucide-react";
import { DOMAIN_PERSONAS, DEMO_PRESETS, DemoPreset } from "@/lib/constants";
import { api } from "@/lib/api";

interface OmniCommandDockProps {
  onIngestComplete?: (dossier: any) => void;
}

export function OmniCommandDock({ onIngestComplete }: OmniCommandDockProps) {
  const router = useRouter();
  const [content, setContent] = useState("");
  const [persona, setPersona] = useState("tech_builder");
  const [isLoading, setIsLoading] = useState(false);
  const [generationStep, setGenerationStep] = useState("");
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"idea" | "github" | "pdf_text">("idea");

  const handleContentChange = (val: string) => {
    setContent(val);
    setError("");
    // Auto-detect GitHub URLs
    if (/^https?:\/\/(?:www\.)?github\.com\//i.test(val.trim())) {
      setActiveTab("github");
    }
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = content.trim();
    if (!trimmed) {
      setError("Please describe your project idea or paste a repository link.");
      return;
    }

    setError("");
    setIsLoading(true);
    setGenerationStep("Analyzing your concept & problem domain...");

    try {
      // Step feedback animation
      const timer1 = setTimeout(() => {
        setGenerationStep("Synthesizing system architecture & stack...");
      }, 700);

      const timer2 = setTimeout(() => {
        setGenerationStep("Inferring verified benchmarks & whitespace...");
      }, 1400);

      const looksLikeUrl = /^https?:\/\//i.test(trimmed);
      const effectiveType = activeTab === "github" && !looksLikeUrl ? "idea" : activeTab;

      const dossier = await api.ingestArtifact({
        input_type: effectiveType,
        raw_content: trimmed,
        domain_persona: persona
      });

      clearTimeout(timer1);
      clearTimeout(timer2);

      if (!dossier || !dossier.slug || !dossier.title) {
        throw new Error("Could not synthesize dossier. Please try again.");
      }

      setGenerationStep("Dossier generated! Opening workspace...");

      // Cache dossier in session & local storage
      if (typeof window !== "undefined") {
        sessionStorage.setItem("current_dossier", JSON.stringify(dossier));
        localStorage.setItem("student_radar_last_dossier", JSON.stringify(dossier));
      }

      setTimeout(() => {
        if (onIngestComplete) {
          onIngestComplete(dossier);
        } else {
          router.push(`/dossier?slug=${encodeURIComponent(dossier.slug)}`);
        }
      }, 500);

    } catch (err: any) {
      console.error("Ingestion error:", err);
      setError(err?.message || "Could not generate the dossier. Please try again.");
      setIsLoading(false);
    }
  };

  const handleSelectPreset = (preset: DemoPreset) => {
    setError("");
    setContent(preset.rawContent);
    setPersona(preset.domain);
    setActiveTab(preset.type as any);
  };

  return (
    <div className="w-full max-w-3xl mx-auto flex flex-col gap-4">
      {/* Omni-Command Dock Surface */}
      <div className="relative rounded-2xl bg-void-card/90 border border-void-border p-3 sm:p-4 shadow-2xl backdrop-blur-2xl transition-all focus-within:border-horizon-indigo/60 focus-within:ring-2 focus-within:ring-horizon-indigo/20">
        
        {/* Glow ambient layer */}
        <div className="absolute -inset-0.5 bg-gradient-to-r from-horizon-indigo/20 to-horizon-violet/20 rounded-2xl blur-lg -z-10 opacity-75 group-hover:opacity-100 transition duration-1000" />

        {/* Input Mode Tabs & Persona selector */}
        <div className="flex flex-wrap items-center justify-between gap-2 px-1 pb-3 border-b border-void-border/60">
          <div className="flex items-center gap-1 bg-void/60 p-1 rounded-lg border border-void-border/50 text-xs">
            <button
              type="button"
              onClick={() => setActiveTab("idea")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
                activeTab === "idea" ? "bg-white/10 text-white font-medium shadow-inner" : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-horizon-indigo" />
              <span>Concept & Idea</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("github")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
                activeTab === "github" ? "bg-white/10 text-white font-medium shadow-inner" : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <Github className="w-3.5 h-3.5" />
              <span>GitHub Link</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("pdf_text")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
                activeTab === "pdf_text" ? "bg-white/10 text-white font-medium shadow-inner" : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Paper / PDF</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-gray-500">Domain Persona:</span>
            <select
              value={persona}
              onChange={(e) => setPersona(e.target.value)}
              aria-label="Select target domain persona"
              className="bg-void/80 border border-void-border rounded-lg text-xs text-gray-200 px-2.5 py-1.5 focus:outline-none focus:border-horizon-indigo cursor-pointer"
            >
              {DOMAIN_PERSONAS.map((p) => (
                <option key={p.id} value={p.id} className="bg-void-card text-white">
                  {p.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 pt-3 px-1">
          <div className="relative w-full">
            <textarea
              value={content}
              onChange={(e) => handleContentChange(e.target.value)}
              rows={activeTab === "github" ? 2 : 3}
              placeholder={
                activeTab === "github"
                  ? "Paste repository URL (e.g. https://github.com/org/repo)..."
                  : activeTab === "idea"
                  ? "Describe your project concept, problem statement, or technical vision (e.g., 'An AI interview coach with real-time speech feedback and behavioral rubrics for students')..."
                  : "Paste your research paper abstract or technical concept..."
              }
              className="w-full bg-void/50 rounded-xl border border-void-border/80 p-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-horizon-indigo resize-none leading-relaxed font-sans"
            />
          </div>

          {/* Action Row */}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-[11px] text-gray-400 font-mono">
              ⚡ Turns ideas into verified Dossiers + PR Kits in &lt; 2 seconds
            </span>

            <button
              type="submit"
              disabled={isLoading || !content.trim()}
              className="flex items-center gap-2 bg-gradient-to-r from-horizon-indigo to-horizon-violet hover:from-indigo-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold px-5 py-2.5 rounded-xl shadow-lg transition-all active:scale-95"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>{generationStep || "Synthesizing..."}</span>
                </>
              ) : (
                <>
                  <span>Generate Proof-of-Work Dossier</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>

        {/* Live Generation Progress Indicator */}
        {isLoading && (
          <div className="mt-3 p-2.5 rounded-xl bg-horizon-indigo/10 border border-horizon-indigo/30 flex items-center gap-2 text-xs text-indigo-300 font-mono animate-pulse">
            <Sparkles className="w-4 h-4 text-horizon-indigo shrink-0" />
            <span>{generationStep}</span>
          </div>
        )}

        {/* Error notification */}
        {error && (
          <div className="mt-3 p-2.5 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-2 text-xs text-red-400">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* 1-Tap Live Demo Presets */}
      <div className="flex flex-col gap-1.5 px-1">
        <div className="flex items-center justify-between text-[11px] font-mono text-gray-500">
          <span>⚡ OR TRY 1-TAP LIVE DEMO PRESETS:</span>
          <span>Click to populate</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {DEMO_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => handleSelectPreset(preset)}
              className="group flex flex-col items-start p-2.5 rounded-xl bg-void-card/60 hover:bg-void-card border border-void-border hover:border-horizon-indigo/50 transition-all text-left"
            >
              <span className="text-xs font-semibold text-gray-200 group-hover:text-white flex items-center justify-between w-full">
                {preset.title}
                <span className="text-[10px] text-gray-500 font-mono">↗</span>
              </span>
              <span className="text-[11px] text-gray-400 line-clamp-2 mt-1 leading-snug">
                {preset.snippet}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
