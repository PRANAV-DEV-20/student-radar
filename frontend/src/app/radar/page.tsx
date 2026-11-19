"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { DOMAIN_PERSONAS } from "@/lib/constants";
import { api } from "@/lib/api";
import { downloadCalendarEvent } from "@/lib/ics";
import {
  Compass,
  Clock,
  Calendar,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  ExternalLink,
  MessageSquare,
  Filter,
  Globe2,
  TrendingUp,
  Search,
  MapPin,
  ShieldCheck,
  AlertCircle,
} from "lucide-react";

const IDEA_STORAGE_KEY = "student_radar_idea";
const DOSSIER_KEYS = ["current_dossier", "student_radar_last_dossier"];

type Opportunity = {
  id: string;
  title: string;
  category: string;
  canonical_source_url: string;
  host_organization?: string;
  deadline: string;
  event_date?: string;
  description: string;
  tags?: string[];
  domain_personas?: string[];
  location_type?: string;
  city?: string;
  reward_pool?: string;
  decision_metadata?: Record<string, any>;
  match_score?: number;
  why_you_match?: string;
  networking_plan?: {
    target_stakeholders?: string[];
    pitch_angle?: string;
    icebreaker_message?: string;
    conversation_starters?: string[];
    followup_draft?: string;
  };
};

function readCurrentDossier(): any | null {
  if (typeof window === "undefined") return null;
  for (const storage of [sessionStorage, localStorage]) {
    for (const key of DOSSIER_KEYS) {
      const raw = storage.getItem(key);
      if (!raw) continue;
      try {
        const parsed = JSON.parse(raw);
        if (parsed?.title || parsed?.problem_statement) return parsed;
      } catch {
        // Ignore malformed cached records and keep looking.
      }
    }
  }
  return null;
}

function dossierIdea(dossier: any | null): string {
  if (!dossier) return "";
  return String(
    dossier.problem_statement || dossier.tagline || dossier.raw_content || dossier.title || "",
  ).trim();
}

function initialIdea(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(IDEA_STORAGE_KEY) || dossierIdea(readCurrentDossier());
}

function freshnessLabel(item: any): string | null {
  const metadata = item?.decision_metadata || {};
  const deadlineValue = metadata.extracted_deadline || item?.deadline || item?.deadline_at;
  if (deadlineValue) {
    const deadline = new Date(deadlineValue);
    if (!Number.isNaN(deadline.getTime()) && deadline.getTime() > Date.now()) {
      const label = deadline.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      return `Closes ${label}`;
    }
  }
  const publishedValue = item?.published_at || metadata.published_at;
  if (publishedValue) {
    const published = new Date(publishedValue);
    if (!Number.isNaN(published.getTime())) {
      const days = Math.max(0, Math.floor((Date.now() - published.getTime()) / 86400000));
      return days === 0 ? "Posted today" : `Posted ${days}d ago`;
    }
  }
  return null;
}

function sourceLabel(opp: Opportunity): string {
  const metadata = opp.decision_metadata || {};
  if (metadata.source_label) return String(metadata.source_label);
  if (metadata.source) {
    return String(metadata.source)
      .replace(/_/g, " ")
      .replace(/\b\w/g, (letter: string) => letter.toUpperCase());
  }
  try {
    return new URL(opp.canonical_source_url).hostname.replace(/^www\./, "");
  } catch {
    return "Web source";
  }
}

function sourceKindLabel(opp: Opportunity): string | null {
  const kind = String(opp.decision_metadata?.source_kind || "");
  if (kind === "public_api") return "Official API";
  if (kind === "public_page") return "Official listing";
  if (kind === "aggregator") return "Aggregator";
  if (kind === "search_discovery" || kind === "search_result") return "Search discovery";
  return null;
}

function needsVerification(opp: Opportunity): boolean {
  return opp.decision_metadata?.verification === "verify_on_official_page";
}

function categoryMatches(opp: Opportunity, filter: string): boolean {
  if (filter === "all") return true;
  const category = String(opp.category || "").toLowerCase();
  if (filter === "hackathon") {
    return ["hackathon", "hackathons", "build_sprint", "build_sprints"].includes(category);
  }
  if (filter === "event") {
    return ["general_event", "general_events", "conference", "competition"].includes(category);
  }
  return category === filter;
}

function locationLabel(opp: Opportunity): string {
  const metadata = opp.decision_metadata || {};
  if (opp.city) return opp.city;
  if (opp.location_type) {
    return opp.location_type
      .replace(/_/g, " ")
      .replace(/\b\w/g, (letter: string) => letter.toUpperCase());
  }
  return metadata.location || "Remote";
}

function eventDateLabel(opp: Opportunity): string | null {
  if (!opp.event_date) return null;
  const parsed = new Date(opp.event_date);
  if (Number.isNaN(parsed.getTime())) return null;
  return `Starts ${parsed.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
}

const REGISTRATION_DEADLINE_BASES = [
  "submission_period",
  "registration_deadline",
  "application_close_date",
  "explicit_deadline",
  "registration_deadline_in_search_snippet",
];

function isRealRadarRecord(opp: Opportunity): boolean {
  const metadata = opp.decision_metadata || {};
  if (metadata.is_live === false) return false;
  const source = String(metadata.source || "").toLowerCase();
  return !["seed", "demo", "fallback", "mock", "search_link"].includes(source);
}

function isUpcomingRegistration(opp: Opportunity): boolean {
  const deadline = new Date(opp.deadline);
  if (Number.isNaN(deadline.getTime()) || deadline.getTime() <= Date.now()) return false;
  const basis = String(opp.decision_metadata?.deadline_basis || "").trim().toLowerCase();
  return !basis || REGISTRATION_DEADLINE_BASES.includes(basis);
}

export default function RadarPage() {
  const router = useRouter();
  const [persona, setPersona] = useState("tech_builder");
  const [briefing, setBriefing] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [feedFilter, setFeedFilter] = useState<"hackathons" | "news" | "builders">("hackathons");
  const [market, setMarket] = useState<any>(null);
  const [isMarketLoading, setIsMarketLoading] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [idea, setIdea] = useState("");
  const [scanSummary, setScanSummary] = useState<string | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);
  const [sourceHealth, setSourceHealth] = useState<any[]>([]);

  useEffect(() => {
    setIdea(initialIdea());
  }, []);

  useEffect(() => {
    async function loadBriefing() {
      setIsLoading(true);
      try {
        const data = await api.getRadarBriefing(persona);
        setBriefing(data);
      } catch (err) {
        console.error("Radar briefing error:", err);
        // Keep the previous briefing instead of replacing it with invented cards.
      } finally {
        setIsLoading(false);
      }
    }
    loadBriefing();
  }, [persona]);

  useEffect(() => {
    async function loadMarketSignals() {
      setIsMarketLoading(true);
      try {
        const dossier = readCurrentDossier();
        const keywords = [
          ...(dossier?.tech_stack || []),
          ...(dossier?.tags || []),
          ...(dossier?.key_metrics || []).map((metric: any) => metric.label),
        ]
          .filter(Boolean)
          .slice(0, 5);
        const personaLabel =
          DOMAIN_PERSONAS.find((item) => item.id === persona)?.label || "student projects";
        const data = await api.getMarketIntelligence(
          keywords.length ? keywords : [personaLabel],
          persona,
          dossier?.title,
        );
        setMarket(data);
      } catch (err) {
        console.error("Market intelligence error:", err);
      } finally {
        setIsMarketLoading(false);
      }
    }
    loadMarketSignals();
  }, [persona]);

  const strongestPick: Opportunity | null = briefing?.strongest_pick || null;
  const urgentDeadlines = briefing?.urgent_deadlines || [];
  const allOpps: Opportunity[] = (briefing?.all_opportunities || [])
    .filter((opp: Opportunity) => isRealRadarRecord(opp) && isUpcomingRegistration(opp))
    .sort(
      (a: Opportunity, b: Opportunity) =>
        new Date(a.deadline).getTime() - new Date(b.deadline).getTime(),
    );
  const liveSignals = (market?.signals || []).filter(
    (signal: any) => signal.is_live !== false,
  );
  const builderSources = ["x", "reddit", "hackernews", "indiehackers", "builder"];
  const newsSignals = liveSignals.filter(
    (signal: any) =>
      signal.radar_intent === "news" ||
      signal.signal_type === "news" ||
      (signal.radar_intent !== "builders" && !builderSources.includes(signal.source)),
  );
  const builderSignals = liveSignals.filter(
    (signal: any) =>
      signal.radar_intent === "builders" ||
      signal.signal_type === "builder" ||
      builderSources.includes(signal.source),
  );
  const visibleSignals = feedFilter === "news" ? newsSignals : feedFilter === "builders" ? builderSignals : [];
  const visibleOpps = feedFilter === "hackathons" ? allOpps : [];

  const sourceOptions = Array.from(
    allOpps.reduce((map: Map<string, number>, opp: Opportunity) => {
      const label = sourceLabel(opp);
      map.set(label, (map.get(label) || 0) + 1);
      return map;
    }, new Map<string, number>()),
  ).sort((a, b) => b[1] - a[1]);

  const filteredOpps = visibleOpps.filter(
    (opp) =>
      categoryMatches(opp, categoryFilter) &&
      (sourceFilter === "all" || sourceLabel(opp) === sourceFilter),
  );

  const mergeScanSignals = (incoming: any[]) => {
    if (!Array.isArray(incoming)) return;
    setMarket((previous: any) => {
      const merged = new Map<string, any>();
      for (const signal of incoming) merged.set(signal.id, signal);
      for (const signal of previous?.signals || []) {
        if (!merged.has(signal.id)) merged.set(signal.id, signal);
      }
      return {
        ...(previous || {}),
        generated_at: new Date().toISOString(),
        signals: Array.from(merged.values()),
      };
    });
  };

  const handleIdeaScan = async () => {
    const rawIdea = idea.trim() || dossierIdea(readCurrentDossier());
    if (!rawIdea) {
      setScanError("Describe your idea first so the Radar knows what to match.");
      return;
    }

    setIdea(rawIdea);
    if (typeof window !== "undefined") localStorage.setItem(IDEA_STORAGE_KEY, rawIdea);
    setIsScanning(true);
    setScanSummary(null);
    setScanError(null);

    try {
      const result = await api.scanLiveRadar({
        raw_idea: rawIdea,
        persona,
        intents: ["hackathons"],
        language: "en",
        max_age_hours: 0,
      });
      // Only replace the briefing when the backend returned a real one.
      if (result?.briefing?.all_opportunities) setBriefing(result.briefing);
      if (Array.isArray(result?.sources)) setSourceHealth(result.sources);
      mergeScanSignals(result?.signals);

      const stats = result?.stats;
      if (stats) {
        const accepted = stats.accepted || 0;
        setScanSummary(
          `${accepted} source-backed ${accepted === 1 ? "result" : "results"} from ${result?.sources?.length || 0} platforms · ${stats.duration_ms}ms`,
        );
      }
    } catch (err) {
      console.error("Live Radar scan error:", err);
      setScanError("Live scan failed. The last saved Radar feed is still shown — no mock cards were added.");
    } finally {
      setIsScanning(false);
    }
  };

  const handleExportICS = (opp: any) => {
    downloadCalendarEvent({
      title: opp.title,
      description: opp.description,
      deadline: opp.deadline,
      url: opp.canonical_source_url,
      host_organization: opp.host_organization,
    });
  };

  const handleTailorPitch = (opp: any) => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("target_opportunity", JSON.stringify(opp));
    }
    router.push("/pr-studio");
  };

  const handleDraftHook = (signal: any) => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("target_market_signal", JSON.stringify(signal));
    }
    router.push("/pr-studio");
  };

  return (
    <div className="relative min-h-screen bg-void text-white selection:bg-horizon-indigo selection:text-white">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[350px] bg-horizon-radial pointer-events-none -z-10" />
      <Navbar currentPersona={persona} onPersonaChange={setPersona} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10 space-y-8">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-mono uppercase tracking-widest text-horizon-indigo">
                // IDEA → REAL OPPORTUNITIES
              </span>
              <span className="text-xs text-gray-400 font-mono">
                [Devpost · MLH · Unstop · Luma · Grants.gov · Commudle · more]
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              One Radar. Every Signal That Matters.
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-1.5 bg-void-card p-1.5 rounded-2xl border border-void-border">
            {DOMAIN_PERSONAS.map((p) => (
              <button
                key={p.id}
                onClick={() => setPersona(p.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                  persona === p.id
                    ? "bg-white/10 text-white shadow-xs border border-white/20"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                {p.shortLabel}
              </button>
            ))}
          </div>
        </div>

        {/* Idea input → source-backed scan */}
        <section className="rounded-2xl bg-void-card border border-horizon-indigo/30 p-5 sm:p-6">
          <div className="flex flex-col lg:flex-row lg:items-end gap-4">
            <div className="flex-1">
              <label
                htmlFor="radar-idea"
                className="flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-gray-300 mb-2"
              >
                <Search className="w-3.5 h-3.5 text-horizon-indigo" />
                Describe your idea or project
              </label>
              <textarea
                id="radar-idea"
                value={idea}
                onChange={(event) => setIdea(event.target.value)}
                rows={3}
                placeholder="e.g. an offline AI tutor for rural students that works on low-end phones"
                className="w-full rounded-xl bg-void border border-void-border px-4 py-3 text-sm text-white placeholder:text-gray-600 focus:outline-none focus:border-horizon-indigo/60 resize-y"
              />
              <p className="mt-2 text-[11px] text-gray-500">
                The Radar retrieves real records first, then ranks them. No deadlines, prizes, or links are invented.
              </p>
            </div>
            <button
              onClick={handleIdeaScan}
              disabled={isScanning}
              className="shrink-0 flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-horizon-indigo to-horizon-violet hover:from-indigo-600 hover:to-purple-600 text-white text-sm font-semibold px-5 py-3 transition-all active:scale-95 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Sparkles className={`w-4 h-4 ${isScanning ? "animate-pulse" : ""}`} />
              {isScanning ? "Scanning platforms…" : "Find opportunities"}
            </button>
          </div>

          {(scanSummary || scanError) && (
            <div className="mt-4 flex flex-wrap items-center gap-3">
              {scanSummary && (
                <span className="text-[11px] font-mono text-emerald-300">{scanSummary}</span>
              )}
              {scanError && (
                <span className="flex items-center gap-1.5 text-[11px] font-mono text-amber-300">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {scanError}
                </span>
              )}
            </div>
          )}

          {sourceHealth.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2 border-t border-void-border/60 pt-4">
              {sourceHealth.map((source: any) => (
                <span
                  key={source.source}
                  title={source.note || ""}
                  className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-mono ${
                    source.status === "error"
                      ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                      : source.status === "ok"
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                        : "border-void-border bg-void text-gray-400"
                  }`}
                >
                  {source.is_official ? <ShieldCheck className="w-3 h-3" /> : <Globe2 className="w-3 h-3" />}
                  {source.label}
                  <span className="opacity-70">{source.accepted_count}</span>
                </span>
              ))}
            </div>
          )}
        </section>

        {urgentDeadlines.length > 0 && (
          <div className="rounded-2xl bg-amber-500/10 border border-amber-500/30 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-amber-500/20 text-amber-400">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xs font-mono uppercase font-bold text-amber-300 block">
                  URGENT DEADLINES (&lt; 72H REMAINING)
                </span>
                <span className="text-xs text-gray-300">
                  {urgentDeadlines[0]?.title} • Closes in {urgentDeadlines[0]?.hours_remaining} hours
                </span>
              </div>
            </div>
            <button
              onClick={() => handleExportICS(urgentDeadlines[0])}
              className="flex items-center gap-1.5 bg-void hover:bg-void-card border border-amber-500/40 text-amber-300 text-xs font-semibold px-3 py-1.5 rounded-xl transition-all"
            >
              <Calendar className="w-3.5 h-3.5" />
              <span>1-Click .ics</span>
            </button>
          </div>
        )}

        {strongestPick && isRealRadarRecord(strongestPick) && isUpcomingRegistration(strongestPick) && (
          <div className="rounded-2xl bg-void-card border border-horizon-indigo/50 p-6 sm:p-8 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-horizon-indigo/10 rounded-full blur-3xl -z-10" />
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-void-border pb-4 mb-5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="flex items-center gap-1.5 text-xs font-bold font-mono text-horizon-indigo bg-horizon-indigo/10 border border-horizon-indigo/30 px-3 py-1 rounded-full">
                  <Sparkles className="w-3.5 h-3.5" />
                  #1 STRONGEST MATCH // {((strongestPick.match_score || 0) * 100).toFixed(0)}% RELEVANCE
                </span>
                <span className="text-xs font-mono text-gray-400">
                  {sourceLabel(strongestPick)} · {strongestPick.category?.toUpperCase()}
                </span>
                {needsVerification(strongestPick) && (
                  <span className="text-[10px] font-mono text-amber-300">Verify on official page</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleExportICS(strongestPick)}
                  className="flex items-center gap-1.5 bg-void hover:bg-void-card border border-void-border text-xs text-gray-300 px-3 py-1.5 rounded-xl transition-all"
                >
                  <Calendar className="w-3.5 h-3.5 text-horizon-indigo" />
                  <span>.ics Export</span>
                </button>
                <button
                  onClick={() => handleTailorPitch(strongestPick)}
                  className="flex items-center gap-1.5 bg-gradient-to-r from-horizon-indigo to-horizon-violet hover:from-indigo-600 hover:to-purple-600 text-white text-xs font-semibold px-4 py-1.5 rounded-xl shadow-md transition-all active:scale-95"
                >
                  <span>Tailor Application Pitch</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="mb-6">
              <h2 className="text-xl sm:text-2xl font-bold text-white mb-2">{strongestPick.title}</h2>
              <p className="text-xs sm:text-sm text-gray-400 max-w-3xl leading-relaxed">
                {strongestPick.description}
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-void border border-void-border text-xs text-gray-300 mb-6 font-mono">
              <strong className="text-horizon-indigo">Why You Match:</strong> {strongestPick.why_you_match}
            </div>

            {strongestPick.networking_plan && (
              <div className="border border-void-border rounded-xl bg-void/60 overflow-hidden">
                <button
                  onClick={() => setIsDrawerOpen(!isDrawerOpen)}
                  className="w-full flex items-center justify-between p-3.5 text-xs font-semibold text-gray-200 hover:text-white transition-colors"
                >
                  <span className="flex items-center gap-2 font-mono">
                    <MessageSquare className="w-4 h-4 text-horizon-violet" />
                    Expand Automated Networking Plan & Icebreaker
                  </span>
                  {isDrawerOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {isDrawerOpen && (
                  <div className="p-4 border-t border-void-border space-y-4 text-xs">
                    <div>
                      <span className="font-mono text-gray-400 block mb-1">Target Stakeholders to Message:</span>
                      <div className="flex flex-wrap gap-2">
                        {(strongestPick.networking_plan.target_stakeholders || []).map((s: string, idx: number) => (
                          <span key={idx} className="bg-void-card border border-void-border px-2.5 py-1 rounded-md text-gray-300">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <span className="font-mono text-gray-400 block mb-1">Custom Pitch Angle:</span>
                      <p className="text-gray-200">{strongestPick.networking_plan.pitch_angle}</p>
                    </div>
                    <div>
                      <span className="font-mono text-gray-400 block mb-1">Pre-Written Icebreaker Message:</span>
                      <div className="p-3 rounded-lg bg-void border border-void-border text-gray-300 font-sans italic">
                        "{strongestPick.networking_plan.icebreaker_message}"
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {market && !isMarketLoading && (
          <div className="rounded-2xl bg-void-card/60 border border-void-border p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-xl bg-horizon-indigo/10 text-horizon-indigo">
                <TrendingUp className="w-4 h-4" />
              </div>
              <div>
                <span className="text-xs font-mono uppercase font-bold text-gray-200">
                  Market & Competitor Pulse
                </span>
                <p className="text-xs text-gray-400 mt-1 max-w-3xl">{market.summary}</p>
                <p className="text-[10px] font-mono text-gray-500 mt-1">{market.trend_basis}</p>
              </div>
            </div>
            <span className="shrink-0 text-[10px] font-mono uppercase px-2.5 py-1 rounded-full border border-void-border text-gray-400">
              Interest: {market.trend_direction}
            </span>
          </div>
        )}

        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-void-border pb-3">
            <span className="text-xs font-mono uppercase text-gray-400 font-bold">
              Unified Radar Feed ({filteredOpps.length + visibleSignals.length})
            </span>
            <div className="flex flex-wrap items-center gap-1 text-xs">
              {([
                ["hackathons", "Hackathons & Grants"],
                ["news", "Current News & Launches"],
                ["builders", "Similar Builders & Discussions"],
              ] as const).map(([value, label]) => (
                <button
                  key={value}
                  onClick={() => setFeedFilter(value)}
                  className={`px-3 py-1 rounded-lg transition-all ${
                    feedFilter === value ? "bg-white/10 text-white font-bold" : "text-gray-400 hover:text-white"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {feedFilter === "hackathons" && (
            <>
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-1 text-xs">
                  <Filter className="w-3 h-3 text-gray-500 mr-1" />
                  {([
                    ["all", "All"],
                    ["hackathon", "Hackathons"],
                    ["event", "Events"],
                    ["grant", "Grants"],
                    ["fellowship", "Fellowships"],
                  ] as const).map(([value, label]) => (
                    <button
                      key={value}
                      onClick={() => setCategoryFilter(value)}
                      className={`px-3 py-1 rounded-lg ${
                        categoryFilter === value ? "bg-white/10 text-white font-bold" : "text-gray-400"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {sourceOptions.length > 1 && (
                  <div className="flex flex-wrap items-center gap-1 text-[11px]">
                    <span className="font-mono text-gray-500 mr-1">SOURCE</span>
                    {[["all", "All"], ...sourceOptions].map(([value, count]: any) => (
                      <button
                        key={value}
                        onClick={() => setSourceFilter(String(value))}
                        className={`px-2 py-1 rounded-md border ${
                          sourceFilter === String(value)
                            ? "border-horizon-indigo/40 bg-horizon-indigo/10 text-indigo-200"
                            : "border-void-border text-gray-500 hover:text-gray-300"
                        }`}
                      >
                        {value} <span className="opacity-60">{count}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {filteredOpps.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-void-border bg-void-card/40 p-8 text-center">
                  <Compass className="w-6 h-6 text-gray-600 mx-auto mb-2" />
                  <p className="text-sm text-gray-300">No upcoming registrations match this view.</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Only opportunities with a future application, submission, or registration deadline are shown. Try a broader idea or clear the filters.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {filteredOpps.map((opp) => {
                    const matchScore = Number(opp.decision_metadata?.match_score || 0);
                    const matchedTerms = opp.decision_metadata?.matched_terms || [];
                    return (
                      <div
                        key={opp.id}
                        className="rounded-2xl bg-void-card border border-void-border hover:border-horizon-indigo/40 p-5 transition-all flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-void-border/60 pb-2 mb-3">
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-horizon-indigo/10 border border-horizon-indigo/30 text-indigo-200">
                                {sourceLabel(opp)}
                              </span>
                              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-void border border-void-border text-gray-400">
                                {opp.category}
                              </span>
                              {sourceKindLabel(opp) && (
                                <span className="text-[9px] font-mono text-gray-500">{sourceKindLabel(opp)}</span>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              {matchScore > 0 && (
                                <span className="text-[10px] font-mono text-indigo-300">
                                  {Math.round(matchScore * 100)}% match
                                </span>
                              )}
                              {freshnessLabel(opp) && (
                                <span className="text-[9px] font-mono text-indigo-300">{freshnessLabel(opp)}</span>
                              )}
                              {opp.reward_pool && (
                                <span className="text-xs font-mono font-bold text-emerald-400">
                                  {opp.reward_pool}
                                </span>
                              )}
                            </div>
                          </div>

                          <h3 className="text-sm font-bold text-white mb-2 leading-snug">{opp.title}</h3>
                          <p className="text-xs text-gray-400 line-clamp-3 mb-3 leading-relaxed">
                            {opp.description}
                          </p>

                          <div className="flex flex-wrap items-center gap-3 text-[10px] font-mono text-gray-500 mb-3">
                            <span className="flex items-center gap-1">
                              <MapPin className="w-3 h-3" />
                              {locationLabel(opp)}
                            </span>
                            {eventDateLabel(opp) && (
                              <span className="flex items-center gap-1">
                                <Calendar className="w-3 h-3" />
                                {eventDateLabel(opp)}
                              </span>
                            )}
                            {matchedTerms.length > 0 && (
                              <span className="text-indigo-300/80">matched: {matchedTerms.slice(0, 3).join(", ")}</span>
                            )}
                          </div>

                          {needsVerification(opp) && (
                            <p className="text-[10px] font-mono text-amber-300/90 mb-2">
                              Non-official discovery — verify details on the linked page.
                            </p>
                          )}
                        </div>

                        <div className="pt-3 border-t border-void-border/60 flex items-center justify-between gap-2 text-xs">
                          <span className="text-[11px] font-mono text-gray-500 truncate">
                            Host: {opp.host_organization || "Listed source"}
                          </span>
                          <div className="flex items-center gap-2 shrink-0">
                            <button
                              onClick={() => handleExportICS(opp)}
                              className="p-1.5 rounded-lg bg-void hover:bg-void-border text-gray-300"
                              title="Download .ics"
                            >
                              <Calendar className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleTailorPitch(opp)}
                              className="p-1.5 rounded-lg bg-void hover:bg-void-border text-gray-300"
                              title="Draft a tailored pitch"
                            >
                              <MessageSquare className="w-3.5 h-3.5" />
                            </button>
                            <a
                              href={opp.canonical_source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-horizon-indigo hover:text-indigo-400 font-semibold"
                            >
                              <span>{opp.category === "hackathon" ? "Apply" : "View source"}</span>
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}

          {feedFilter !== "hackathons" && (
            <div className="space-y-3">
              <span className="text-[10px] font-mono uppercase text-gray-500">
                {isMarketLoading && !visibleSignals.length
                  ? "Scanning platforms…"
                  : `${visibleSignals.length} ${feedFilter === "news" ? "news & launch" : "builder"} signals`}
              </span>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {visibleSignals.map((signal: any) => (
                  <div
                    key={signal.id}
                    className="rounded-2xl bg-void-card border border-void-border hover:border-horizon-violet/40 p-5 transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 border-b border-void-border/60 pb-2 mb-3">
                        <span className="flex items-center gap-1.5 text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-void border border-void-border text-gray-400">
                          <Globe2 className="w-3 h-3 text-horizon-violet" />
                          {signal.source?.replace("_", " ")}
                        </span>
                        <div className="flex flex-col items-end gap-1">
                          <span className="text-[10px] font-mono text-gray-500">
                            {Math.round((signal.relevance_score || 0) * 100)}% relevance
                          </span>
                          {freshnessLabel(signal) && (
                            <span className="text-[9px] font-mono text-indigo-300">{freshnessLabel(signal)}</span>
                          )}
                        </div>
                      </div>
                      <h3 className="text-sm font-bold text-white mb-2 leading-snug">{signal.title}</h3>
                      <p className="text-xs text-gray-400 line-clamp-3 mb-3 leading-relaxed">{signal.summary}</p>
                    </div>
                    <div className="pt-3 border-t border-void-border/60 flex items-center justify-between gap-2 text-xs">
                      <a
                        href={signal.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-gray-400 hover:text-white"
                      >
                        <span>Open source</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                      <button
                        onClick={() => handleDraftHook(signal)}
                        className="flex items-center gap-1.5 bg-gradient-to-r from-horizon-indigo to-horizon-violet hover:from-indigo-600 hover:to-purple-600 text-white text-xs font-semibold px-3 py-1.5 rounded-xl transition-all active:scale-95"
                      >
                        <span>Draft Response / PR Hook</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
