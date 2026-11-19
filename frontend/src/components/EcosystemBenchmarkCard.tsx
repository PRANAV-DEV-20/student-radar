"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import {
  ArrowRight,
  BookOpen,
  Check,
  Compass,
  ExternalLink,
  GitFork,
  Layers3,
  Loader2,
  RefreshCw,
  Rocket,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

interface EcosystemBenchmarkCardProps {
  dossier: any;
  isLoading?: boolean;
  isRefreshing?: boolean;
  onRefresh?: () => void;
  onAddUpgrades?: (selected: any[]) => void | Promise<void>;
}

const difficultyClasses = (difficulty: string) =>
  difficulty === "Weekend Sprint"
    ? "bg-emerald-400/10 text-emerald-300 border-emerald-400/30"
    : "bg-amber-400/10 text-amber-300 border-amber-400/30";

export function EcosystemBenchmarkCard({
  dossier,
  isLoading = false,
  isRefreshing = false,
  onRefresh,
  onAddUpgrades,
}: EcosystemBenchmarkCardProps) {
  const router = useRouter();
  const benchmark = dossier?.benchmark_analysis || {};
  const similarProjects: any[] = benchmark.similar_projects || [];
  const upgrades: any[] = benchmark.advanced_upgrades || [];
  const persistedTitles = useMemo(
    () => new Set<string>((benchmark.selected_upgrades || []).map((item: any) => String(item.upgrade_title || ""))),
    [benchmark.selected_upgrades],
  );

  const [selectedTitles, setSelectedTitles] = useState<Set<string>>(
    () => new Set(persistedTitles),
  );
  const [isSavingRoadmap, setIsSavingRoadmap] = useState(false);
  const [savedNotice, setSavedNotice] = useState(false);

  useEffect(() => {
    setSelectedTitles(new Set(persistedTitles));
  }, [persistedTitles]);

  const toggleUpgrade = (title: string) => {
    setSavedNotice(false);
    setSelectedTitles((previous) => {
      const next = new Set(previous);
      if (next.has(title)) next.delete(title);
      else next.add(title);
      return next;
    });
  };

  const selectedUpgrades = upgrades.filter((item) => selectedTitles.has(item.upgrade_title));
  const hasBenchmark = similarProjects.length > 0 || upgrades.length > 0;

  const handleDraftHook = (project: any) => {
    if (typeof window === "undefined") return;
    sessionStorage.setItem(
      "target_market_signal",
      JSON.stringify({
        source: project.source_platform || "ecosystem benchmark",
        title: project.name,
        summary: project.what_they_built || "Peer project found in the ecosystem benchmark.",
        url: project.url,
        student_differentiator: project.student_differentiator || "",
        benchmark_hook: "Draft Differentiation Hook",
      }),
    );
    if (dossier) {
      sessionStorage.setItem("current_dossier", JSON.stringify(dossier));
    }
    router.push("/pr-studio");
  };

  const handleAddUpgrades = async () => {
    if (!selectedUpgrades.length || !onAddUpgrades) return;
    setIsSavingRoadmap(true);
    try {
      await onAddUpgrades(selectedUpgrades);
      setSavedNotice(true);
      window.setTimeout(() => setSavedNotice(false), 2500);
    } finally {
      setIsSavingRoadmap(false);
    }
  };

  const generatedAt = benchmark.generated_at
    ? new Date(benchmark.generated_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 380, damping: 30 }}
      className="rounded-2xl bg-void-card border border-void-border p-5 sm:p-6 shadow-xl relative overflow-hidden"
    >
      <div className="absolute -top-16 -left-12 w-56 h-56 bg-horizon-violet/10 rounded-full blur-3xl -z-10" />
      <div className="absolute -bottom-20 -right-16 w-56 h-56 bg-horizon-indigo/10 rounded-full blur-3xl -z-10" />

      <div className="flex items-start justify-between gap-3 border-b border-void-border pb-3 mb-4">
        <div className="flex items-start gap-2.5 min-w-0">
          <div className="p-1.5 rounded-lg bg-horizon-indigo/15 border border-horizon-indigo/25 shrink-0">
            <Compass className="w-4 h-4 text-horizon-indigo" />
          </div>
          <div className="min-w-0">
            <h2 className="text-xs font-mono uppercase tracking-wider font-bold text-gray-100 leading-snug">
              // Ecosystem Benchmark &amp; Evolution Roadmap
            </h2>
            <p className="text-[10px] text-gray-500 font-mono mt-1">
              Peer evidence → production-grade next steps
            </p>
          </div>
        </div>
        {onRefresh && (
          <motion.button
            whileTap={{ scale: 0.94 }}
            onClick={onRefresh}
            disabled={isRefreshing}
            title="Re-run ecosystem scan"
            aria-label="Re-run ecosystem scan"
            className="p-1.5 rounded-lg bg-void hover:bg-white/5 border border-void-border text-gray-400 hover:text-white transition-colors disabled:opacity-50 shrink-0"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
          </motion.button>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-5 animate-pulse" aria-label="Loading ecosystem benchmark">
          <div>
            <div className="h-2.5 w-40 rounded bg-white/10 mb-3" />
            {[0, 1].map((key) => (
              <div key={key} className="rounded-xl bg-void border border-void-border p-3.5 mb-2">
                <div className="h-2.5 w-2/3 rounded bg-white/10 mb-2" />
                <div className="h-2 w-full rounded bg-white/5" />
              </div>
            ))}
          </div>
          <div>
            <div className="h-2.5 w-48 rounded bg-white/10 mb-3" />
            {[0, 1, 2].map((key) => (
              <div key={key} className="rounded-xl bg-void border border-void-border p-3.5 mb-2">
                <div className="h-2.5 w-3/4 rounded bg-white/10 mb-2" />
                <div className="h-2 w-full rounded bg-white/5" />
              </div>
            ))}
          </div>
        </div>
      ) : !hasBenchmark ? (
        <div className="rounded-xl bg-void border border-dashed border-void-border p-5 text-center">
          <div className="w-9 h-9 mx-auto mb-3 rounded-xl bg-horizon-indigo/10 flex items-center justify-center">
            <GitFork className="w-4 h-4 text-horizon-indigo" />
          </div>
          <p className="text-xs font-semibold text-gray-200 mb-1">No benchmark grounded yet</p>
          <p className="text-[11px] text-gray-500 leading-relaxed mb-3">
            Run a scan to compare this project with real peer builds and production-grade systems.
            Nothing is shown until a source link is verified.
          </p>
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-white bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >
              {isRefreshing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
              Run ecosystem scan
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-5">
          {/* Tier 1 — peer & indie projects */}
          <section>
            <div className="flex items-center justify-between gap-2 mb-2.5">
              <div className="flex items-center gap-2">
                <GitFork className="w-3.5 h-3.5 text-horizon-indigo" />
                <h3 className="text-[11px] font-mono font-bold uppercase tracking-wider text-gray-300">
                  Similar Projects
                </h3>
              </div>
              <span className="text-[9px] font-mono text-gray-500 uppercase tracking-wide">
                Peer / Indie Level
              </span>
            </div>

            <div className="space-y-2">
              {similarProjects.slice(0, 3).map((project: any, index: number) => (
                <motion.div
                  key={`${project.url}-${index}`}
                  whileHover={{ y: -2 }}
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  className="group rounded-xl bg-void border border-void-border hover:border-horizon-indigo/40 p-3.5 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-white leading-snug line-clamp-2">
                        {project.name}
                      </p>
                      <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                        <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-void-card border border-void-border text-gray-400">
                          {project.source_platform}
                        </span>
                        <span className="inline-flex items-center gap-1 text-[9px] font-mono text-emerald-400/80">
                          <ShieldCheck className="w-3 h-3" /> real link
                        </span>
                      </div>
                    </div>
                    <a
                      href={project.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Open ${project.name} source`}
                      className="p-1 rounded-md text-gray-500 group-hover:text-horizon-indigo transition-colors shrink-0"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>

                  {project.what_they_built && (
                    <p className="text-[11px] text-gray-400 leading-relaxed mt-2.5 line-clamp-3">
                      {project.what_they_built}
                    </p>
                  )}

                  {project.student_differentiator && (
                    <div className="mt-2.5 rounded-lg bg-horizon-indigo/10 border-l-2 border-horizon-indigo px-2.5 py-2">
                      <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-indigo-300">
                        Your Edge
                      </span>
                      <p className="text-[11px] text-gray-300 leading-relaxed mt-0.5">
                        {project.student_differentiator}
                      </p>
                    </div>
                  )}
                </motion.div>
              ))}
            </div>

            {similarProjects.length > 0 && (
              <button
                onClick={() => handleDraftHook(similarProjects[0])}
                className="mt-2.5 inline-flex items-center gap-1.5 text-[11px] font-semibold text-horizon-indigo hover:text-indigo-300 transition-colors"
              >
                Compare &amp; Draft Differentiation Hook
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </section>

          {/* Tier 2 — advanced/next-stage upgrades */}
          <section className="pt-4 border-t border-void-border">
            <div className="flex items-center justify-between gap-2 mb-2.5">
              <div className="flex items-center gap-2">
                <Rocket className="w-3.5 h-3.5 text-horizon-violet" />
                <h3 className="text-[11px] font-mono font-bold uppercase tracking-wider text-gray-300">
                  Advanced Solutions &amp; Next-Stage Upgrades
                </h3>
              </div>
              <span className="text-[9px] font-mono text-gray-500 uppercase tracking-wide">
                Startup / Research
              </span>
            </div>

            <div className="space-y-2">
              {upgrades.slice(0, 3).map((upgrade: any, index: number) => {
                const isSelected = selectedTitles.has(upgrade.upgrade_title);
                return (
                  <motion.div
                    key={`${upgrade.reference_url}-${index}`}
                    role="button"
                    tabIndex={0}
                    aria-pressed={isSelected}
                    onClick={() => toggleUpgrade(upgrade.upgrade_title)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        toggleUpgrade(upgrade.upgrade_title);
                      }
                    }}
                    animate={{ scale: isSelected ? 1.01 : 1 }}
                    whileTap={{ scale: 0.99 }}
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    className={`w-full text-left rounded-xl p-3.5 border transition-colors cursor-pointer ${
                      isSelected
                        ? "bg-horizon-violet/10 border-horizon-violet/50 shadow-[0_0_20px_rgba(168,85,247,0.12)]"
                        : "bg-void border-void-border hover:border-horizon-violet/35"
                    }`}
                  >
                    <div className="flex items-start gap-2.5">
                      <span
                        className={`w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-mono font-bold shrink-0 ${
                          isSelected
                            ? "bg-horizon-violet text-white"
                            : "bg-void-card border border-void-border text-gray-500"
                        }`}
                      >
                        {isSelected ? <Check className="w-3.5 h-3.5" /> : index + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold text-white leading-snug">
                          {upgrade.upgrade_title}
                        </p>
                        <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                          <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${difficultyClasses(upgrade.difficulty)}`}>
                            {upgrade.difficulty}
                          </span>
                          {upgrade.inspired_by && (
                            <span className="inline-flex items-center gap-1 text-[9px] font-mono text-gray-500 truncate max-w-[160px]">
                              <BookOpen className="w-3 h-3 shrink-0" />
                              {upgrade.inspired_by}
                            </span>
                          )}
                        </div>
                        {upgrade.architectural_impact && (
                          <p className="text-[11px] text-gray-400 leading-relaxed mt-2 line-clamp-3">
                            {upgrade.architectural_impact}
                          </p>
                        )}
                        <a
                          href={upgrade.reference_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(event) => event.stopPropagation()}
                          className="inline-flex items-center gap-1 text-[10px] font-mono text-horizon-indigo hover:text-indigo-300 mt-2 transition-colors"
                        >
                          Read source <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>

            <div className="sticky bottom-3 z-10 mt-3 -mx-1 px-1 py-1 bg-gradient-to-t from-void-card via-void-card/95 to-transparent">
              <motion.button
                whileTap={{ scale: 0.98 }}
                onClick={handleAddUpgrades}
                disabled={!selectedUpgrades.length || !onAddUpgrades || isSavingRoadmap}
                className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-horizon-indigo to-horizon-violet hover:from-indigo-600 hover:to-purple-600 text-white text-[11px] font-semibold px-4 py-2.5 rounded-xl shadow-md transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isSavingRoadmap ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Layers3 className="w-3.5 h-3.5" />
                )}
                <span>
                  {savedNotice
                    ? "Roadmap updated ✓"
                    : selectedUpgrades.length
                      ? `Add ${selectedUpgrades.length} Selected Upgrade${selectedUpgrades.length > 1 ? "s" : ""} to My Roadmap`
                      : "Select upgrades to build your roadmap"}
                </span>
                {!savedNotice && selectedUpgrades.length > 0 && <ArrowRight className="w-3.5 h-3.5" />}
              </motion.button>
            </div>
          </section>

          <div className="rounded-lg bg-void/60 border border-void-border px-3 py-2.5">
            <div className="flex items-start gap-2">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-[10px] text-gray-400 leading-relaxed">
                  Grounded in real open links — no fabricated metrics, startups, or posts.
                  {generatedAt ? ` Scanned ${generatedAt}.` : ""}
                </p>
                {benchmark.query_basis && (
                  <details className="mt-1.5">
                    <summary className="text-[9px] font-mono text-gray-500 cursor-pointer hover:text-gray-300">
                      Search basis
                    </summary>
                    <p className="text-[9px] font-mono text-gray-600 leading-relaxed mt-1 break-words">
                      {benchmark.query_basis}
                    </p>
                  </details>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {hasBenchmark && !isLoading && (
        <div className="flex items-center justify-center gap-1.5 mt-3 text-[9px] font-mono text-gray-600 uppercase tracking-widest">
          <Sparkles className="w-3 h-3" /> Exa + Gemini grounded mentor layer
        </div>
      )}
    </motion.div>
  );
}
