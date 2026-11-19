"use client";

import React, { Suspense, useMemo, useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { PrePublishChecklist } from "@/components/PrePublishChecklist";
import { OutreachComposer } from "@/components/OutreachComposer";
import { FlowStepper } from "@/components/FlowStepper";
import { api, generatePRLocalFallback } from "@/lib/api";
import { getDomainPack } from "@/lib/domainPacks";
import { buildProjectDNA } from "@/lib/projectDna";
import { getFlowState, markFlowStageDone } from "@/lib/flow";
import { Copy, Check, Sparkles, Zap, RefreshCw, Send, Loader2, ExternalLink, Mail } from "lucide-react";

type PlaybookType =
  | "linkedin"
  | "instagram_reel"
  | "instagram_carousel"
  | "x_thread"
  | "show_hn"
  | "reel_script"
  | "cold_pitch"
  | "policy_brief"
  | "plain_explainer";

type Tone = "academic" | "high_octane" | "executive" | "founder" | "storyteller" | "humble_beginner";

const FORMATS: Array<{ id: PlaybookType; label: string; hint: string }> = [
  { id: "linkedin", label: "LinkedIn post", hint: "Hook + story + ask" },
  { id: "instagram_carousel", label: "Instagram carousel", hint: "Caption + 7 slides" },
  { id: "x_thread", label: "X thread", hint: "7–9 numbered posts" },
  { id: "reel_script", label: "Reel / short video", hint: "Timed 6-beat script" },
  { id: "show_hn", label: "Show HN / Reddit", hint: "Technical, no marketing" },
  { id: "cold_pitch", label: "Cold email pitch", hint: "Short, one ask" },
  { id: "policy_brief", label: "Policy brief", hint: "Cited, not legal advice" },
  { id: "plain_explainer", label: "Plain-language note", hint: "Methods + limitations" },
  { id: "instagram_reel", label: "Reel storyboard", hint: "Legacy format" },
];

const TONES: Array<{ id: Tone; label: string }> = [
  { id: "academic", label: "Academic" },
  { id: "founder", label: "Founder" },
  { id: "storyteller", label: "Storyteller" },
  { id: "humble_beginner", label: "Humble beginner" },
  { id: "high_octane", label: "High octane" },
  { id: "executive", label: "Executive" },
];

const ANGLES = [
  "The problem story — why this problem matters",
  "The build journey — what we tried and learned",
  "The result / insight — the one thing we found",
  "The call for collaborators — what we need next",
];

function PRStudioContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialTab = searchParams.get("tab");

  const [mode, setMode] = useState<"content" | "outreach">(initialTab === "outreach" ? "outreach" : "content");
  const [dossier, setDossier] = useState<any>(null);
  const [playbookType, setPlaybookType] = useState<PlaybookType>("linkedin");
  const [tone, setTone] = useState<Tone>("academic");
  const [angle, setAngle] = useState(ANGLES[0]);
  const [targetAudience, setTargetAudience] = useState("Peer builders, technical founders, and researchers");
  const [isGenerating, setIsGenerating] = useState(false);
  const [prData, setPrData] = useState<any>(null);
  const [contextLabel, setContextLabel] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);
  const [isBoosting, setIsBoosting] = useState(false);
  const [boostSuccess, setBoostSuccess] = useState(false);
  const [flowState, setFlowState] = useState(getFlowState());

  const pack = useMemo(() => getDomainPack(dossier?.domain_persona || dossier?.domain), [dossier]);
  const dna = useMemo(() => (dossier ? buildProjectDNA(dossier) : null), [dossier]);

  const recommendedFormats: PlaybookType[] =
    pack.key === "biotech"
      ? ["plain_explainer", "instagram_carousel", "linkedin", "x_thread", "reel_script"]
      : pack.key === "law_policy"
        ? ["policy_brief", "linkedin", "x_thread", "instagram_carousel", "reel_script"]
        : ["linkedin", "x_thread", "show_hn", "instagram_carousel", "reel_script"];

  const buildRoadmapContext = (targetDossier: any): string => {
    const selected = targetDossier?.benchmark_analysis?.selected_upgrades || [];
    if (!Array.isArray(selected) || selected.length === 0) return "";
    const lines = selected.slice(0, 3).map((upgrade: any, index: number) =>
      [
        `${index + 1}. ${upgrade.upgrade_title || "Next-stage upgrade"}`,
        upgrade.inspired_by ? `Inspired by ${upgrade.inspired_by}` : "",
        upgrade.reference_url ? `Source: ${upgrade.reference_url}` : "",
        upgrade.architectural_impact || "",
      ].filter(Boolean).join(" — "),
    );
    return ["Building in Public — Version 2.0 Roadmap:", ...lines, "Use only these grounded upgrades; do not invent metrics or links."].join(" ");
  };

  useEffect(() => {
    let context: string | undefined;
    let audience: string | undefined;

    if (typeof window !== "undefined") {
      const marketRaw = sessionStorage.getItem("target_market_signal");
      const oppRaw = sessionStorage.getItem("target_opportunity");
      if (marketRaw) {
        try {
          const signal = JSON.parse(marketRaw);
          context = [
            `Draft a response or PR hook grounded in this external signal from ${signal.source}:`,
            `"${signal.title}" — ${signal.summary}`,
            `Source: ${signal.url}.`,
            "Do not invent quotes, engagement figures, or claims that are not in the signal.",
          ].join(" ");
          audience = `Builders and founders discussing ${signal.title} on ${signal.source}`;
          setContextLabel(`${signal.source}: ${signal.title}`);
          setPlaybookType("cold_pitch");
        } catch {
          // Ignore malformed handoff data.
        }
        sessionStorage.removeItem("target_market_signal");
      } else if (oppRaw) {
        try {
          const opp = JSON.parse(oppRaw);
          context = [`Tailor this pitch to: ${opp.title} hosted by ${opp.host_organization || "the organizer"}.`, opp.description || ""].join(" ");
          audience = `Organizers and peers in the ${opp.category || "event"} community`;
          setContextLabel(opp.title || "Target opportunity");
        } catch {
          // Ignore malformed handoff data.
        }
        sessionStorage.removeItem("target_opportunity");
      }
    }

    const stored = typeof window !== "undefined" ? sessionStorage.getItem("current_dossier") : null;
    const finish = (loaded: any) => {
      if (!loaded?.title) return;
      const derivedPack = getDomainPack(loaded.domain_persona || loaded.domain);
      setDossier(loaded);
      setTone((derivedPack.defaultTone as Tone) || "academic");
      setPlaybookType(
        derivedPack.key === "biotech" ? "plain_explainer" : derivedPack.key === "law_policy" ? "policy_brief" : "linkedin",
      );
      if (buildRoadmapContext(loaded)) {
        setContextLabel((previous) => previous ? `${previous} · Version 2.0 roadmap` : "Building in Public — Version 2.0 Roadmap");
      }
      generateCopy(loaded, undefined, undefined, context, audience);
    };

    if (stored) {
      try { finish(JSON.parse(stored)); }
      catch { api.getDossier("autonomous-drone-swarm-18d39f").then(finish); }
    } else {
      api.getDossier("autonomous-drone-swarm-18d39f").then(finish);
    }
  }, []);

  const generateCopy = async (
    targetDossier: any,
    pType?: PlaybookType,
    pTone?: Tone,
    context?: string,
    audience?: string,
  ) => {
    setIsGenerating(true);
    try {
      const format = pType || playbookType;
      const voice = pTone || tone;
      const effectiveContext = [
        context,
        buildRoadmapContext(targetDossier),
        `Content angle: ${angle}`,
      ].filter(Boolean).join(" ").slice(0, 4000) || undefined;
      const dossierId = targetDossier?.id;
      const isPersistedId = typeof dossierId === "string" &&
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(dossierId);

      if (!isPersistedId) {
        setPrData(generatePRLocalFallback({
          playbook_type: format,
          tone: voice,
          angle,
          target_audience: audience || targetAudience,
          target_opportunity_context: effectiveContext,
        }));
        markFlowStageDone("position", `${format} copy generated locally`);
        return;
      }

      const res = await api.generatePR({
        dossier_id: dossierId,
        playbook_type: format,
        tone: voice,
        target_audience: audience || targetAudience,
        target_opportunity_context: effectiveContext,
        angle,
      });
      setPrData(res);
      markFlowStageDone("position", `${format} copy generated`);
      if (res?.asset_id) api.trackAssetEvent(res.asset_id, "view").catch(() => undefined);
    } catch (error) {
      console.error("PR generation failed:", error);
      setPrData(generatePRLocalFallback({
        playbook_type: pType || playbookType,
        tone: pTone || tone,
        angle,
        target_audience: audience || targetAudience,
      }));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleFormatChange = (next: PlaybookType) => {
    setPlaybookType(next);
    if (dossier) generateCopy(dossier, next, tone);
  };

  const handleToneChange = (next: Tone) => {
    setTone(next);
    if (dossier) generateCopy(dossier, playbookType, next);
  };

  const handleCopy = async () => {
    if (!prData?.body_markdown) return;
    try {
      await navigator.clipboard.writeText(prData.body_markdown);
      if (prData?.asset_id) api.trackAssetEvent(prData.asset_id, "copy").catch(() => undefined);
      setCopied(true);
      markFlowStageDone("publish", `${playbookType} copy ready to publish`);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard may be blocked.
    }
  };

  const copyPassport = async () => {
    const link = `${window.location.origin}/p/${dossier?.slug || "project"}`;
    try {
      await navigator.clipboard.writeText(link);
      setLinkCopied(true);
      markFlowStageDone("publish", "Project passport link copied");
      setTimeout(() => setLinkCopied(false), 2000);
    } catch {
      window.open(link, "_blank", "noopener,noreferrer");
    }
  };

  const handleBoost = async () => {
    if (!dossier?.id) return;
    setIsBoosting(true);
    try {
      await api.boostDossier(dossier.id);
      setBoostSuccess(true);
      markFlowStageDone("track", "Campus spotlight boost activated");
    } catch (error) {
      console.error("Boost failed:", error);
    } finally {
      setIsBoosting(false);
    }
  };

  return (
    <>
      <Navbar />
      <main className="relative min-h-screen bg-void text-white selection:bg-horizon-indigo selection:text-white">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 h-[350px] w-[1200px] bg-horizon-radial pointer-events-none -z-10" />
        <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <span className="font-mono text-xs uppercase tracking-widest text-horizon-indigo">// POSITION · PUBLISH · CONNECT</span>
              <span className="font-mono text-xs text-gray-400">[{pack.shortLabel} pack]</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              One DNA card. Every format. One clear ask.
            </h1>
          </div>

          <FlowStepper state={flowState} />

          <div className="flex flex-wrap gap-2 rounded-2xl border border-void-border bg-void-card p-1.5">
            <button onClick={() => setMode("content")} className={`flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-semibold ${mode === "content" ? "bg-horizon-indigo text-white" : "text-gray-400 hover:text-white"}`}>
              <Sparkles className="h-3.5 w-3.5" /> Content kit & project passport
            </button>
            <button onClick={() => setMode("outreach")} className={`flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-semibold ${mode === "outreach" ? "bg-horizon-indigo text-white" : "text-gray-400 hover:text-white"}`}>
              <Mail className="h-3.5 w-3.5" /> Outreach (one recipient at a time)
            </button>
          </div>

          {mode === "outreach" ? (
            <OutreachComposer dossier={dossier} />
          ) : (
            <>
              {dossier && <PrePublishChecklist dossier={dossier} />}
              {contextLabel && (
                <div className="rounded-2xl border border-horizon-violet/30 bg-horizon-violet/10 p-4 text-xs text-gray-300">
                  <span className="mb-1 block font-mono uppercase text-horizon-violet">Drafting with external context</span>
                  {contextLabel}
                </div>
              )}

              <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
                {/* Configurator */}
                <div className="space-y-6 rounded-2xl border border-void-border bg-void-card p-5 lg:col-span-3">
                  <div>
                    <p className="mb-3 block font-mono text-xs font-bold uppercase text-gray-400">1. Format pack</p>
                    <div className="space-y-2">
                      {FORMATS.map((format) => {
                        const recommended = recommendedFormats.includes(format.id);
                        return (
                          <button
                            key={format.id}
                            onClick={() => handleFormatChange(format.id)}
                            className={`w-full rounded-xl border p-3 text-left transition-all ${
                              playbookType === format.id
                                ? "border-horizon-indigo bg-horizon-indigo/20 text-white"
                                : "border-void-border bg-void text-gray-400 hover:text-white"
                            }`}
                          >
                            <span className="flex items-center justify-between text-xs font-semibold">
                              {format.label}
                              {recommended && <span className="font-mono text-[9px] text-emerald-300">BEST FOR {pack.shortLabel}</span>}
                            </span>
                            <span className="mt-0.5 block text-[10px] text-gray-500">{format.hint}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div>
                    <p className="mb-2 font-mono text-xs font-bold uppercase text-gray-400">2. Angle</p>
                    <select
                      value={angle}
                      onChange={(event) => setAngle(event.target.value)}
                      className="w-full rounded-lg border border-void-border bg-void px-2.5 py-2 text-[11px] text-white focus:border-horizon-indigo focus:outline-none"
                    >
                      {ANGLES.map((item) => <option key={item} value={item}>{item}</option>)}
                    </select>
                  </div>

                  <div>
                    <p className="mb-2 font-mono text-xs font-bold uppercase text-gray-400">3. Tone</p>
                    <div className="grid grid-cols-2 gap-1 rounded-xl border border-void-border bg-void p-1 text-[11px]">
                      {TONES.map((item) => (
                        <button
                          key={item.id}
                          onClick={() => handleToneChange(item.id)}
                          className={`rounded-lg py-1.5 transition-all ${tone === item.id ? "bg-white/10 font-bold text-white" : "text-gray-400"}`}
                        >
                          {item.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p className="mb-1.5 font-mono text-xs font-bold uppercase text-gray-400">4. Audience</p>
                    <input
                      value={targetAudience}
                      onChange={(event) => setTargetAudience(event.target.value)}
                      className="w-full rounded-xl border border-void-border bg-void p-2.5 text-xs text-white focus:border-horizon-indigo focus:outline-none"
                    />
                  </div>

                  <button
                    onClick={() => dossier && generateCopy(dossier)}
                    disabled={isGenerating}
                    className="flex w-full items-center justify-center gap-2 rounded-xl border border-void-border bg-void py-2.5 text-xs text-gray-300 hover:text-white disabled:opacity-50"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${isGenerating ? "animate-spin" : ""}`} /> Regenerate copy
                  </button>
                </div>

                {/* Copy */}
                <div className="space-y-4 rounded-2xl border border-void-border bg-void-card p-6 lg:col-span-5">
                  <div className="flex items-center justify-between border-b border-void-border pb-3">
                    <span className="font-mono text-xs uppercase tracking-wider font-bold text-gray-300">Generated copy</span>
                    <button onClick={handleCopy} className="flex items-center gap-1.5 rounded-lg bg-white/10 px-3 py-1.5 text-xs font-semibold text-white hover:bg-white/20">
                      {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                      {copied ? "Copied!" : "1-click copy"}
                    </button>
                  </div>
                  {isGenerating ? (
                    <div className="flex h-64 flex-col items-center justify-center gap-2 text-gray-400">
                      <Loader2 className="h-6 w-6 animate-spin text-horizon-indigo" />
                      <span className="font-mono text-xs">Applying {pack.shortLabel} format rules…</span>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {prData?.headline && <div className="rounded-xl border border-void-border bg-void p-3.5 text-xs font-bold leading-relaxed text-white">“{prData.headline}”</div>}
                      <textarea readOnly rows={14} value={prData?.body_markdown || ""} className="w-full resize-none rounded-xl border border-void-border bg-void p-3.5 font-sans text-xs leading-relaxed text-gray-200 focus:outline-none" />
                      {prData?.suggested_tags && (
                        <div className="flex flex-wrap gap-1.5">
                          {prData.suggested_tags.map((tag: string) => <span key={tag} className="rounded border border-horizon-indigo/20 bg-horizon-indigo/10 px-2 py-0.5 font-mono text-[11px] text-horizon-indigo">{tag}</span>)}
                        </div>
                      )}
                      {dna && dna.claims.length > 0 && (
                        <div className="rounded-lg border border-amber-500/25 bg-amber-500/5 p-3 text-[11px] text-amber-200">
                          {dna.claims.length} claim(s) still need evidence before publishing. Review them on the Dossier workspace.
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Passport + boost */}
                <div className="space-y-6 rounded-2xl border border-void-border bg-void-card p-5 lg:col-span-4">
                  <div>
                    <p className="mb-3 block font-mono text-xs font-bold uppercase text-gray-400">Project passport (share link)</p>
                    <div className="flex aspect-[1200/630] flex-col justify-between overflow-hidden rounded-xl border border-white/20 bg-editorial-paper p-4 text-editorial-ink shadow-lg">
                      <div className="flex items-center justify-between border-b border-gray-200 pb-1.5">
                        <span className="font-mono text-[9px] font-bold uppercase text-gray-600">STUDENT RADAR // {pack.shortLabel}</span>
                        <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[9px] font-bold text-emerald-600">PASSPORT</span>
                      </div>
                      <div className="my-2">
                        <h4 className="line-clamp-1 font-serif text-sm font-bold text-gray-900">{dossier?.title || "Your project"}</h4>
                        <p className="mt-0.5 line-clamp-2 text-[10px] leading-snug text-gray-600">{dossier?.tagline || "A student-built proof-of-work project."}</p>
                      </div>
                      <div className="flex items-center justify-between border-t border-gray-100 pt-1 font-mono text-[9px] text-gray-500">
                        <span>studentradar.dev/p/{(dossier?.slug || "project").substring(0, 15)}</span>
                        <span className="font-bold text-indigo-600">1200×630 HD</span>
                      </div>
                    </div>
                    <div className="mt-3 flex gap-2">
                      <button onClick={copyPassport} className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-void-border py-2 text-[11px] text-gray-300 hover:text-white">
                        {linkCopied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />} {linkCopied ? "Link copied" : "Copy share link"}
                      </button>
                      {dossier?.slug && (
                        <a href={`/p/${dossier.slug}`} target="_blank" className="flex items-center gap-1 rounded-lg border border-void-border px-3 py-2 text-[11px] text-gray-300 hover:text-white">
                          <ExternalLink className="h-3 w-3" /> Open
                        </a>
                      )}
                    </div>
                  </div>

                  <div className="space-y-3 rounded-xl border border-void-border bg-void p-4">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-xs font-bold text-white"><Zap className="h-4 w-4 fill-horizon-violet text-horizon-violet" /> Campus spotlight</span>
                      <span className="font-mono text-xs font-bold text-horizon-violet">-20⚡</span>
                    </div>
                    <p className="text-[11px] leading-relaxed text-gray-400">Feature your passport in the campus discovery directory for 48 hours.</p>
                    {boostSuccess ? (
                      <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-2.5 text-center text-xs font-bold text-emerald-400">✓ Passport boosted</div>
                    ) : (
                      <button onClick={handleBoost} disabled={isBoosting} className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-horizon-violet to-horizon-indigo py-2.5 text-xs font-semibold text-white disabled:opacity-50">
                        {isBoosting ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Send className="h-3.5 w-3.5" /> Boost launch (-20⚡)</>}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </main>
    </>
  );
}

export default function PRStudioPage() {
  return (
    <Suspense fallback={<div className="py-10 text-center font-mono text-xs text-gray-500">Loading studio…</div>}>
      <PRStudioContent />
    </Suspense>
  );
}
