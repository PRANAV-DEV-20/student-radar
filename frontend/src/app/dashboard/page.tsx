"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { FlowStepper } from "@/components/FlowStepper";
import { DetailDrawer, DrawerRow, DrawerSection } from "@/components/DetailDrawer";
import { DOMAIN_PERSONAS } from "@/lib/constants";
import { getDomainPack } from "@/lib/domainPacks";
import { FLOW_STAGES, getFlowState, getNextFlowStage, flowProgress, markFlowStageDone, type FlowStageId } from "@/lib/flow";
import { buildProjectDNA } from "@/lib/projectDna";
import { api } from "@/lib/api";
import {
  FileText,
  Compass,
  Globe2,
  Clock,
  ArrowRight,
  Copy,
  Check,
  ExternalLink,
  Sparkles,
  Calendar,
  AlertTriangle,
  Users,
  Eye,
  ListChecks,
  ChevronRight,
  Mail,
  RefreshCw,
} from "lucide-react";

function readLocalDossier(): any | null {
  if (typeof window === "undefined") return null;
  for (const storage of [sessionStorage, localStorage]) {
    for (const key of ["current_dossier", "student_radar_last_dossier"]) {
      try {
        const raw = storage.getItem(key);
        if (!raw) continue;
        const parsed = JSON.parse(raw);
        if (parsed?.title && parsed?.slug) return parsed;
      } catch {
        // Ignore malformed cached records.
      }
    }
  }
  return null;
}

type DrawerKind =
  | "dossier"
  | "metric"
  | "stage"
  | "deadline"
  | "signal"
  | "builder"
  | "opportunity";

interface DrawerState {
  kind: DrawerKind;
  title: string;
  eyebrow: string;
  subtitle?: string;
  payload?: any;
}

export default function DashboardPage() {
  const router = useRouter();
  const [persona, setPersona] = useState("tech_builder");
  const [currentDossier, setCurrentDossier] = useState<any>(null);
  const [dossiers, setDossiers] = useState<any[]>([]);
  const [briefing, setBriefing] = useState<any>(null);
  const [market, setMarket] = useState<any>(null);
  const [reach, setReach] = useState<any>(null);
  const [copiedSlug, setCopiedSlug] = useState<string | null>(null);
  const [isRerunning, setIsRerunning] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [flowState, setFlowState] = useState<ReturnType<typeof getFlowState>>({});
  const [drawer, setDrawer] = useState<DrawerState | null>(null);

  const refreshFlow = () => setFlowState(getFlowState());

  useEffect(() => {
    let cancelled = false;

    const stored = readLocalDossier();
    if (stored) {
      setCurrentDossier(stored);
      if (stored.domain_persona) setPersona(stored.domain_persona);
    }

    api.listDossiers()
      .then((listed) => {
        if (cancelled) return;
        const byKey = new Map<string, any>();
        for (const item of [stored, ...(Array.isArray(listed) ? listed : [])]) {
          if (!item) continue;
          const key = item.id || item.slug;
          if (!key) continue;
          const existing = byKey.get(key);
          if (!existing || (item.id && !existing.id)) byKey.set(key, item);
        }
        const items = [...byKey.values()];
        const canonical = stored
          ? items.find((item) => item.id === stored.id || item.slug === stored.slug)
          : null;
        if (canonical) setCurrentDossier(canonical);
        setDossiers(items);
      })
      .catch((error) => {
        console.error("Dashboard dossier load error:", error);
        if (stored) setDossiers([stored]);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    refreshFlow();
    window.addEventListener("student-radar:flow", refreshFlow);
    return () => {
      cancelled = true;
      window.removeEventListener("student-radar:flow", refreshFlow);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    api.getRadarBriefing(persona)
      .then((data) => !cancelled && setBriefing(data))
      .catch((error) => console.error("Dashboard radar error:", error));
    return () => { cancelled = true; };
  }, [persona]);

  useEffect(() => {
    let cancelled = false;
    const keywords = [
      ...(currentDossier?.tech_stack || []),
      ...(currentDossier?.tags || []),
      ...(currentDossier?.key_metrics || []).map((metric: any) => metric.label),
    ].filter(Boolean).slice(0, 5);
    const personaLabel = DOMAIN_PERSONAS.find((item) => item.id === persona)?.label || "student projects";
    api.getMarketIntelligence(keywords.length ? keywords : [personaLabel], persona, currentDossier?.title)
      .then((data) => !cancelled && setMarket(data))
      .catch((error) => console.error("Dashboard market pulse error:", error));
    return () => { cancelled = true; };
  }, [persona, currentDossier]);

  useEffect(() => {
    let cancelled = false;
    api.getPRReach()
      .then((data) => !cancelled && setReach(data))
      .catch((error) => console.error("Dashboard PR reach error:", error));
    return () => { cancelled = true; };
  }, []);

  const allOpportunities: any[] = briefing?.all_opportunities || [];
  const urgentDeadlines: any[] = briefing?.urgent_deadlines || [];
  const signals: any[] = Array.from(
    new Map((market?.signals || []).map((signal: any) => [signal.url, signal])).values(),
  );
  const similarBuilders: any[] = market?.similar_builders || [];
  const personaLabel = DOMAIN_PERSONAS.find((item) => item.id === persona)?.shortLabel || persona;
  const pack = getDomainPack(persona);
  const dna = useMemo(() => (currentDossier ? buildProjectDNA(currentDossier) : null), [currentDossier]);
  const nextStage = getNextFlowStage(flowState);

  const openPRStudio = (dossier?: any) => {
    if (dossier && typeof window !== "undefined") {
      sessionStorage.setItem("current_dossier", JSON.stringify(dossier));
    }
    router.push("/pr-studio");
  };

  const tailorPitch = (opportunity: any) => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("target_opportunity", JSON.stringify(opportunity));
      if (currentDossier) sessionStorage.setItem("current_dossier", JSON.stringify(currentDossier));
    }
    setDrawer(null);
    router.push("/pr-studio");
  };

  const draftHook = (signal: any) => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("target_market_signal", JSON.stringify(signal));
      if (currentDossier) sessionStorage.setItem("current_dossier", JSON.stringify(currentDossier));
    }
    setDrawer(null);
    router.push("/pr-studio");
  };

  const copyShareLink = async (slug: string) => {
    const link = `${window.location.origin}/p/${slug}`;
    try {
      await navigator.clipboard.writeText(link);
      setCopiedSlug(slug);
      setTimeout(() => setCopiedSlug(null), 2000);
    } catch {
      window.open(link, "_blank", "noopener,noreferrer");
    }
  };

  const rerunAnalysis = async () => {
    if (!currentDossier || isRerunning) {
      if (!currentDossier) router.push("/dossier");
      return;
    }
    setIsRerunning(true);
    try {
      const proof = [
        ...(currentDossier.key_metrics || []).map((m: any) => `${m.label}: ${m.value}`),
        ...(currentDossier.proof_signals || []),
      ].join("; ");
      const rawContent = [
        currentDossier.title,
        currentDossier.problem_statement,
        currentDossier.solution_breakdown?.architecture || currentDossier.solution_architecture,
        proof,
        "Re-analysis requested after project updates. Keep all claims grounded and flag unsupported ones.",
      ].filter(Boolean).join("\n").slice(0, 10000);
      const updated = await api.ingestArtifact({
        input_type: "idea",
        raw_content: rawContent,
        domain_persona: currentDossier.domain_persona || persona,
      });
      if (updated?.title) {
        setCurrentDossier(updated);
        if (typeof window !== "undefined") {
          sessionStorage.setItem("current_dossier", JSON.stringify(updated));
          localStorage.setItem("student_radar_last_dossier", JSON.stringify(updated));
        }
      }
      markFlowStageDone("repeat", "Dossier re-analysed with current evidence");
      setFlowState(getFlowState());
      setDrawer(null);
      router.push("/dossier");
    } catch (error) {
      console.error("Re-analysis failed:", error);
    } finally {
      setIsRerunning(false);
    }
  };

  const hudCards = [
    { key: "dossiers", label: "Active Dossiers", value: dossiers.length, icon: FileText, detail: "Open the project passport and DNA" },
    { key: "opportunities", label: "Matched Events", value: allOpportunities.length, icon: Compass, detail: `filtered for ${personaLabel}` },
    { key: "signals", label: "External Signals", value: signals.length, icon: Globe2, detail: `sources: ${pack.radarSources.slice(0, 2).join(", ")}` },
    { key: "deadlines", label: "Urgent Deadlines", value: urgentDeadlines.length, icon: Clock, detail: "closing within 72 hours" },
    { key: "reach", label: "PR Reach", value: reach?.total ?? 0, icon: Eye, detail: "tracked dossier + asset events" },
  ];

  const openMetric = (key: string, label: string) => {
    if (key === "dossiers") {
      setDrawer({ kind: "metric", eyebrow: "ACTIVE DOSSIERS", title: label, subtitle: "Every proof-of-work page you have generated.", payload: dossiers });
    } else if (key === "opportunities") {
      setDrawer({ kind: "metric", eyebrow: "MATCHED EVENTS", title: label, subtitle: `Curated for ${pack.label}.`, payload: allOpportunities });
    } else if (key === "signals") {
      setDrawer({ kind: "metric", eyebrow: "EXTERNAL SIGNALS", title: label, subtitle: "Source-linked items — verification links are not live posts.", payload: signals });
    } else if (key === "deadlines") {
      setDrawer({ kind: "metric", eyebrow: "URGENT DEADLINES", title: label, subtitle: "Closing in the next 72 hours.", payload: urgentDeadlines });
    } else {
      setDrawer({ kind: "metric", eyebrow: "PR REACH", title: label, subtitle: reach?.latest_event_at ? `Latest event ${new Date(reach.latest_event_at).toLocaleString()}` : "No tracked engagement yet.", payload: { reach } });
    }
  };

  // ---------- Drawer body ----------
  const renderDrawerBody = () => {
    if (!drawer) return null;

    if (drawer.kind === "stage") {
      const stage = FLOW_STAGES.find((item) => item.id === drawer.payload?.id) || nextStage;
      const isDone = Boolean(flowState[stage.id]);
      return (
        <>
          <p className="text-sm leading-relaxed text-gray-300">{stage.description}</p>
          <DrawerSection title={`Deliverables · ${isDone ? "Done" : "To do"}`}>
            {stage.deliverables.map((item) => (
              <DrawerRow key={item} title={item} action={<ChevronRight className="h-3 w-3 text-gray-500" />} />
            ))}
          </DrawerSection>
          {stage.id === "understand" && dna && (
            <DrawerSection title="Current readiness">
              <DrawerRow title={`${dna.readiness.total}/100`} detail={dna.readiness.axes.map((a) => `${a.label} ${a.score}`).join(" · ")} />
            </DrawerSection>
          )}
          {stage.id === "connect" && (
            <DrawerSection title="Outreach safety">
              <DrawerRow title="One recipient per draft" detail="Never bulk send. Drafts open in your own mail app." />
              <DrawerRow title="Daily cap" detail="Maximum 5 drafts per day with day 4 and day 10 follow-ups." />
            </DrawerSection>
          )}
          {stage.id === "repeat" && (
            <DrawerSection title="Re-analysis">
              <DrawerRow title="Uses your latest dossier" detail={currentDossier?.title || "No dossier loaded yet"} />
              <DrawerRow title="Adds no invented claims" detail="New evidence is scored and unsupported claims stay flagged." />
            </DrawerSection>
          )}
        </>
      );
    }

    if (drawer.kind === "dossier") {
      const item = drawer.payload;
      const itemDna = buildProjectDNA(item);
      return (
        <>
          <div className="rounded-xl border border-void-border bg-void p-4">
            <p className="text-sm font-bold text-white">{item.title}</p>
            <p className="mt-1 text-xs leading-relaxed text-gray-400">{item.tagline || item.problem_statement}</p>
            <div className="mt-3 flex flex-wrap gap-2 font-mono text-[10px] text-gray-400">
              <span className="rounded-full border border-void-border px-2 py-0.5">{item.stage || "Prototype"}</span>
              <span className="rounded-full border border-void-border px-2 py-0.5">{itemDna.domainPack.shortLabel}</span>
              <span className="rounded-full border border-void-border px-2 py-0.5">Readiness {itemDna.readiness.total}</span>
            </div>
          </div>
          <DrawerSection title="Project DNA">
            {itemDna.fields.map((field) => (
              <DrawerRow key={field.label} title={field.label} detail={field.value} />
            ))}
          </DrawerSection>
          <DrawerSection title="Stage-aware next step">
            <DrawerRow title={itemDna.stage} detail={itemDna.stageAdvice} />
          </DrawerSection>
          {itemDna.claims.length > 0 && (
            <DrawerSection title="Claims to verify">
              {itemDna.claims.slice(0, 3).map((claim, index) => (
                <DrawerRow key={`${claim.text}-${index}`} title={`“${claim.text}”`} detail={claim.fix} />
              ))}
            </DrawerSection>
          )}
          <DrawerSection title="Source-linked records">
            {itemDna.evidence.length
              ? itemDna.evidence.slice(0, 5).map((source, index) => (
                  <DrawerRow
                    key={`${source.url}-${index}`}
                    title={source.title}
                    detail={`${source.kind} · ${source.platform}`}
                    action={
                      <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-horizon-indigo">
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    }
                  />
                ))
              : <DrawerRow title="No external records yet" detail="Refresh the reality check in the Dossier workspace." />}
          </DrawerSection>
        </>
      );
    }

    if (drawer.kind === "metric") {
      const items = Array.isArray(drawer.payload) ? drawer.payload : [];
      const reachData = drawer.payload?.reach;
      if (reachData) {
        return (
          <DrawerSection title="Engagement breakdown">
            <DrawerRow title="Total events" detail={String(reachData.total ?? 0)} />
            {Object.entries(reachData.by_event_type || {}).map(([key, value]) => (
              <DrawerRow key={key} title={key.replace(/_/g, " ")} detail={String(value)} />
            ))}
            <DrawerRow title="Dossier views" detail={String(reachData.dossier_views ?? 0)} />
            <DrawerRow title="Asset views" detail={String(reachData.asset_views ?? 0)} />
          </DrawerSection>
        );
      }
      if (!items.length) {
        return <p className="text-xs text-gray-500">Nothing here yet. Generate a dossier or run a radar scan to populate this view.</p>;
      }
      return (
        <div className="space-y-2">
          {items.slice(0, 12).map((item: any, index: number) => (
            <DrawerRow
              key={`${item.id || item.slug || item.url || index}`}
              title={item.title || item.name || `${item.source || "item"} signal`}
              detail={item.summary || item.description || item.tagline || item.host_organization || item.detail || ""}
              action={
                item.url || item.canonical_source_url ? (
                  <a href={item.url || item.canonical_source_url} target="_blank" rel="noopener noreferrer" className="text-horizon-indigo">
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                ) : undefined
              }
            />
          ))}
        </div>
      );
    }

    if (drawer.kind === "deadline" || drawer.kind === "opportunity") {
      const item = drawer.payload;
      return (
        <>
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
            <p className="text-sm font-bold text-white">{item.title}</p>
            <p className="mt-1 text-xs text-gray-400">{item.description}</p>
            <div className="mt-3 flex flex-wrap gap-2 font-mono text-[10px] text-amber-200">
              <span>{item.category || "opportunity"}</span>
              {item.hours_remaining ? <span>{item.hours_remaining}h left</span> : null}
              {item.reward_pool ? <span>{item.reward_pool}</span> : null}
            </div>
          </div>
          <DrawerSection title="Why this matches">
            <DrawerRow title="Domain" detail={pack.label} />
            <DrawerRow title="Reason" detail={item.why_you_match || `Accepted in ${pack.opportunityTypes.join(", ").toLowerCase()}.`} />
            {item.canonical_source_url && (
              <DrawerRow
                title="Official source"
                detail="Open the organiser's page to confirm the deadline and eligibility."
                action={<a href={item.canonical_source_url} target="_blank" rel="noopener noreferrer" className="text-horizon-indigo"><ExternalLink className="h-3.5 w-3.5" /></a>}
              />
            )}
          </DrawerSection>
        </>
      );
    }

    if (drawer.kind === "signal") {
      const item = drawer.payload;
      return (
        <>
          <p className="text-sm leading-relaxed text-gray-300">{item.summary}</p>
          <DrawerSection title="Source">
            <DrawerRow title={String(item.source || "source").replace(/_/g, " ")} detail={item.url} />
            <DrawerRow title="Freshness" detail={item.is_live ? "Live result" : "Verification link — not a live post"} />
          </DrawerSection>
        </>
      );
    }

    if (drawer.kind === "builder") {
      const item = drawer.payload;
      return (
        <>
          <p className="text-sm font-bold text-white">{item.name}</p>
          <p className="mt-2 text-xs leading-relaxed text-gray-400">{item.outreach_hook}</p>
          <DrawerSection title="Outreach angle">
            <DrawerRow title="Suggested ask" detail={`Ask for ${pack.outreachTargets[0]?.toLowerCase() || "feedback"}-level feedback on your project.`} />
          </DrawerSection>
        </>
      );
    }

    return null;
  };

  const drawerFooter = () => {
    if (!drawer) return null;
    if (drawer.kind === "dossier") {
      const item = drawer.payload;
      const slug = item.slug || "project";
      return (
        <div className="flex flex-wrap gap-2">
          <Link href={`/p/${slug}`} className="flex items-center gap-1 rounded-lg border border-void-border px-3 py-1.5 text-[11px] text-gray-300"><ExternalLink className="h-3 w-3" /> Passport</Link>
          <button onClick={() => openPRStudio(item)} className="flex items-center gap-1 rounded-lg bg-horizon-indigo px-3 py-1.5 text-[11px] font-semibold text-white"><Sparkles className="h-3 w-3" /> PR Studio</button>
          <button onClick={() => copyShareLink(slug)} className="flex items-center gap-1 rounded-lg border border-void-border px-3 py-1.5 text-[11px] text-gray-300"><Copy className="h-3 w-3" /> Copy link</button>
        </div>
      );
    }
    if (drawer.kind === "deadline" || drawer.kind === "opportunity") {
      return <button onClick={() => tailorPitch(drawer.payload)} className="flex items-center gap-1.5 rounded-lg bg-horizon-indigo px-3 py-2 text-[11px] font-semibold text-white">Tailor pitch in PR Studio <ArrowRight className="h-3 w-3" /></button>;
    }
    if (drawer.kind === "signal") {
      return <button onClick={() => draftHook(drawer.payload)} className="flex items-center gap-1.5 rounded-lg bg-horizon-indigo px-3 py-2 text-[11px] font-semibold text-white">Draft PR hook <ArrowRight className="h-3 w-3" /></button>;
    }
    if (drawer.kind === "builder") {
      return (
        <button onClick={() => draftHook({ id: drawer.payload?.id, source: drawer.payload?.platform, title: drawer.payload?.name, summary: drawer.payload?.outreach_hook, url: drawer.payload?.profile_url, is_live: drawer.payload?.is_live })} className="flex items-center gap-1.5 rounded-lg bg-horizon-indigo px-3 py-2 text-[11px] font-semibold text-white"><Mail className="h-3 w-3" /> Draft outreach</button>
      );
    }
    if (drawer.kind === "stage") {
      const stage = FLOW_STAGES.find((s) => s.id === drawer.payload?.id) || nextStage;
      if (stage.id === "repeat") {
        return (
          <button
            onClick={rerunAnalysis}
            disabled={isRerunning}
            className="flex items-center gap-1.5 rounded-lg bg-horizon-indigo px-3 py-2 text-[11px] font-semibold text-white disabled:opacity-60"
          >
            {isRerunning ? <RefreshCw className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
            {isRerunning ? "Re-analysing…" : "Re-analyse project"}
          </button>
        );
      }
      return <Link href={stage.route} className="flex items-center gap-1.5 rounded-lg bg-horizon-indigo px-3 py-2 text-[11px] font-semibold text-white">Open {stage.label} <ArrowRight className="h-3 w-3" /></Link>;
    }
    return <button onClick={() => setDrawer(null)} className="text-[11px] text-gray-400 hover:text-white">Close</button>;
  };

  return (
    <div className="relative min-h-screen bg-void text-white selection:bg-horizon-indigo selection:text-white">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 h-[350px] w-[1200px] bg-horizon-radial pointer-events-none -z-10" />
      <Navbar currentPersona={persona} onPersonaChange={setPersona} />

      <main className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <span className="font-mono text-xs uppercase tracking-widest text-horizon-indigo">// STUDENT BUILDER COMMAND CENTER</span>
            <span className="font-mono text-xs text-gray-500">[{personaLabel} pack]</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Turn any project into visibility and opportunities in 10 minutes.
          </h1>
          <p className="mt-2 max-w-3xl text-xs text-gray-400">
            Click any card, metric or stage to see the underlying work, sources and next action. Counts come from your saved dossiers, the current radar snapshot and tracked engagement — nothing is invented.
          </p>
        </div>

        {/* The guided flow */}
        <section className="space-y-3 rounded-2xl border border-void-border bg-void-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 text-sm font-bold text-white"><ListChecks className="h-4 w-4 text-horizon-indigo" /> Your visibility flow</h2>
            <span className="font-mono text-[11px] text-gray-400">{flowProgress(flowState)}% complete</span>
          </div>
          <FlowStepper state={flowState} />
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-horizon-indigo/25 bg-horizon-indigo/5 p-3">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-widest text-horizon-indigo">Next best action</p>
              <p className="mt-1 text-xs font-semibold text-white">{nextStage.label} — {nextStage.tagline}</p>
              <p className="mt-1 max-w-2xl text-[11px] text-gray-400">{nextStage.description}</p>
            </div>
            <button
              onClick={() => setDrawer({ kind: "stage", eyebrow: "FLOW TASK", title: nextStage.label, subtitle: nextStage.tagline, payload: nextStage })}
              className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-horizon-indigo to-horizon-violet px-3 py-2 text-[11px] font-semibold text-white"
            >
              See tasks <ArrowRight className="h-3 w-3" />
            </button>
          </div>
        </section>

        {/* Telemetry HUD — clickable */}
        <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {hudCards.map((card) => {
            const Icon = card.icon;
            return (
              <button
                key={card.key}
                onClick={() => openMetric(card.key, card.label)}
                className="flex items-start gap-3 rounded-2xl border border-void-border bg-void-card p-4 text-left transition-all hover:border-horizon-indigo/50"
              >
                <div className="rounded-xl bg-horizon-indigo/10 p-2 text-horizon-indigo"><Icon className="h-4 w-4" /></div>
                <div className="min-w-0">
                  <span className="block font-mono text-2xl font-bold text-white">{isLoading ? "—" : card.value}</span>
                  <span className="mt-0.5 block text-xs text-gray-300">{card.label}</span>
                  <span className="block truncate text-[10px] text-gray-500">{card.detail}</span>
                </div>
              </button>
            );
          })}
        </section>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Project dossiers */}
          <section className="space-y-4 rounded-2xl border border-void-border bg-void-card p-5 lg:col-span-7">
            <div className="flex items-center justify-between gap-2 border-b border-void-border pb-3">
              <h2 className="flex items-center gap-2 text-sm font-bold text-white"><FileText className="h-4 w-4 text-horizon-indigo" /> Project Dossiers</h2>
              <Link href="/dossier" className="text-xs font-semibold text-horizon-indigo hover:text-indigo-400">New dossier →</Link>
            </div>

            {isLoading ? (
              <p className="text-xs text-gray-500">Loading saved dossiers…</p>
            ) : dossiers.length === 0 ? (
              <div className="rounded-xl border border-void-border bg-void p-4 text-xs text-gray-400">
                No dossiers saved yet. Paste a repo, PDF or idea in the Studio to generate your first proof-of-work page.
              </div>
            ) : (
              dossiers.slice(0, 4).map((dossier) => {
                const slug = dossier.slug || "project";
                const itemDna = buildProjectDNA(dossier);
                return (
                  <div key={dossier.id || slug} className="space-y-3 rounded-xl border border-void-border bg-void p-4">
                    <button
                      onClick={() => setDrawer({ kind: "dossier", eyebrow: "PROJECT WORK", title: dossier.title, subtitle: dossier.tagline, payload: dossier })}
                      className="flex w-full items-start justify-between gap-3 text-left"
                    >
                      <div className="min-w-0">
                        <h3 className="text-sm font-bold text-white">{dossier.title}</h3>
                        <p className="mt-1 line-clamp-2 text-xs text-gray-400">{dossier.tagline}</p>
                      </div>
                      <ChevronRight className="h-4 w-4 shrink-0 text-horizon-indigo" />
                    </button>
                    <div className="flex flex-wrap gap-1.5 font-mono text-[10px] text-gray-400">
                      <span className="rounded-full border border-void-border px-2 py-0.5">{dossier.stage || "Prototype"}</span>
                      <span className="rounded-full border border-void-border px-2 py-0.5">DNA {itemDna.fields.filter((f) => f.basis !== "missing").length}/9</span>
                      <span className="rounded-full border border-void-border px-2 py-0.5">Ready {itemDna.readiness.total}</span>
                      {itemDna.claims.length > 0 && <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-amber-300">{itemDna.claims.length} claims</span>}
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs">
                      <button onClick={() => setDrawer({ kind: "dossier", eyebrow: "PROJECT WORK", title: dossier.title, subtitle: dossier.tagline, payload: dossier })} className="flex items-center gap-1 rounded-lg border border-void-border px-3 py-1.5 text-gray-300 hover:text-white"><Eye className="h-3 w-3" /> View work</button>
                      <button onClick={() => openPRStudio(dossier)} className="flex items-center gap-1 rounded-lg bg-gradient-to-r from-horizon-indigo to-horizon-violet px-3 py-1.5 font-semibold text-white"><Sparkles className="h-3 w-3" /> PR Studio</button>
                      <button onClick={() => copyShareLink(slug)} className="flex items-center gap-1 rounded-lg border border-void-border px-3 py-1.5 text-gray-300 hover:text-white">{copiedSlug === slug ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />} {copiedSlug === slug ? "Copied" : "Copy link"}</button>
                      <Link href={`/dossier?slug=${slug}`} className="flex items-center gap-1 rounded-lg border border-void-border px-3 py-1.5 text-gray-300 hover:text-white"><FileText className="h-3 w-3" /> Edit</Link>
                    </div>
                  </div>
                );
              })
            )}
          </section>

          {/* Urgent deadlines */}
          <section className="space-y-4 rounded-2xl border border-void-border bg-void-card p-5 lg:col-span-5">
            <div className="flex items-center justify-between gap-2 border-b border-void-border pb-3">
              <h2 className="flex items-center gap-2 text-sm font-bold text-white"><Clock className="h-4 w-4 text-amber-400" /> Urgent Deadlines</h2>
              <Link href="/radar" className="text-xs text-horizon-indigo hover:text-indigo-400">Open Radar →</Link>
            </div>
            {urgentDeadlines.length === 0 ? (
              <p className="text-xs text-gray-500">Nothing closing in the next 72 hours. Check back after the next radar crawl.</p>
            ) : (
              urgentDeadlines.slice(0, 3).map((deadline: any) => (
                <button
                  key={deadline.id}
                  onClick={() => setDrawer({ kind: "deadline", eyebrow: "OPPORTUNITY", title: deadline.title, subtitle: `${deadline.category || "opportunity"} · ${deadline.hours_remaining}h left`, payload: deadline })}
                  className="w-full space-y-3 rounded-xl border border-amber-500/20 bg-void p-4 text-left transition-all hover:border-amber-500/50"
                >
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="text-xs font-bold leading-snug text-white">{deadline.title}</h3>
                    <span className="shrink-0 font-mono text-[10px] text-amber-300">{deadline.hours_remaining}h</span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] font-mono uppercase text-gray-500">
                    <span>{deadline.category || "opportunity"}</span>
                    <span className="flex items-center gap-1 text-horizon-indigo">View details <ChevronRight className="h-3 w-3" /></span>
                  </div>
                </button>
              ))
            )}
          </section>
        </div>

        {/* Cross-platform pulse */}
        <section className="space-y-4 rounded-2xl border border-void-border bg-void-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-void-border pb-3">
            <h2 className="flex items-center gap-2 text-sm font-bold text-white"><Globe2 className="h-4 w-4 text-horizon-violet" /> Cross-Platform Idea Visibility</h2>
            <span className="font-mono text-[10px] text-gray-500">{market ? `Interest: ${market.trend_direction}` : "scanning…"}</span>
          </div>
          {market && <p className="max-w-4xl text-xs text-gray-400">{market.summary}</p>}

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:col-span-8">
              {signals.slice(0, 4).map((signal: any) => (
                <button
                  key={signal.id}
                  onClick={() => setDrawer({ kind: "signal", eyebrow: String(signal.source || "signal").replace(/_/g, " "), title: signal.title, subtitle: signal.is_live ? "Live result" : "Verification link", payload: signal })}
                  className="space-y-2 rounded-xl border border-void-border bg-void p-4 text-left hover:border-horizon-indigo/40"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] uppercase text-gray-400">{String(signal.source || "source").replace("_", " ")}</span>
                    {!signal.is_live && <span className="font-mono text-[9px] text-amber-400/80">verification link</span>}
                  </div>
                  <h3 className="line-clamp-2 text-xs font-bold leading-snug text-white">{signal.title}</h3>
                  <span className="flex items-center gap-1 text-[11px] text-horizon-indigo">Open details <ChevronRight className="h-3 w-3" /></span>
                </button>
              ))}
              {signals.length === 0 && <p className="text-xs text-gray-500">No signals yet. Run a live radar scan.</p>}
            </div>

            <div className="space-y-3 rounded-xl border border-void-border bg-void p-4 lg:col-span-4">
              <h3 className="flex items-center gap-2 text-xs font-bold text-white"><Users className="h-3.5 w-3.5 text-horizon-violet" /> Similar Minds</h3>
              {similarBuilders.length === 0 ? (
                <p className="text-[11px] text-gray-500">Adjacent builders appear here when a search provider is connected. Until then, use the source links to explore each community directly.</p>
              ) : (
                similarBuilders.slice(0, 3).map((builder: any) => (
                  <button
                    key={builder.id}
                    onClick={() => setDrawer({ kind: "builder", eyebrow: "COLLABORATOR", title: builder.name, payload: builder })}
                    className="block w-full border-t border-void-border pt-3 text-left first:border-0 first:pt-0"
                  >
                    <p className="line-clamp-2 text-[11px] font-semibold text-gray-200">{builder.name}</p>
                    <p className="mt-1 line-clamp-2 text-[10px] text-gray-500">{builder.outreach_hook}</p>
                    <span className="mt-1 flex items-center gap-1 text-[11px] text-horizon-indigo">Draft outreach <ChevronRight className="h-3 w-3" /></span>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <Calendar className="h-3.5 w-3.5 text-gray-500" />
            <Link href="/radar" className="text-xs text-gray-400 hover:text-white">See the full unified radar feed →</Link>
          </div>
        </section>

        {/* Domain pack reference */}
        <section className="rounded-2xl border border-void-border bg-void-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-void-border pb-3">
            <h2 className="flex items-center gap-2 text-sm font-bold text-white"><AlertTriangle className="h-4 w-4 text-amber-400" /> {pack.shortLabel} pack rules</h2>
            <span className="font-mono text-[10px] text-gray-500">one engine · three packs</span>
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
            {[
              { title: "Visibility channels", items: pack.channels },
              { title: "Opportunity types", items: pack.opportunityTypes },
              { title: "Retrieval sources", items: pack.radarSources },
            ].map((group) => (
              <div key={group.title}>
                <p className="font-mono text-[10px] uppercase tracking-widest text-gray-500">{group.title}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {group.items.map((item) => <span key={item} className="rounded-full border border-void-border px-2 py-0.5 text-[10px] text-gray-300">{item}</span>)}
                </div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-amber-200/90">Key risk: {pack.keyRisk}</p>
        </section>
      </main>

      <DetailDrawer
        isOpen={Boolean(drawer)}
        onClose={() => setDrawer(null)}
        eyebrow={drawer?.eyebrow}
        title={drawer?.title || "Details"}
        subtitle={drawer?.subtitle}
        footer={drawerFooter()}
      >
        {renderDrawerBody()}
      </DetailDrawer>
    </div>
  );
}
