"use client";

import React, { useState } from "react";
import { Navbar } from "@/components/Navbar";
import { OmniCommandDock } from "@/components/OmniCommandDock";
import { KineticFanOut } from "@/components/KineticFanOut";
import { Sparkles, ShieldCheck, Zap, Lock, Compass, ArrowRight, Share2, Layers } from "lucide-react";
import Link from "next/link";

export default function LandingPage() {
  const [persona, setPersona] = useState("tech_builder");
  const [showAuthModal, setShowAuthModal] = useState(false);

  return (
    <div className="relative min-h-screen bg-void text-white selection:bg-horizon-indigo selection:text-white overflow-hidden">
      
      {/* 1. Luminous Horizon Depth Glow (HorizonX AI Aesthetic) */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[450px] bg-horizon-radial pointer-events-none -z-10" />

      {/* 2. Top Navigation */}
      <Navbar
        currentPersona={persona}
        onPersonaChange={setPersona}
        onOpenAuthModal={() => setShowAuthModal(true)}
      />

      {/* 3. Hero Section */}
      <main className="relative pt-16 sm:pt-20 pb-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto flex flex-col items-center">
        
        {/* Top Product Category Pill */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-void-card border border-void-border text-xs text-gray-300 mb-6 shadow-sm">
          <span className="flex h-2 w-2 rounded-full bg-horizon-indigo animate-pulse" />
          <span className="font-mono text-[11px] uppercase tracking-wider text-gray-400">
            SINGLE-PLAYER UTILITY FIRST // ZERO-ML DATASETS
          </span>
        </div>

        {/* Hero Title */}
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-center text-white max-w-4xl leading-[1.1] mb-6">
          Turn Raw Student Builds Into{" "}
          <span className="bg-gradient-to-r from-horizon-indigo via-purple-300 to-horizon-violet bg-clip-text text-transparent">
            Proof-of-Work Dossiers
          </span>
        </h1>

        {/* Hero Subtitle */}
        <p className="text-base sm:text-lg text-gray-400 text-center max-w-2xl leading-relaxed mb-10">
          Paste any idea, GitHub repository, or research PDF. Receive a publication-grade Editorial Dossier, 3-column PR launch kit, and tailored daily opportunity radar in seconds.
        </p>

        {/* Omni-Command Dock (⌘K) */}
        <div className="w-full mb-16">
          <OmniCommandDock />
        </div>

        {/* 4. 3-Card Kinetic Fan-Out Stage */}
        <KineticFanOut />

        {/* 5. Scrollytelling Bento Grid: Product Loops & Architectural Advantages */}
        <section className="w-full mt-24">
          <div className="text-center mb-12">
            <span className="text-xs font-mono uppercase tracking-widest text-horizon-indigo mb-2 inline-block">
              // ARCHITECTURAL DESIGN ADVANTAGES
            </span>
            <h2 className="text-3xl font-bold tracking-tight text-white">
              Why Student Radar Prevents Platform Failure
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            
            {/* Bento Card 1: Single-Player Wedge */}
            <div className="p-6 rounded-2xl bg-void-card border border-void-border hover:border-horizon-indigo/40 transition-all flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-xl bg-horizon-indigo/10 border border-horizon-indigo/30 flex items-center justify-center mb-4">
                  <Layers className="w-5 h-5 text-horizon-indigo" />
                </div>
                <h3 className="text-base font-bold text-white mb-2">Single-Player Utility Wedge</h3>
                <p className="text-xs text-gray-400 leading-relaxed">
                  Students get instant value on day one by turning raw ideas into verified dossiers. Generated dossiers automatically seed the public discovery directory.
                </p>
              </div>
              <div className="mt-4 pt-4 border-t border-void-border/50 text-[11px] font-mono text-horizon-indigo">
                → No empty-feed dilemma
              </div>
            </div>

            {/* Bento Card 2: Domain-Agnostic Engine */}
            <div className="p-6 rounded-2xl bg-void-card border border-void-border hover:border-horizon-violet/40 transition-all flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-xl bg-horizon-violet/10 border border-horizon-violet/30 flex items-center justify-center mb-4">
                  <Compass className="w-5 h-5 text-horizon-violet" />
                </div>
                <h3 className="text-base font-bold text-white mb-2">Domain-Agnostic Personas</h3>
                <p className="text-xs text-gray-400 leading-relaxed">
                  Decoupled JSON config files serve Engineering, Law & Policy, Finance & Venture, and Biotech without writing new backend code.
                </p>
              </div>
              <div className="mt-4 pt-4 border-t border-void-border/50 text-[11px] font-mono text-horizon-violet">
                → configs/personas/*.json
              </div>
            </div>

            {/* Bento Card 3: Zero-PII Web Crypto */}
            <div className="p-6 rounded-2xl bg-void-card border border-void-border hover:border-emerald-500/40 transition-all flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mb-4">
                  <Lock className="w-5 h-5 text-emerald-400" />
                </div>
                <h3 className="text-base font-bold text-white mb-2">Privacy-Safe Peer Matching</h3>
                <p className="text-xs text-gray-400 leading-relaxed">
                  Client-side SHA-256 Web Crypto hashing matches campus builders without ever storing non-user personal email addresses on the backend.
                </p>
              </div>
              <div className="mt-4 pt-4 border-t border-void-border/50 text-[11px] font-mono text-emerald-400">
                → window.crypto.subtle
              </div>
            </div>

            {/* Bento Card 4: Visibility Credits Loop */}
            <div className="p-6 rounded-2xl bg-void-card border border-void-border hover:border-amber-500/40 transition-all flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mb-4">
                  <Zap className="w-5 h-5 text-amber-400" />
                </div>
                <h3 className="text-base font-bold text-white mb-2">Visibility Token Economy</h3>
                <p className="text-xs text-gray-400 leading-relaxed">
                  Earn +10⚡ for substantive peer reviews, +15⚡ for attributed campus invites, and spend -20⚡ to boost your project into the discovery spotlight.
                </p>
              </div>
              <div className="mt-4 pt-4 border-t border-void-border/50 text-[11px] font-mono text-amber-400">
                → Structured 3-field rubric
              </div>
            </div>

          </div>
        </section>

      </main>

      {/* Footer */}
      <footer className="w-full border-t border-void-border py-8 text-center text-xs text-gray-500 font-mono">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <span>AI-POWERED STUDENT RADAR // OBSIDIAN ATELIER DESIGN SYSTEM</span>
          <span>BUILT FOR TECHNICAL BUILDERS & RESEARCHERS GLOBALLY</span>
        </div>
      </footer>

      {/* Simulated Auth / Claim Modal */}
      {showAuthModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="relative w-full max-w-sm rounded-2xl bg-void-card border border-void-border p-6 shadow-2xl text-center">
            <div className="w-12 h-12 rounded-full bg-horizon-indigo/20 text-horizon-indigo flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-white mb-1">Claim Guest Dossier</h3>
            <p className="text-xs text-gray-400 mb-6">
              Sign in with Google to bind your unauthenticated guest session and unlock 30⚡ Visibility Credits.
            </p>
            <button
              onClick={() => {
                localStorage.setItem("student_radar_jwt", "demo_jwt_token");
                setShowAuthModal(false);
                window.location.reload();
              }}
              className="w-full flex items-center justify-center gap-2 bg-white text-gray-900 font-bold text-xs py-2.5 rounded-xl shadow-lg hover:bg-gray-100 transition-all active:scale-95"
            >
              <span>Continue with Google</span>
            </button>
            <button
              onClick={() => setShowAuthModal(false)}
              className="mt-3 text-xs text-gray-500 hover:text-gray-300"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

    </div>
  );
}

