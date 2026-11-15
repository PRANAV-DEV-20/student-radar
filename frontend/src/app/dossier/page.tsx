"use client";

import React, { Suspense, useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { DossierCard } from "@/components/DossierCard";
import { IdeaRadarWidget } from "@/components/IdeaRadarWidget";
import { ContactDiscoveryModal } from "@/components/ContactDiscoveryModal";
import { PeerReviewModal } from "@/components/PeerReviewModal";
import { api } from "@/lib/api";
import { ArrowLeft, Sparkles, Share2 } from "lucide-react";
import Link from "next/link";

function DossierContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const slug = searchParams.get("slug");

  const [dossier, setDossier] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState("Contributor");
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);

  useEffect(() => {
    async function loadDossier() {
      setIsLoading(true);
      try {
        if (slug) {
          const data = await api.getDossier(slug);
          setDossier(data);
        } else {
          const stored = typeof window !== "undefined" ? sessionStorage.getItem("current_dossier") : null;
          if (stored) {
            setDossier(JSON.parse(stored));
          } else {
            const data = await api.getDossier("autonomous-drone-swarm-18d39f");
            setDossier(data);
          }
        }
      } catch (err) {
        console.error("Failed to load dossier:", err);
      } finally {
        setIsLoading(false);
      }
    }

    loadDossier();
  }, [slug]);

  return (
    <>
      {/* Navigation Breadcrumb */}
      <div className="flex items-center justify-between mb-6">
        <Link
          href="/"
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white font-mono transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Studio Dock</span>
        </Link>

        <div className="flex items-center gap-2">
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
        </div>
      </div>

      {/* 65 / 35 Split Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* Left Column (65% width / 8 cols): The Editorial Paper Dossier */}
        <div className="lg:col-span-8 w-full">
          <DossierCard
            dossier={dossier}
            onOpenPeerReview={() => setIsReviewModalOpen(true)}
            onOpenPRStudio={() => router.push(`/pr-studio?dossierId=${dossier?.id || ""}`)}
          />
        </div>

        {/* Right Column (35% width / 4 cols): Idea Radar & Ecosystem Intel */}
        <div className="lg:col-span-4 w-full">
          <IdeaRadarWidget
            dossier={dossier}
            onOpenInviteModal={(role) => {
              setSelectedRole(role || "Contributor");
              setIsInviteModalOpen(true);
            }}
          />
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
