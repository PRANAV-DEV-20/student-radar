"use client";

import React, { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import "./dossier-v2.css";

import ChatPanel from "@/components/dossier-v2/ChatPanel";
import EvidenceDrawer from "@/components/dossier-v2/EvidenceDrawer";
import ExecutiveBrief from "@/components/dossier-v2/ExecutiveBrief";
import NotConfiguredState, { GenericErrorState } from "@/components/dossier-v2/NotConfiguredState";
import ProgressTimeline, { TimelineEvent, TimelineKind } from "@/components/dossier-v2/ProgressTimeline";
import RankedBoard, { RankedEntry } from "@/components/dossier-v2/RankedBoard";
import RelatedWorkTable from "@/components/dossier-v2/RelatedWorkTable";
import RoadmapChecklist, { RoadmapEntry } from "@/components/dossier-v2/RoadmapChecklist";
import RootInputForm from "@/components/dossier-v2/RunInputForm";
import RunToolbar from "@/components/dossier-v2/RunToolbar";
import SectionCard from "@/components/dossier-v2/SectionCard";
import SectionNav from "@/components/dossier-v2/SectionNav";
import TechStackCards from "@/components/dossier-v2/TechStackCards";
import {
  askDossier,
  asDossierV2Error,
  cellToString,
  ChatResponse,
  deepenSection,
  DossierRun,
  DossierV2Error,
  downloadTextFile,
  exportRunText,
  getRun,
  isRecord,
  patchSection,
  rerunResearch,
  RoadmapItem,
  saveRoadmap,
  SectionItem,
  SECTION_KEYS,
  SECTION_TITLES,
  SectionKey,
  SectionPatchBody,
  sectionContentPayload,
  sectionCount,
  startRun,
  StartRunPayload,
  streamRunEvents,
  terminalStatus,
} from "@/lib/dossierV2Api";

function eventId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function additionId(item: RoadmapItem, index: number): string {
  return `added-${index}-${item.text.replace(/\W/g, "").slice(0, 18)}`;
}

function DossierV2Workspace() {
  const searchParams = useSearchParams();
  const queryRunId = searchParams.get("run_id");

  const [activeRunId, setActiveRunId] = useState<string | null>(queryRunId);
  const [run, setRun] = useState<DossierRun | null>(null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<DossierV2Error | null>(null);
  const [runError, setRunError] = useState("");
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [streamError, setStreamError] = useState(false);
  const [selectedEvidence, setSelectedEvidence] = useState<string | null>(null);
  const [deepeningKey, setDeepeningKey] = useState<SectionKey | null>(null);
  const [deepenWatch, setDeepenWatch] = useState<{
    key: SectionKey;
    before: string;
    startedAt: number;
  } | null>(null);
  const [deepenError, setDeepenError] = useState("");
  const [roadmapAdditions, setRoadmapAdditions] = useState<RoadmapItem[]>([]);
  const [addingRoadmapId, setAddingRoadmapId] = useState<string | null>(null);
  const [doneMap, setDoneMap] = useState<Record<string, boolean>>({});
  const [rerunning, setRerunning] = useState(false);
  const [exporting, setExporting] = useState<"markdown" | "json" | null>(null);
  const [toolbarError, setToolbarError] = useState("");
  const [activeSection, setActiveSection] = useState<SectionKey>("executive_brief");
  const [showForm, setShowForm] = useState(!queryRunId);

  useEffect(() => {
    if (queryRunId && queryRunId !== activeRunId) {
      setActiveRunId(queryRunId);
      setShowForm(false);
    }
  }, [queryRunId, activeRunId]);

  const refreshRun = useCallback(async (id: string): Promise<DossierRun> => {
    const data = await getRun(id);
    setRun(data);
    return data;
  }, []);

  useEffect(() => {
    if (!activeRunId) {
      setRun(null);
      setEvents([]);
      return;
    }

    let cancelled = false;
    let finished = false;
    let source: EventSource | null = null;
    let poll: ReturnType<typeof setInterval> | null = null;

    setShowForm(false);
    setRun(null);
    setEvents([]);
    setRunError("");
    setStreamError(false);
    setRoadmapAdditions([]);
    setDoneMap({});

    const pushEvent = (type: TimelineKind, message: string) => {
      if (cancelled) return;
      setEvents((current) => [
        ...current.slice(-40),
        { id: eventId(type), type, message, at: Date.now() },
      ]);
    };

    const refresh = async (): Promise<void> => {
      try {
        const data = await getRun(activeRunId);
        if (cancelled) return;
        setRun(data);
        if (terminalStatus(data.status)) {
          finished = true;
          source?.close();
          if (poll) clearInterval(poll);
        }
      } catch (err) {
        if (!cancelled) setRunError(asDossierV2Error(err).message);
      }
    };

    const messageFor = (type: string, data: unknown): string => {
      if (!isRecord(data)) return `${type} event`;
      const stage = cellToString(data.stage ?? "");
      const message = cellToString(data.message ?? data.title ?? data.section ?? "");
      return [stage, message].filter(Boolean).join(" · ") || `${type} event`;
    };

    source = streamRunEvents(activeRunId, {
      onEvent: (event) => {
        pushEvent(event.type, messageFor(event.type, event.data));
        if (event.type === "complete") finished = true;
        if (event.type === "error") {
          const detail = isRecord(event.data)
            ? cellToString(event.data.message ?? event.data.error ?? "The run reported an error")
            : "The run reported an error";
          setRunError(detail || "The run reported an error");
        }
        void refresh();
      },
      onError: () => {
        if (cancelled || finished) return;
        setStreamError(true);
        pushEvent("local", "Live stream unavailable — polling the run directly");
      },
    });
    poll = setInterval(() => void refresh(), 2500);
    void refresh();

    return () => {
      cancelled = true;
      source?.close();
      if (poll) clearInterval(poll);
    };
  }, [activeRunId]);

  // Deepen is asynchronous on the server; poll until that section actually changes.
  useEffect(() => {
    if (!deepenWatch || !activeRunId) return;
    let cancelled = false;
    const timer = setInterval(async () => {
      if (Date.now() - deepenWatch.startedAt > 120000) {
        setDeepenWatch(null);
        return;
      }
      try {
        const data = await getRun(activeRunId);
        if (cancelled) return;
        setRun(data);
        if (JSON.stringify(data.sections[deepenWatch.key] || null) !== deepenWatch.before) {
          setDeepenWatch(null);
          setEvents((current) => [
            ...current.slice(-40),
            {
              id: eventId("local"),
              type: "local",
              message: `Deepening complete · ${SECTION_TITLES[deepenWatch.key]}`,
              at: Date.now(),
            },
          ]);
        }
      } catch (err) {
        if (!cancelled) setDeepenError(asDossierV2Error(err).message);
      }
    }, 2000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [deepenWatch, activeRunId]);

  // Keep checklist state in sync with any `done` flags persisted by the API.
  useEffect(() => {
    const items = run?.sections.roadmap?.items || [];
    if (!items.length) return;
    setDoneMap((current) => {
      const next = { ...current };
      items.forEach((item, index) => {
        const id = item.id || `roadmap-${index}`;
        if (item.done !== undefined) next[id] = Boolean(item.done);
        else if (next[id] === undefined) next[id] = false;
      });
      return next;
    });
  }, [run]);

  const sectionAnchorKey = Object.keys(run?.sections || {}).join("|");
  useEffect(() => {
    if (!run) return;
    const nodes = Array.from(document.querySelectorAll<HTMLElement>("[data-dv2-section]"));
    if (!nodes.length) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        const key = visible[0]?.target.getAttribute("data-dv2-section");
        if (key && (SECTION_KEYS as readonly string[]).includes(key)) {
          setActiveSection(key as SectionKey);
        }
      },
      { rootMargin: "-110px 0px -65% 0px", threshold: 0 },
    );
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [run?.id, sectionAnchorKey, Boolean(run)]);

  const jumpTo = useCallback((key: SectionKey) => {
    setActiveSection(key);
    document.getElementById(`dv2-section-${key}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const handleStart = async (payload: StartRunPayload) => {
    setStarting(true);
    setStartError(null);
    setToolbarError("");
    try {
      const created = await startRun(payload);
      setActiveRunId(created.run_id);
      setShowForm(false);
    } catch (err) {
      setStartError(asDossierV2Error(err));
    } finally {
      setStarting(false);
    }
  };

  const handleOpenEvidence = useCallback((refId: string) => setSelectedEvidence(refId), []);

  const handleDeepen = async (key: SectionKey) => {
    if (!activeRunId) return;
    setDeepeningKey(key);
    setDeepenError("");
    try {
      await deepenSection(activeRunId, key);
      setDeepenWatch({
        key,
        before: JSON.stringify(run?.sections[key] || null),
        startedAt: Date.now(),
      });
      setEvents((current) => [
        ...current.slice(-40),
        {
          id: eventId("local"),
          type: "local",
          message: `Deepening requested · ${SECTION_TITLES[key]}`,
          at: Date.now(),
        },
      ]);
    } catch (err) {
      setDeepenError(asDossierV2Error(err).message);
    } finally {
      setDeepeningKey(null);
    }
  };

  const handlePatch = async (key: SectionKey, body: SectionPatchBody) => {
    if (!activeRunId) throw new Error("There is no active run to edit.");
    setRun((current) => {
      if (!current || !current.sections[key]) return current;
      return {
        ...current,
        sections: {
          ...current.sections,
          [key]: {
            ...current.sections[key],
            ...(body.content as Partial<DossierRun["sections"][string]>),
            locked: body.locked,
          },
        },
      };
    });
    try {
      await patchSection(activeRunId, key, body);
      await refreshRun(activeRunId);
    } catch (err) {
      await refreshRun(activeRunId).catch(() => undefined);
      throw err;
    }
  };

  const handleAsk = useCallback(
    (question: string): Promise<ChatResponse> => {
      if (!activeRunId) return Promise.reject(new Error("There is no active run to ask about."));
      return askDossier(activeRunId, question);
    },
    [activeRunId],
  );

  const handleRerun = async () => {
    if (!activeRunId) return;
    setRerunning(true);
    setToolbarError("");
    try {
      const created = await rerunResearch(activeRunId);
      setActiveRunId(created.run_id);
      setRun(null);
    } catch (err) {
      setToolbarError(asDossierV2Error(err).message);
    } finally {
      setRerunning(false);
    }
  };

  const handleExport = async (format: "markdown" | "json") => {
    if (!activeRunId) return;
    setExporting(format);
    setToolbarError("");
    try {
      const text = await exportRunText(activeRunId, format);
      downloadTextFile(
        `dossier-v2-${activeRunId}.${format === "json" ? "json" : "md"}`,
        text,
        format === "json" ? "application/json" : "text/markdown",
      );
    } catch (err) {
      setToolbarError(asDossierV2Error(err).message);
    } finally {
      setExporting(null);
    }
  };

  const handleAddToRoadmap = async (entry: RankedEntry) => {
    if (!activeRunId) return;
    setAddingRoadmapId(entry.id);
    const item: RoadmapItem = {
      text: entry.item.text,
      section: entry.source,
      effort: typeof entry.item.effort === "string" ? entry.item.effort : "unknown",
    };
    try {
      const updated = await saveRoadmap(activeRunId, [item]);
      if (isRecord(updated) && "sections" in updated) {
        setRun(updated as unknown as DossierRun);
      } else {
        await refreshRun(activeRunId);
      }
      setRoadmapAdditions((current) =>
        current.some((existing) => existing.text === item.text) ? current : [...current, item],
      );
      setEvents((current) => [
        ...current.slice(-40),
        { id: eventId("local"), type: "local", message: "Added an item to the roadmap", at: Date.now() },
      ]);
    } catch (err) {
      setToolbarError(asDossierV2Error(err).message);
    } finally {
      setAddingRoadmapId(null);
    }
  };

  const roadmapSectionItems = run?.sections.roadmap?.items || [];
  const roadmapEntries = useMemo<RoadmapEntry[]>(() => {
    const base = roadmapSectionItems.map((item, index) => ({
      id: item.id || `roadmap-${index}`,
      text: item.text,
      effort: typeof item.effort === "string" ? item.effort : "unknown",
      section: "roadmap",
      added: false,
    }));
    const additions = roadmapAdditions
      .map((item, index) => ({
        id: additionId(item, index),
        text: item.text,
        effort: typeof item.effort === "string" ? item.effort : "unknown",
        section: item.section,
        added: true,
      }))
      .filter((entry) => !base.some((existing) => existing.text === entry.text));
    return [...base, ...additions];
  }, [roadmapSectionItems, roadmapAdditions]);

  const handleToggleRoadmap = async (entry: RoadmapEntry, done: boolean) => {
    const nextDone = { ...doneMap, [entry.id]: done };
    setDoneMap(nextDone);
    if (!activeRunId || !run?.sections.roadmap) return;

    const mergedItems: SectionItem[] = [
      ...roadmapSectionItems.map((item, index) => ({
        ...item,
        done: Boolean(nextDone[item.id || `roadmap-${index}`]),
      })),
      ...roadmapAdditions.map((item, index) => ({
        id: additionId(item, index),
        label: "recommendation",
        text: item.text,
        evidence: [],
        effort: item.effort,
        done: Boolean(nextDone[additionId(item, index)]),
      })),
    ];

    try {
      await patchSection(activeRunId, "roadmap", {
        content: sectionContentPayload(run.sections.roadmap, { items: mergedItems }),
        locked: Boolean(run.sections.roadmap.locked),
      });
      await refreshRun(activeRunId);
    } catch (err) {
      setDoneMap(doneMap);
      setToolbarError(asDossierV2Error(err).message);
    }
  };

  const rankedEntries = useMemo<RankedEntry[]>(() => {
    const entries: RankedEntry[] = [];
    (["gaps", "challenges_risks"] as const).forEach((key) => {
      const section = run?.sections[key];
      if (!section) return;
      section.items.forEach((item, index) => {
        entries.push({ id: `${key}-${item.id || index}`, item, source: key });
      });
    });
    return entries;
  }, [run]);

  const ideaSummary =
    run?.sections.idea_restated?.summary ||
    run?.sections.executive_brief?.summary ||
    "No idea summary was returned in this run.";

  const counts = sectionCount(run);
  const completed = run?.progress?.completed_sections ?? counts.done;
  const total = run?.progress?.total_sections ?? counts.total;
  const notConfigured = Boolean(startError?.isNotConfigured && !activeRunId);
  const isTerminal = Boolean(run && terminalStatus(run.status));

  const specialChildren = (key: SectionKey): React.ReactNode => {
    if (!run) return null;
    switch (key) {
      case "related_work":
        return (
          <RelatedWorkTable
            section={run.sections.related_work}
            ideaSummary={ideaSummary}
            onOpenEvidence={handleOpenEvidence}
          />
        );
      case "gaps":
      case "challenges_risks":
        return (
          <RankedBoard
            entries={rankedEntries}
            onAdd={handleAddToRoadmap}
            addingId={addingRoadmapId}
            onOpenEvidence={handleOpenEvidence}
          />
        );
      case "tech_stack":
        return <TechStackCards section={run.sections.tech_stack} onOpenEvidence={handleOpenEvidence} />;
      case "roadmap":
        return (
          <RoadmapChecklist
            entries={roadmapEntries}
            doneMap={doneMap}
            onToggle={handleToggleRoadmap}
            onOpenEvidence={handleOpenEvidence}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="dv2-page">
      <div className="dv2-horizon" aria-hidden="true" />
      <div className="dv2-shell">
        <header className="dv2-topbar">
          <Link href="/" className="dv2-back">
            <ArrowLeft size={14} /> Back to studio
          </Link>
          <div className="dv2-brand">
            <p className="dv2-brand-kicker">LaunchPad · research workbench</p>
            <h1>Dossier v2</h1>
            <p className="dv2-brand-sub">An evidence-first brief for a student project, built section by section.</p>
          </div>
        </header>

        {showForm && (
          <RootInputForm onStart={handleStart} isStarting={starting} error={startError} />
        )}

        {notConfigured && (
          <NotConfiguredState
            error={startError as DossierV2Error}
            onRetry={() => {
              setStartError(null);
              setShowForm(true);
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        )}

        {activeRunId && (
          <>
            <RunToolbar
              run={run}
              runId={activeRunId}
              onNewRun={() => {
                setShowForm(true);
                setStartError(null);
              }}
              onRerun={handleRerun}
              rerunning={rerunning}
              onExport={handleExport}
              exporting={exporting}
              error={toolbarError}
            />

            {runError && (
              <GenericErrorState
                message={runError}
                onRetry={() => {
                  setRunError("");
                  void refreshRun(activeRunId).catch((err) => setRunError(asDossierV2Error(err).message));
                }}
              />
            )}

            {!run ? (
              <div className="dv2-paper dv2-loading">
                <span className="dv2-spinner" /> Loading run {activeRunId}…
              </div>
            ) : (
              <div className="dv2-workspace">
                <SectionNav
                  sections={run.sections || {}}
                  activeKey={activeSection}
                  onSelect={jumpTo}
                />

                <main className="dv2-main">
                  <div
                    id="dv2-section-executive_brief"
                    data-dv2-section="executive_brief"
                    className="dv2-brief-anchor"
                  >
                    <ExecutiveBrief
                      section={run.sections.executive_brief}
                      onOpenEvidence={handleOpenEvidence}
                      onJumpToQuestions={() => jumpTo("open_questions_evidence")}
                    />
                  </div>

                  <ProgressTimeline
                    status={run.status}
                    stage={run.progress?.stage || ""}
                    message={run.progress?.message || ""}
                    completed={completed}
                    total={total}
                    events={events}
                    streamError={streamError}
                  />

                  {isTerminal && run.status.toLowerCase().includes("fail") && (
                    <div className="dv2-partial-note" role="status">
                      This run ended with status <strong>{run.status}</strong>. Only the sections actually written are shown;
                      missing sections are marked, not filled in.
                    </div>
                  )}

                  {deepenError && <div className="dv2-inline-error" role="alert">{deepenError}</div>}

                  {SECTION_KEYS.filter((key) => key !== "executive_brief").map((key) => (
                    <SectionCard
                      key={key}
                      sectionKey={key}
                      section={run.sections[key]}
                      onOpenEvidence={handleOpenEvidence}
                      onDeepen={handleDeepen}
                      deepening={deepeningKey === key || deepenWatch?.key === key}
                      onPatch={handlePatch}
                      hideItems={key === "roadmap" && Boolean(run.sections.roadmap?.items?.length)}
                      hideTables={key === "related_work" || key === "tech_stack"}
                    >
                      {specialChildren(key)}
                    </SectionCard>
                  ))}
                </main>

                <ChatPanel
                  onAsk={handleAsk}
                  onOpenEvidence={handleOpenEvidence}
                  disabled={!activeRunId}
                />
              </div>
            )}
          </>
        )}
      </div>

      <EvidenceDrawer
        open={Boolean(selectedEvidence)}
        refId={selectedEvidence}
        evidence={run?.evidence || []}
        onClose={() => setSelectedEvidence(null)}
      />
    </div>
  );
}

export default function DossierV2Page() {
  return (
    <Suspense fallback={<div className="dv2-boot">Preparing the dossier workbench…</div>}>
      <DossierV2Workspace />
    </Suspense>
  );
}
