"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Github, FileText, Sparkles, Loader2, Link as LinkIcon, Compass } from "lucide-react";
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
  const [activeTab, setActiveTab] = useState<"github" | "idea" | "pdf_text">("github");

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!content.trim()) return;

    setIsLoading(true);
    try {
      const dossier = await api.ingestArtifact({
        input_type: activeTab,
        raw_content: content.trim(),
        domain_persona: persona
      });

      // Save active dossier in session storage
      if (typeof window !== "undefined") {
        sessionStorage.setItem("current_dossier", JSON.stringify(dossier));
      }

      if (onIngestComplete) {
        onIngestComplete(dossier);
      } else {
        router.push(`/dossier?slug=${dossier.slug}`);
      }
    } catch (err: any) {
      console.error("Ingestion error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectPreset = (preset: DemoPreset) => {
    setContent(preset.rawContent);
    setPersona(preset.domain);
    setActiveTab(preset.type);
  };

  return (
    <div className="w-full max-w-3xl mx-auto flex flex-col gap-4">
      {/* Omni-Command Dock Surface */}
      <div className="relative rounded-2xl bg-void-card/90 border border-void-border p-2 sm:p-3 shadow-2xl backdrop-blur-2xl transition-all focus-within:border-horizon-indigo/60 focus-within:ring-2 focus-within:ring-horizon-indigo/20">
        
        {/* Glow ambient layer */}
        <div className="absolute -inset-0.5 bg-gradient-to-r from-horizon-indigo/20 to-horizon-violet/20 rounded-2xl blur-lg -z-10 opacity-75 group-hover:opacity-100 transition duration-1000" />

        {/* Input Mode Tabs & Persona selector */}
        <div className="flex flex-wrap items-center justify-between gap-2 px-2 pb-2 border-b border-void-border/60">
          <div className="flex items-center gap-1 bg-void/60 p-1 rounded-lg border border-void-border/50 text-xs">
            <button
              type="button"
              onClick={() => setActiveTab("github")}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
                activeTab === "github" ? "bg-white/10 text-white font-medium" : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <Github className="w-3.5 h-3.5" />
              <span>GitHub Link</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("idea")}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
                activeTab === "idea" ? "bg-white/10 text-white font-medium" : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Raw Concept</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("pdf_text")}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
                activeTab === "pdf_text" ? "bg-white/10 text-white font-medium" : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Paper / Abstract</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-gray-500">Domain:</span>
            <select
              value={persona}
              onChange={(e) => setPersona(e.target.value)}
              aria-label="Select target domain persona"
              className="bg-void/80 border border-void-border rounded-lg text-xs text-gray-200 px-2.5 py-1 focus:outline-none focus:border-horizon-indigo cursor-pointer"
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
        <form onSubmit={handleSubmit} className="flex items-center gap-2 pt-2 px-2">
          <div className="relative flex-1 flex items-center">
            {activeTab === "github" ? (
              <LinkIcon className="absolute left-3 w-4 h-4 text-gray-500" />
            ) : (
              <Sparkles className="absolute left-3 w-4 h-4 text-horizon-indigo" />
            )}
            <input
              type="text"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={
                activeTab === "github"
                  ? "Paste repository URL (e.g. https://github.com/org/repo)..."
                  : activeTab === "idea"
                  ? "Describe what you're building, core problem, and technical architecture..."
                  : "Paste paper abstract or research text breakdown..."
              }
              className="w-full bg-transparent pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !content.trim()}
            className="flex items-center gap-2 bg-gradient-to-r from-horizon-indigo to-horizon-violet hover:from-indigo-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-lg transition-all active:scale-95 shrink-0"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Extracting...</span>
              </>
            ) : (
              <>
                <span>Generate Dossier</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>
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

