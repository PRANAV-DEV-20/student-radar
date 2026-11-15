"use client";

import React, { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { api } from "@/lib/api";
import { Copy, Check, Sparkles, Zap, Share2, RefreshCw, Send, Loader2 } from "lucide-react";

function PRStudioContent() {
  const searchParams = useSearchParams();
  const paramDossierId = searchParams.get("dossierId");

  const [dossier, setDossier] = useState<any>(null);
  const [playbookType, setPlaybookType] = useState<"linkedin" | "instagram_reel" | "cold_pitch">("linkedin");
  const [tone, setTone] = useState<"academic" | "high_octane" | "executive">("high_octane");
  const [targetAudience, setTargetAudience] = useState("Peer builders, technical founders, and investors");
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [prData, setPrData] = useState<any>(null);
  const [copied, setCopied] = useState(false);
  
  const [isBoosting, setIsBoosting] = useState(false);
  const [boostSuccess, setBoostSuccess] = useState(false);

  useEffect(() => {
    const stored = typeof window !== "undefined" ? sessionStorage.getItem("current_dossier") : null;
    if (stored) {
      const parsed = JSON.parse(stored);
      setDossier(parsed);
      generateCopy(parsed, playbookType, tone);
    } else {
      api.getDossier("autonomous-drone-swarm-18d39f").then((res) => {
        setDossier(res);
        generateCopy(res, playbookType, tone);
      });
    }
  }, []);

  const generateCopy = async (targetDossier: any, pType: string, pTone: string) => {
    setIsGenerating(true);
    try {
      const res = await api.generatePR({
        dossier_id: targetDossier?.id || "mock-id",
        playbook_type: pType,
        tone: pTone,
        target_audience: targetAudience
      });
      setPrData(res);
    } catch (err) {
      console.error("PR generation failed:", err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handlePlaybookChange = (newType: "linkedin" | "instagram_reel" | "cold_pitch") => {
    setPlaybookType(newType);
    if (dossier) generateCopy(dossier, newType, tone);
  };

  const handleToneChange = (newTone: "academic" | "high_octane" | "executive") => {
    setTone(newTone);
    if (dossier) generateCopy(dossier, playbookType, newTone);
  };

  const handleCopy = () => {
    if (prData?.body_markdown) {
      navigator.clipboard.writeText(prData.body_markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleBoost = async () => {
    if (!dossier?.id) return;
    setIsBoosting(true);
    try {
      await api.boostDossier(dossier.id);
      setBoostSuccess(true);
    } catch (err: any) {
      console.error("Boost failed:", err);
    } finally {
      setIsBoosting(false);
    }
  };

  return (
    <>
      {/* Page Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-mono uppercase tracking-widest text-horizon-indigo">
            // 3-COLUMN PR STUDIO
          </span>
          <span className="text-xs text-gray-400 font-mono">
            [Anchored to: {dossier?.title || "Project Dossier"}]
          </span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
          Automated PR Kit & Social Launch Studio
        </h1>
      </div>

      {/* 3-Column Studio Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* COLUMN 1: Playbook & Voice Configurator (3 Cols) */}
        <div className="lg:col-span-3 rounded-2xl bg-void-card border border-void-border p-5 space-y-6">
          <div>
            <span className="text-xs font-mono uppercase text-gray-400 font-bold block mb-3">
              1. Select Playbook
            </span>
            <div className="space-y-2">
              <button
                onClick={() => handlePlaybookChange("linkedin")}
                className={`w-full flex items-center justify-between p-3 rounded-xl border text-xs font-semibold text-left transition-all ${
                  playbookType === "linkedin"
                    ? "bg-horizon-indigo/20 border-horizon-indigo text-white shadow-xs"
                    : "bg-void border-void-border text-gray-400 hover:text-white"
                }`}
              >
                <span>LinkedIn Viral Hook</span>
                <span className="font-mono text-[10px] text-indigo-300">#B2B</span>
              </button>

              <button
                onClick={() => handlePlaybookChange("instagram_reel")}
                className={`w-full flex items-center justify-between p-3 rounded-xl border text-xs font-semibold text-left transition-all ${
                  playbookType === "instagram_reel"
                    ? "bg-horizon-indigo/20 border-horizon-indigo text-white shadow-xs"
                    : "bg-void border-void-border text-gray-400 hover:text-white"
                }`}
              >
                <span>Instagram Reel Storyboard</span>
                <span className="font-mono text-[10px] text-purple-300">#Video</span>
              </button>

              <button
                onClick={() => handlePlaybookChange("cold_pitch")}
                className={`w-full flex items-center justify-between p-3 rounded-xl border text-xs font-semibold text-left transition-all ${
                  playbookType === "cold_pitch"
                    ? "bg-horizon-indigo/20 border-horizon-indigo text-white shadow-xs"
                    : "bg-void border-void-border text-gray-400 hover:text-white"
                }`}
              >
                <span>Investor / Recruiter Pitch</span>
                <span className="font-mono text-[10px] text-amber-300">#Email</span>
              </button>
            </div>
          </div>

          {/* Tone Slider */}
          <div>
            <span className="text-xs font-mono uppercase text-gray-400 font-bold block mb-2">
              2. Tone Modulation
            </span>
            <div className="grid grid-cols-3 gap-1 bg-void p-1 rounded-xl border border-void-border text-[11px]">
              <button
                onClick={() => handleToneChange("academic")}
                className={`py-1.5 rounded-lg transition-all ${
                  tone === "academic" ? "bg-white/10 text-white font-bold" : "text-gray-400"
                }`}
              >
                Academic
              </button>
              <button
                onClick={() => handleToneChange("high_octane")}
                className={`py-1.5 rounded-lg transition-all ${
                  tone === "high_octane" ? "bg-white/10 text-white font-bold" : "text-gray-400"
                }`}
              >
                High Octane
              </button>
              <button
                onClick={() => handleToneChange("executive")}
                className={`py-1.5 rounded-lg transition-all ${
                  tone === "executive" ? "bg-white/10 text-white font-bold" : "text-gray-400"
                }`}
              >
                Executive
              </button>
            </div>
          </div>

          {/* Target Audience */}
          <div>
            <span className="text-xs font-mono uppercase text-gray-400 font-bold block mb-1.5">
              3. Target Audience
            </span>
            <input
              type="text"
              value={targetAudience}
              onChange={(e) => setTargetAudience(e.target.value)}
              className="w-full rounded-xl bg-void border border-void-border p-2.5 text-xs text-white focus:outline-none focus:border-horizon-indigo"
            />
          </div>

          <button
            onClick={() => dossier && generateCopy(dossier, playbookType, tone)}
            disabled={isGenerating}
            className="w-full flex items-center justify-center gap-2 bg-void hover:bg-void-card border border-void-border text-xs text-gray-300 hover:text-white py-2.5 rounded-xl transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? "animate-spin" : ""}`} />
            <span>Regenerate Copy</span>
          </button>
        </div>

        {/* COLUMN 2: Live Copy Generator (5 Cols) */}
        <div className="lg:col-span-5 rounded-2xl bg-void-card border border-void-border p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-void-border pb-3">
            <span className="text-xs font-mono uppercase tracking-wider font-bold text-gray-300">
              Generated Markdown Copy
            </span>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 text-xs font-semibold text-white bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg transition-all"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? "Copied!" : "1-Click Copy"}</span>
            </button>
          </div>

          {isGenerating ? (
            <div className="h-64 flex flex-col items-center justify-center gap-2 text-gray-400">
              <Loader2 className="w-6 h-6 animate-spin text-horizon-indigo" />
              <span className="text-xs font-mono">Synthesizing playbook rules via Gemini...</span>
            </div>
          ) : (
            <div className="space-y-4">
              {prData?.headline && (
                <div className="p-3.5 rounded-xl bg-void border border-void-border text-xs font-bold text-white leading-relaxed">
                  "{prData.headline}"
                </div>
              )}

              <textarea
                readOnly
                rows={12}
                value={prData?.body_markdown || ""}
                className="w-full bg-void rounded-xl border border-void-border p-3.5 text-xs text-gray-200 font-sans leading-relaxed resize-none focus:outline-none"
              />

              {prData?.suggested_tags && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {prData.suggested_tags.map((tag: string) => (
                    <span key={tag} className="text-[11px] font-mono text-horizon-indigo bg-horizon-indigo/10 px-2 py-0.5 rounded border border-horizon-indigo/20">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* COLUMN 3: 1200x630 Launch Card & Boost Studio (4 Cols) */}
        <div className="lg:col-span-4 rounded-2xl bg-void-card border border-void-border p-5 space-y-6">
          <div>
            <span className="text-xs font-mono uppercase text-gray-400 font-bold block mb-3">
              1200×630 OpenGraph Launch Card
            </span>

            <div className="w-full aspect-[1200/630] rounded-xl bg-editorial-paper border border-white/20 p-4 shadow-lg text-editorial-ink flex flex-col justify-between overflow-hidden relative">
              <div className="flex items-center justify-between border-b border-gray-200 pb-1.5">
                <span className="text-[9px] font-mono font-bold text-gray-600 uppercase">
                  STUDENT RADAR // {dossier?.domain_persona?.replace("_", " ").toUpperCase() || "TECH BUILDER"}
                </span>
                <span className="text-[9px] font-bold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                  VERIFIED
                </span>
              </div>

              <div className="my-2">
                <h4 className="text-sm font-bold font-serif line-clamp-1 text-gray-900">
                  {dossier?.title || "Autonomous Drone Swarm"}
                </h4>
                <p className="text-[10px] text-gray-600 line-clamp-2 mt-0.5 leading-snug">
                  {dossier?.tagline || "Decentralized mesh coordination protocol."}
                </p>
              </div>

              <div className="flex items-center justify-between pt-1 border-t border-gray-100 text-[9px] font-mono text-gray-500">
                <span>studentradar.dev/p/{dossier?.slug?.substring(0, 15) || "slug"}</span>
                <span className="text-indigo-600 font-bold">1200×630 HD</span>
              </div>
            </div>
          </div>

          {/* Visibility Credits Loop Studio */}
          <div className="p-4 rounded-xl bg-void border border-void-border space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Zap className="w-4 h-4 text-horizon-violet fill-horizon-violet" />
                Campus Spotlight Boost
              </span>
              <span className="text-xs font-mono text-horizon-violet font-bold">-20⚡</span>
            </div>
            <p className="text-[11px] text-gray-400 leading-relaxed">
              Feature your Proof-of-Work Dossier at the top of the campus discovery directory for 72 hours.
            </p>

            {boostSuccess ? (
              <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-400 text-center font-bold">
                ✓ Dossier Boosted on Campus Feed!
              </div>
            ) : (
              <button
                onClick={handleBoost}
                disabled={isBoosting}
                className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-horizon-violet to-horizon-indigo hover:from-purple-600 hover:to-indigo-600 text-white text-xs font-semibold py-2.5 rounded-xl shadow-md transition-all active:scale-95"
              >
                {isBoosting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <span>Boost Launch (-20⚡)</span>
                  </>
                )}
              </button>
            )}
          </div>

          {/* Earn Credits Callout */}
          <div className="p-3.5 rounded-xl bg-void/50 border border-void-border text-[11px] text-gray-400 space-y-1">
            <span className="font-semibold text-gray-300 block">Need more credits?</span>
            <p>• Submit a verified 3-field peer review: <strong>+10⚡</strong></p>
            <p>• Peer signup via your WhatsApp invite: <strong>+15⚡</strong></p>
          </div>

        </div>

      </div>
    </>
  );
}

export default function PRStudioPage() {
  return (
    <div className="relative min-h-screen bg-void text-white selection:bg-horizon-indigo selection:text-white">
      {/* Top Luminous Ambient Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[350px] bg-horizon-radial pointer-events-none -z-10" />

      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
        <Suspense fallback={<div className="text-xs font-mono text-gray-500 py-10 text-center">Loading PR Studio...</div>}>
          <PRStudioContent />
        </Suspense>
      </main>
    </div>
  );
}
