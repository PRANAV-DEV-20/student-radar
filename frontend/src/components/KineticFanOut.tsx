"use client";

import React, { useState } from "react";
import { ShieldCheck, ArrowUpRight, Cpu, Activity, Dna } from "lucide-react";

export function KineticFanOut() {
  const [activeCard, setActiveCard] = useState<number>(1);

  const cards = [
    {
      id: 0,
      title: "Autonomous Drone Swarm Mesh",
      domain: "ENGINEERING / AI",
      tagline: "Mesh-based multi-agent coordination operating in zero-GPS environments.",
      metric: "12.4ms",
      metricLabel: "Convergence Latency",
      stack: ["Rust", "ROS 2", "LoRaWAN"],
      badgeColor: "text-indigo-400 bg-indigo-500/10 border-indigo-500/30",
      icon: Cpu,
      rotation: "-rotate-6 translate-y-3 -translate-x-8 hover:-translate-y-2 hover:rotate-0",
      activeTransform: "-rotate-4 -translate-x-4",
    },
    {
      id: 1,
      title: "DeFi Liquidity Risk Sentinel",
      domain: "FINANCE / QUANT",
      tagline: "Dynamic AMM fee curvature reducing loss-versus-rebalancing (LVR) by 34.2%.",
      metric: "-34.2%",
      metricLabel: "Impermanent Loss",
      stack: ["Solidity", "Rust", "TimescaleDB"],
      badgeColor: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
      icon: Activity,
      rotation: "rotate-0 translate-y-0 z-20 scale-105",
      activeTransform: "scale-105 z-20 shadow-2xl ring-1 ring-horizon-indigo/40",
    },
    {
      id: 2,
      title: "CRISPR Epigenetic Predictor",
      domain: "BIOTECH / DESIGN",
      tagline: "Transformer model incorporating ENCODE DNase chromatin accessibility with 97.8% recall.",
      metric: "97.8%",
      metricLabel: "Off-Target Recall",
      stack: ["PyTorch", "RDKit", "Mol*"],
      badgeColor: "text-cyan-400 bg-cyan-500/10 border-cyan-500/30",
      icon: Dna,
      rotation: "rotate-6 translate-y-3 translate-x-8 hover:-translate-y-2 hover:rotate-0",
      activeTransform: "rotate-4 translate-x-4",
    }
  ];

  return (
    <div className="relative w-full max-w-5xl mx-auto py-12 px-4 flex flex-col items-center">
      <div className="text-center mb-10">
        <span className="text-xs font-mono uppercase tracking-widest text-horizon-indigo mb-2 inline-block">
          // PROOF-OF-WORK DOSSIER GALLERY
        </span>
        <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          Publication-Ready Builds from Day One
        </h2>
        <p className="text-sm text-gray-400 max-w-xl mx-auto mt-2">
          Every ingested idea or repo generates a verified, high-contrast Editorial Paper Dossier with architectural specs and PR assets.
        </p>
      </div>

      {/* 3-Card Fan-Out Stage */}
      <div className="relative w-full max-w-4xl h-[380px] sm:h-[420px] flex items-center justify-center">
        {cards.map((card, idx) => {
          const Icon = card.icon;
          const isCenter = idx === activeCard;

          return (
            <div
              key={card.id}
              onClick={() => setActiveCard(idx)}
              className={`absolute top-0 w-80 sm:w-96 rounded-2xl bg-editorial-paper p-6 sm:p-7 shadow-2xl transition-all duration-500 cursor-pointer text-editorial-ink ${
                isCenter ? "z-30 scale-100 shadow-2xl" : "z-10 opacity-80 hover:opacity-100"
              } ${card.rotation}`}
            >
              {/* Paper Dossier Card Header */}
              <div className="flex items-center justify-between border-b border-gray-200 pb-3 mb-4">
                <span className={`text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded border ${card.badgeColor}`}>
                  {card.domain}
                </span>
                <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  VERIFIED ARTIFACT
                </span>
              </div>

              {/* Title & Tagline */}
              <div className="mb-6">
                <h3 className="text-lg font-bold font-serif leading-tight text-gray-900 mb-2">
                  {card.title}
                </h3>
                <p className="text-xs text-gray-600 leading-relaxed">
                  {card.tagline}
                </p>
              </div>

              {/* Quantitative Metric Callout */}
              <div className="rounded-xl bg-white border border-gray-200 p-3 mb-5 flex items-center justify-between">
                <div>
                  <span className="text-[10px] uppercase font-mono text-gray-500 block">
                    {card.metricLabel}
                  </span>
                  <span className="text-xl font-bold font-mono text-gray-900">
                    {card.metric}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-gray-50 border border-gray-100">
                  <Icon className="w-5 h-5 text-gray-700" />
                </div>
              </div>

              {/* Tech Stack Pills & Dossier Link */}
              <div className="flex items-center justify-between pt-2 border-t border-gray-100">
                <div className="flex flex-wrap gap-1.5">
                  {card.stack.map((s) => (
                    <span key={s} className="text-[10px] font-mono bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                      {s}
                    </span>
                  ))}
                </div>
                <span className="text-xs font-semibold text-horizon-indigo flex items-center gap-0.5 hover:underline">
                  View <ArrowUpRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

