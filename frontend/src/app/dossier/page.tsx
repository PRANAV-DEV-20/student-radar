"use client";

import React, { Suspense, useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { DossierCard } from "@/components/DossierCard";
import { IdeaRadarWidget } from "@/components/IdeaRadarWidget";
import { EcosystemBenchmarkCard } from "@/components/EcosystemBenchmarkCard";
import { ContactDiscoveryModal } from "@/components/ContactDiscoveryModal";
import { PeerReviewModal } from "@/components/PeerReviewModal";
import { ProjectDNACard } from "@/components/ProjectDNACard";
import { markFlowStageDone } from "@/lib/flow";
import { api } from "@/lib/api";
import { ArrowLeft, Sparkles, Share2, AlertCircle, RefreshCw, Send, Check } from "lucide-react";
import Link from "next/link";

function DossierContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const slug = searchParams.get("slug");

  const [dossier, setDossier] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState("Contributor");
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);

  // Quick inline refinement
  const [refinePrompt, setRefinePrompt] = useState("");
  const [isRefining, setIsRefining] = useState(false);
  const [refineSuccess, setRefineSuccess] = useState(false);
  const [isRefreshingBenchmark, setIsRefreshingBenchmark] = useState(false);
  const [isSavingRoadmap, setIsSavingRoadmap] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadDossier() {
      setIsLoading(true);
      setError("");
      try {
        let stored: any = null;
        if (typeof window !== "undefined") {
          for (const storage of [sessionStorage, localStorage]) {
            for (const key of ["current_dossier", "student_radar_last_dossier"]) {
              try {
                const raw = storage.getItem(key);
                if (!raw) continue;
                const parsed = JSON.parse(raw);
                if (parsed?.title && parsed?.slug) {
                  stored = parsed;
                  break;
                }
              } catch {
                // Ignore malformed local records.
              }
            }
            if (stored) break;
          }
        }

        if (slug) {
          if (stored?.slug === slug) {
            if (!cancelled) {
              setDossier(stored);
              markFlowStageDone("understand", `DNA card built for ${stored.title}`);
            }
            return;
          }

          const data = await api.getDossier(slug);
          if (cancelled) return;
          if (data?.title) {
            setDossier(data);
            markFlowStageDone("understand", `DNA card built for ${data.title}`);
            return;
          }
          if (stored) {
            setDossier(stored);
            markFlowStageDone("understand", `DNA card built for ${stored.title}`);
            return;
          }
          setError("We couldn't load this dossier. It may have been generated in another tab.");
          return;
        }

        if (stored) {
          if (!cancelled) {
            setDossier(stored);
            markFlowStageDone("understand", `DNA card built for ${stored.title}`);
          }
          return;
        }

        const data = await api.getDossier("autonomous-drone-swarm-18d39f");
        if (cancelled) return;
        if (data?.title) {
          setDossier(data);
          markFlowStageDone("understand", `DNA card built for ${data.title}`);
        } else {
          setError("No dossier is loaded yet. Generate one from the studio dock to get started.");
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.message || "We couldn't load the dossier workspace.");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadDossier();
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const handleRefine = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!refinePrompt.trim() || !dossier) return;

    setIsRefining(true);
    try {
      const mergedInput = `${dossier.title}: ${dossier.problem_statement}. Additional user refinement: ${refinePrompt.trim()}`;
      const updated = await api.ingestArtifact({
        input_type: "idea",
        raw_content: mergedInput,
        domain_persona: dossier.domain_persona || "tech_builder"
      });

      setDossier(updated);
      if (typeof window !== "undefined") {
        sessionStorage.setItem("current_dossier", JSON.stringify(updated));
        localStorage.setItem("student_radar_last_dossier", JSON.stringify(updated));
      }
      setRefinePrompt("");
      markFlowStageDone("repeat", "Dossier re-analysed with a refinement");
      setRefineSuccess(true);
      setTimeout(() => setRefineSuccess(false), 2500);
    } catch (err: any) {
      console.error("Refinement failed:", err);
    } finally {
      setIsRefining(false);
    }
  };

  const persistUpdatedDossier = (updated: any) => {
    if (!updated?.title) return;
    setDossier(updated);
    if (typeof window !== "undefined") {
      sessionStorage.setItem("current_dossier", JSON.stringify(updated));
      localStorage.setItem("student_radar_last_dossier", JSON.stringify(updated));
    }
  };

  const handleRefreshBenchmark = async () => {
    if (!dossier?.slug || isRefreshingBenchmark) return;
    setIsRefreshingBenchmark(true);
    try {
      const updated = await api.refreshDossierBenchmark(dossier.slug);
      persistUpdatedDossier(updated);
    } catch (err: any) {
      console.error("Ecosystem benchmark refresh failed:", err);
    } finally {
      setIsRefreshingBenchmark(false);
    }
  };

  const handleSaveRoadmap = async (selectedUpgrades: any[]) => {
    if (!dossier?.slug || isSavingRoadmap) return;
    setIsSavingRoadmap(true);
    try {
      const updated = await api.saveDossierRoadmap(dossier.slug, selectedUpgrades);
      persistUpdatedDossier(updated);
    } catch (err: any) {
      console.error("Roadmap save failed:", err);
    } finally {
      setIsSavingRoadmap(false);
    }
  };

  return (
    <>
      {/* Navigation Breadcrumb */}
      <div className="flex items-center justify-between mb-4">
        <Link
          href="/"
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white font-mono transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Studio Dock</span>
        </Link>

        <div className="flex items-center gap-2">
          {dossier && (
            <>
              <button
                onClick={() => setIsReviewModalOpen(true)}
                className="flex items-center gap-1.5 bg-void-card border border-horizon-violet/30 hover:border-horizon-violet text-xs text-horizon-violet font-semibold px-3 py-1.5 rounded-lg transition-all"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Review (+10⚡)</span>
              </button>
              <button
                onClick={() => setIsInviteModalOpen(true)}
                className="flex items-center gap-1.5 bg-horizon-indigo hover:bg-indigo-600 text-white text-xs font-semibold px-3.5 py-1.5 rounded-lg shadow-md transition-all active:scale-95"
              >
                <Share2 className="w-3.5 h-3.5" />
                <span>Invite Peers (+15⚡)</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Interactive LLM Concept Refinement Bar */}
      {dossier && (
        <div className="mb-6 rounded-xl bg-void-card border border-void-border p-2 sm:p-2.5 shadow-lg flex items-center gap-2">
          <form onSubmit={handleRefine} className="flex-1 flex items-center gap-2">
            <div className="flex items-center gap-1.5 text-xs font-mono text-gray-400 px-2 shrink-0">
              <Sparkles className="w-3.5 h-3.5 text-horizon-indigo" />
              <span className="hidden sm:inline">Refine Concept:</span>
            </div>
            <input
              type="text"
              value={refinePrompt}
              onChange={(e) => setRefinePrompt(e.target.value)}
              placeholder="Add more details, requested tech stack, or specific target metrics (e.g., 'Add WebAssembly edge execution and sub-50ms latency')..."
              className="w-full bg-void/60 rounded-lg border border-void-border px-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-horizon-indigo"
            />
            <button
              type="submit"
              disabled={isRefining || !refinePrompt.trim()}
              className="flex items-center gap-1.5 bg-horizon-indigo/20 hover:bg-horizon-indigo/40 border border-horizon-indigo/40 disabled:opacity-40 text-xs font-semibold text-white px-3.5 py-1.5 rounded-lg transition-all shrink-0"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-horizon-indigo ${isRefining ? "animate-spin" : ""}`} />
              <span>{isRefining ? "Refining..." : "Update Dossier"}</span>
            </button>
          </form>
          {refineSuccess && (
            <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1 pr-2 shrink-0">
              <Check className="w-3 h-3" /> Updated!
            </span>
          )}
        </div>
      )}

      {/* 65 / 35 Split Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* Left Column (65% width / 8 cols): Project DNA + Editorial Paper Dossier */}
        <div className="lg:col-span-8 w-full space-y-6">
          {isLoading ? (
            <div className="w-full rounded-2xl bg-editorial-paper border border-white/20 p-10 text-center text-editorial-ink">
              <Sparkles className="w-6 h-6 mx-auto mb-3 animate-pulse text-horizon-indigo" />
              <p className="text-sm font-mono text-gray-500">Assembling your Proof-of-Work dossier...</p>
            </div>
          ) : dossier ? (
            <>
              <ProjectDNACard dossier={dossier} />
              <DossierCard
                dossier={dossier}
                onOpenPeerReview={() => setIsReviewModalOpen(true)}
                onOpenPRStudio={() => router.push(`/pr-studio?dossierId=${dossier?.id || ""}`)}
              />
            </>
          ) : (
            <div className="w-full rounded-2xl bg-editorial-paper border border-white/20 p-10 text-center text-editorial-ink">
              <AlertCircle className="w-7 h-7 mx-auto mb-3 text-horizon-violet" />
              <h2 className="text-lg font-bold font-serif mb-2">No dossier loaded</h2>
              <p className="text-sm text-gray-600 max-w-md mx-auto mb-5">
                {error || "Generate a dossier from the studio dock to open your Proof-of-Work workspace."}
              </p>
              <Link
                href="/"
                className="inline-flex items-center gap-2 bg-horizon-indigo hover:bg-indigo-600 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition-all"
              >
                Generate a Dossier
              </Link>
            </div>
          )}
        </div>

        {/* Right Column (35% width / 4 cols): Idea Radar & Ecosystem Intel */}
        <div className="lg:col-span-4 w-full flex flex-col gap-6">
          {dossier && (
            <>
              <IdeaRadarWidget
                dossier={dossier}
                onOpenInviteModal={(role) => {
                  setSelectedRole(role || "Contributor");
                  setIsInviteModalOpen(true);
                }}
              />
              <EcosystemBenchmarkCard
                dossier={dossier}
                isLoading={isLoading}
                isRefreshing={isRefreshingBenchmark}
                onRefresh={dossier.slug ? handleRefreshBenchmark : undefined}
                onAddUpgrades={handleSaveRoadmap}
              />
            </>
          )}
        </div>

      </div>

      {/* Contact Discovery Modal (Zero-PII Web Crypto + wa.me) */}
      <ContactDiscoveryModal
        isOpen={isInviteModalOpen}
        onClose={() => setIsInviteModalOpen(false)}
        dossierId={dossier?.id || "mock-id"}
        dossierSlug={dossier?.slug || "project"}
        roleContext={selectedRole}
      />

      {/* Peer Review Rubric Modal (+10⚡) */}
      <PeerReviewModal
        isOpen={isReviewModalOpen}
        onClose={() => setIsReviewModalOpen(false)}
        dossierId={dossier?.id || "mock-id"}
        dossierTitle={dossier?.title || "Project Dossier"}
      />
    </>
  );
}

export default function DossierPage() {
  return (
    <div className="relative min-h-screen bg-void text-white selection:bg-horizon-indigo selection:text-white">
      {/* Top Luminous Ambient Arc */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[350px] bg-horizon-radial pointer-events-none -z-10" />

      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
        <Suspense fallback={<div className="text-xs font-mono text-gray-500 py-10 text-center">Loading Proof-of-Work Dossier Workspace...</div>}>
          <DossierContent />
        </Suspense>
      </main>
    </div>
  );
}
