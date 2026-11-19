"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Zap, ShieldCheck, Compass, Sparkles, UserCheck, LayoutDashboard } from "lucide-react";
import { DOMAIN_PERSONAS } from "@/lib/constants";
import { getAuthToken } from "@/lib/api";

interface NavbarProps {
  currentPersona?: string;
  onPersonaChange?: (personaId: string) => void;
  onOpenAuthModal?: () => void;
}

export function Navbar({ currentPersona = "tech_builder", onPersonaChange, onOpenAuthModal }: NavbarProps) {
  const pathname = usePathname();
  const [credits, setCredits] = useState(30);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    const token = getAuthToken();
    if (token) setIsLoggedIn(true);
  }, []);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-void-border bg-void/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        
        {/* Brand / Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-void-card border border-void-border group-hover:border-horizon-indigo transition-colors shadow-sm">
            <span className="text-lg font-black bg-gradient-to-tr from-horizon-indigo to-horizon-violet bg-clip-text text-transparent">
              ⚡
            </span>
            <div className="absolute inset-0 rounded-lg bg-horizon-indigo/20 blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold tracking-tight text-white flex items-center gap-1.5">
              STUDENT RADAR
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded border border-horizon-indigo/40 bg-horizon-indigo/10 text-indigo-300">
                PoW
              </span>
            </span>
            <span className="text-[10px] text-gray-400 font-mono">Proof-of-Work & Opportunity</span>
          </div>
        </Link>

        {/* Center Navigation Links */}
        <nav className="hidden md:flex items-center gap-1 bg-void-card/60 p-1 rounded-full border border-void-border">
          <Link
            href="/"
            className={`px-3.5 py-1.5 text-xs font-medium rounded-full transition-all ${
              pathname === "/" ? "bg-white/10 text-white shadow-inner" : "text-gray-400 hover:text-white"
            }`}
          >
            Studio
          </Link>
          <Link
            href="/dashboard"
            className={`px-3.5 py-1.5 text-xs font-medium rounded-full transition-all flex items-center gap-1 ${
              pathname.startsWith("/dashboard") ? "bg-white/10 text-white shadow-inner" : "text-gray-400 hover:text-white"
            }`}
          >
            <LayoutDashboard className="w-3.5 h-3.5 text-horizon-indigo" />
            Dashboard
          </Link>
          <Link
            href="/dossier"
            className={`px-3.5 py-1.5 text-xs font-medium rounded-full transition-all ${
              pathname.startsWith("/dossier") ? "bg-white/10 text-white shadow-inner" : "text-gray-400 hover:text-white"
            }`}
          >
            Dossier
          </Link>
          <Link
            href="/pr-studio"
            className={`px-3.5 py-1.5 text-xs font-medium rounded-full transition-all ${
              pathname.startsWith("/pr-studio") ? "bg-white/10 text-white shadow-inner" : "text-gray-400 hover:text-white"
            }`}
          >
            PR Studio
          </Link>
          <Link
            href="/radar"
            className={`px-3.5 py-1.5 text-xs font-medium rounded-full transition-all flex items-center gap-1 ${
              pathname.startsWith("/radar") ? "bg-white/10 text-white shadow-inner" : "text-gray-400 hover:text-white"
            }`}
          >
            <Compass className="w-3.5 h-3.5 text-horizon-indigo" />
            Radar
          </Link>
        </nav>

        {/* Right Section: Persona Selector + Credits & Auth */}
        <div className="flex items-center gap-3">
          {/* Persona selector quick toggle */}
          {onPersonaChange && (
            <div className="hidden lg:flex items-center gap-1 bg-void-card border border-void-border px-2 py-1 rounded-lg">
              <span className="text-[11px] font-mono text-gray-500 mr-1">Domain:</span>
              <select
                value={currentPersona}
                onChange={(e) => onPersonaChange(e.target.value)}
                aria-label="Filter domain persona"
                className="bg-transparent text-xs text-gray-200 focus:outline-none cursor-pointer"
              >
                {DOMAIN_PERSONAS.map((p) => (
                  <option key={p.id} value={p.id} className="bg-void-card text-white">
                    {p.shortLabel}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Visibility Credits (⚡) — hidden on the command center by design */}
          {!pathname.startsWith("/dashboard") && (
            <div className="flex items-center gap-1.5 bg-void-card border border-horizon-violet/30 px-3 py-1.5 rounded-full shadow-sm">
              <Zap className="w-3.5 h-3.5 text-horizon-violet fill-horizon-violet" />
              <span className="text-xs font-bold text-white font-mono">{credits}⚡</span>
            </div>
          )}

          {/* Auth Button */}
          <button
            onClick={onOpenAuthModal}
            className="flex items-center gap-1.5 bg-gradient-to-r from-horizon-indigo to-horizon-violet hover:from-indigo-600 hover:to-purple-600 text-white text-xs font-semibold px-3.5 py-1.5 rounded-lg shadow-md transition-all active:scale-95"
          >
            {isLoggedIn ? (
              <>
                <UserCheck className="w-3.5 h-3.5" />
                <span>Account</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Sign in / Claim</span>
              </>
            )}
          </button>
        </div>

      </div>
    </header>
  );
}

