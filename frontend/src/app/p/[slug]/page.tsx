import React from "react";
import type { Metadata } from "next";
import { Navbar } from "@/components/Navbar";
import { DossierCard } from "@/components/DossierCard";
import { DossierViewBeacon } from "@/components/DossierViewBeacon";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { synthesizeFallbackDossier, slugToFallbackContent } from "@/lib/heuristicDossier";

interface PublicDossierProps {
  params: Promise<{ slug: string }>;
}

async function fetchDossierData(slug: string) {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  try {
    const res = await fetch(`${API_BASE}/dossiers/public/${slug}`, {
      next: { revalidate: 60 },
    });
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn(`Public dossier fetch failed for ${slug}, using local fallback.`);
  }

  // Derive the preview from the slug instead of showing an unrelated drone
  // project. A real backend response will replace this as soon as it is
  // available.
  return synthesizeFallbackDossier(
    slugToFallbackContent(slug),
    "idea",
    "tech_builder",
    slug,
  );
}

export async function generateMetadata({ params }: PublicDossierProps): Promise<Metadata> {
  const resolvedParams = await params;
  const dossier = await fetchDossierData(resolvedParams.slug);

  return {
    title: `${dossier.title} // Proof-of-Work Dossier`,
    description: dossier.tagline,
    openGraph: {
      title: `${dossier.title} — Verified Proof-of-Work`,
      description: dossier.tagline,
      images: [
        {
          url: `https://assets.studentradar.dev/og/${resolvedParams.slug}.png`,
          width: 1200,
          height: 630,
          alt: dossier.title,
        },
      ],
      type: "article",
    },
    twitter: {
      card: "summary_large_image",
      title: dossier.title,
      description: dossier.tagline,
      images: [`https://assets.studentradar.dev/og/${resolvedParams.slug}.png`],
    },
  };
}

export default async function PublicDossierPage({ params }: PublicDossierProps) {
  const resolvedParams = await params;
  const dossier = await fetchDossierData(resolvedParams.slug);

  return (
    <div className="relative min-h-screen bg-void text-white selection:bg-horizon-indigo selection:text-white">
      <DossierViewBeacon slug={resolvedParams.slug} />

      {/* Top Ambient Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[350px] bg-horizon-radial pointer-events-none -z-10" />

      <Navbar />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
        
        {/* Back Link */}
        <div className="flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white font-mono transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Discover More Student Builds</span>
          </Link>

          <span className="text-xs font-mono text-gray-500">
            Public Proof-of-Work Record
          </span>
        </div>

        {/* Public Dossier Card */}
        <DossierCard dossier={dossier} />

        {/* Recruiter & Collaborator Action Panel */}
        <div className="rounded-2xl bg-void-card border border-void-border p-6 text-center space-y-4">
          <h3 className="text-base font-bold text-white">
            Interested in Collaborating with this Builder Team?
          </h3>
          <p className="text-xs text-gray-400 max-w-lg mx-auto leading-relaxed">
            Connect with this team directly, review their open engineering roles, or explore their full public architecture specification.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Link
              href="/"
              className="bg-white text-gray-900 text-xs font-bold px-4 py-2.5 rounded-xl hover:bg-gray-100 transition-all shadow-md"
            >
              Build Your Own Dossier
            </Link>
          </div>
        </div>

      </main>
    </div>
  );
}

