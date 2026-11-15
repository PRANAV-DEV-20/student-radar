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
  Award,
  Filter
} from "lucide-react";

export default function RadarPage() {
  const router = useRouter();
  const [persona, setPersona] = useState("tech_builder");
  const [briefing, setBriefing] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<"all" | "hackathon" | "grant" | "fellowship">("all");

  useEffect(() => {
    async function loadBriefing() {
      setIsLoading(true);
      try {
        const data = await api.getRadarBriefing(persona);
        setBriefing(data);
      } catch (err) {
        console.error("Radar briefing error:", err);
      } finally {
        setIsLoading(false);
      }
    }
    loadBriefing();
  }, [persona]);

  const strongestPick = briefing?.strongest_pick;
  const urgentDeadlines = briefing?.urgent_deadlines || [];
  const allOpps = briefing?.all_opportunities || [];

  const filteredOpps = allOpps.filter((opp: any) => {
    if (categoryFilter === "all") return true;
    return opp.category?.toLowerCase() === categoryFilter;
  });

  const handleExportICS = (opp: any) => {
    downloadCalendarEvent({
      title: opp.title,
      description: opp.description,
      deadline: opp.deadline,
      url: opp.canonical_source_url,
      host_organization: opp.host_organization
    });
  };

  const handleTailorPitch = (opp: any) => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("target_opportunity", JSON.stringify(opp));
    }
    router.push("/pr-studio");
  };

  return (
    <div className="relative min-h-screen bg-void text-white selection:bg-horizon-indigo selection:text-white">
      {/* Top Ambient Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[350px] bg-horizon-radial pointer-events-none -z-10" />

      <Navbar currentPersona={persona} onPersonaChange={setPersona} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10 space-y-8">
        
        {/* Header & Persona Selector */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-mono uppercase tracking-widest text-horizon-indigo">
                // DAILY OPPORTUNITY RADAR
              </span>
              <span className="text-xs text-gray-400 font-mono">
                [Celery Beat: 5:30 AM Crawl + 6:30 AM Match]
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Curated Event & Hackathon Radar
            </h1>
          </div>

          {/* Persona Mode Switcher Pills */}
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

        {/* Urgent <72h Deadline Ticker */}
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

            <div className="flex items-center gap-2">
              <button
                onClick={() => handleExportICS(urgentDeadlines[0])}
                className="flex items-center gap-1.5 bg-void hover:bg-void-card border border-amber-500/40 text-amber-300 text-xs font-semibold px-3 py-1.5 rounded-xl transition-all"
              >
                <Calendar className="w-3.5 h-3.5" />
                <span>1-Click .ics</span>
              </button>
            </div>
          </div>
        )}

        {/* Strongest Pick Hero Card */}
        {strongestPick && (
          <div className="rounded-2xl bg-void-card border border-horizon-indigo/50 p-6 sm:p-8 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-horizon-indigo/10 rounded-full blur-3xl -z-10" />

            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-void-border pb-4 mb-5">
              <div className="flex items-center gap-2">
                <span className="flex items-center gap-1.5 text-xs font-bold font-mono text-horizon-indigo bg-horizon-indigo/10 border border-horizon-indigo/30 px-3 py-1 rounded-full">
                  <Sparkles className="w-3.5 h-3.5" />
                  #1 STRONGEST MATCH // {(strongestPick.match_score * 100).toFixed(0)}% RELEVANCE
                </span>
                <span className="text-xs font-mono text-gray-400">
                  {strongestPick.category?.toUpperCase()}
                </span>
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

            {/* Opportunity Details */}
            <div className="mb-6">
              <h2 className="text-xl sm:text-2xl font-bold text-white mb-2">
                {strongestPick.title}
              </h2>
              <p className="text-xs sm:text-sm text-gray-400 max-w-3xl leading-relaxed">
                {strongestPick.description}
              </p>
            </div>

            {/* Why You Match Pill */}
            <div className="p-3.5 rounded-xl bg-void border border-void-border text-xs text-gray-300 mb-6 font-mono">
              <strong className="text-horizon-indigo">Why You Match:</strong> {strongestPick.why_you_match}
            </div>

            {/* Expandable Networking Plan Drawer */}
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
                        {strongestPick.networking_plan.target_stakeholders.map((s: string, idx: number) => (
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

        {/* Filter Tabs for All Opportunities */}
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-void-border pb-3">
            <span className="text-xs font-mono uppercase text-gray-400 font-bold">
              All Active Opportunities ({filteredOpps.length})
            </span>

            <div className="flex items-center gap-1 text-xs">
              <button
                onClick={() => setCategoryFilter("all")}
                className={`px-3 py-1 rounded-lg ${categoryFilter === "all" ? "bg-white/10 text-white font-bold" : "text-gray-400"}`}
              >
                All
              </button>
              <button
                onClick={() => setCategoryFilter("hackathon")}
                className={`px-3 py-1 rounded-lg ${categoryFilter === "hackathon" ? "bg-white/10 text-white font-bold" : "text-gray-400"}`}
              >
                Hackathons
              </button>
              <button
                onClick={() => setCategoryFilter("grant")}
                className={`px-3 py-1 rounded-lg ${categoryFilter === "grant" ? "bg-white/10 text-white font-bold" : "text-gray-400"}`}
              >
                Grants
              </button>
              <button
                onClick={() => setCategoryFilter("fellowship")}
                className={`px-3 py-1 rounded-lg ${categoryFilter === "fellowship" ? "bg-white/10 text-white font-bold" : "text-gray-400"}`}
              >
                Fellowships
              </button>
            </div>
          </div>

          {/* Opportunities List */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredOpps.map((opp: any) => (
              <div
                key={opp.id}
                className="rounded-2xl bg-void-card border border-void-border hover:border-horizon-indigo/40 p-5 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between border-b border-void-border/60 pb-2 mb-3">
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-void border border-void-border text-gray-400">
                      {opp.category}
                    </span>
                    {opp.reward_pool && (
                      <span className="text-xs font-mono font-bold text-emerald-400">
                        {opp.reward_pool}
                      </span>
                    )}
                  </div>

                  <h3 className="text-sm font-bold text-white mb-2 leading-snug">
                    {opp.title}
                  </h3>
                  <p className="text-xs text-gray-400 line-clamp-3 mb-4 leading-relaxed">
                    {opp.description}
                  </p>
                </div>

                <div className="pt-3 border-t border-void-border/60 flex items-center justify-between text-xs">
                  <span className="text-[11px] font-mono text-gray-500">
                    Host: {opp.host_organization || "Partner"}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleExportICS(opp)}
                      className="p-1.5 rounded-lg bg-void hover:bg-void-border text-gray-300"
                      title="Download .ics"
                    >
                      <Calendar className="w-3.5 h-3.5" />
                    </button>
                    <a
                      href={opp.canonical_source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-horizon-indigo hover:text-indigo-400 font-semibold"
                    >
                      <span>Apply</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

      </main>

    </div>
  );
}

