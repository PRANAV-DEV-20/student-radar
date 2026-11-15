"use client";

import React from "react";
import { Compass, Users, Sparkles, UserPlus, Lightbulb, ExternalLink } from "lucide-react";

interface IdeaRadarWidgetProps {
  dossier: any;
  onOpenInviteModal?: (role?: string) => void;
}

export function IdeaRadarWidget({ dossier, onOpenInviteModal }: IdeaRadarWidgetProps) {
  if (!dossier) return null;

  const whitespace = dossier.whitespace_analysis || {};
  const missingRoles = dossier.missing_roles || [];
  const topVoices = whitespace.top_voices || [];

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Widget Container */}
      <div className="rounded-2xl bg-void-card border border-void-border p-6 shadow-xl relative overflow-hidden">
        {/* Subtle radial corner glow */}
        <div className="absolute top-0 right-0 w-48 h-48 bg-horizon-indigo/10 rounded-full blur-3xl -z-10" />

        <div className="flex items-center gap-2 border-b border-void-border pb-3 mb-5">
          <Compass className="w-4 h-4 text-horizon-indigo" />
          <h2 className="text-xs font-mono uppercase tracking-wider font-bold text-gray-200">
            // Idea Radar & Whitespace Intel
          </h2>
        </div>

        {/* 1. Market Whitespace Analysis */}
        <div className="mb-6">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-300 mb-2">
            <Lightbulb className="w-4 h-4 text-amber-400" />
            <span>Identified Competitive Whitespace:</span>
          </div>
          <div className="p-3.5 rounded-xl bg-void border border-void-border text-xs text-gray-300 leading-relaxed font-sans">
            {whitespace.market_gap || "Identified market gap in low-latency edge deployment and decentralized failure recovery."}
          </div>
        </div>

        {/* 2. Top Ecosystem Voices */}
        {topVoices.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-300 mb-2">
              <Sparkles className="w-4 h-4 text-horizon-violet" />
              <span>Top Ecosystem Voices to Tag / Pitch:</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {topVoices.map((voice: string, idx: number) => (
                <span
                  key={idx}
                  className="text-xs font-mono bg-void-card/90 border border-void-border hover:border-horizon-violet/40 text-gray-300 px-2.5 py-1 rounded-md transition-colors"
                >
                  {voice}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 3. Missing Roles Recommender */}
        <div>
          <div className="flex items-center justify-between text-xs font-semibold text-gray-300 mb-3">
            <div className="flex items-center gap-1.5">
              <Users className="w-4 h-4 text-horizon-indigo" />
              <span>Recommended Team Additions:</span>
            </div>
            <span className="text-[10px] text-emerald-400 font-mono">+15⚡ reward</span>
          </div>

          <div className="space-y-2.5">
            {missingRoles.length > 0 ? (
              missingRoles.map((roleObj: any, i: number) => (
                <div
                  key={i}
                  className="p-3 rounded-xl bg-void border border-void-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5"
                >
                  <div>
                    <span className="text-xs font-bold text-white block">
                      {roleObj.role}
                    </span>
                    <span className="text-[11px] text-gray-400 line-clamp-2">
                      {roleObj.reason}
                    </span>
                  </div>

                  <button
                    onClick={() => onOpenInviteModal && onOpenInviteModal(roleObj.role)}
                    className="shrink-0 flex items-center gap-1 text-[11px] font-semibold text-white bg-horizon-indigo/20 hover:bg-horizon-indigo/40 border border-horizon-indigo/40 px-3 py-1.5 rounded-lg transition-all"
                  >
                    <UserPlus className="w-3.5 h-3.5 text-horizon-indigo" />
                    <span>Invite Peer</span>
                  </button>
                </div>
              ))
            ) : (
              <div className="p-3 rounded-xl bg-void text-xs text-gray-500 font-mono">
                No open roles configured.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

