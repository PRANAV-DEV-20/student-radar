"use client";

import React from "react";
import Link from "next/link";
import {
  BrainCircuit,
  PenLine,
  Send,
  Users,
  BarChart3,
  RefreshCw,
  Check,
  type LucideIcon,
} from "lucide-react";
import { FLOW_STAGES, getFlowState, type FlowStageId } from "@/lib/flow";

const ICONS: Record<FlowStageId, LucideIcon> = {
  understand: BrainCircuit,
  position: PenLine,
  publish: Send,
  connect: Users,
  track: BarChart3,
  repeat: RefreshCw,
};

interface FlowStepperProps {
  activeStage?: FlowStageId;
  /** Re-read on render; callers can force updates by passing state. */
  state?: ReturnType<typeof getFlowState>;
}

export function FlowStepper({ activeStage, state }: FlowStepperProps) {
  const flowState = state || getFlowState();
  const activeIndex = activeStage ? FLOW_STAGES.findIndex((s) => s.id === activeStage) : -1;
  const firstIncomplete = FLOW_STAGES.findIndex((s) => !flowState[s.id]);

  return (
    <nav aria-label="Visibility flow" className="w-full">
      <ol className="grid grid-cols-3 gap-2 sm:grid-cols-6">
        {FLOW_STAGES.map((stage, index) => {
          const Icon = ICONS[stage.id];
          const done = Boolean(flowState[stage.id]);
          const isNext = index === firstIncomplete;
          const isActive = index === activeIndex || (activeIndex === -1 && isNext);
          const href = stage.id === "publish" && !done ? "/pr-studio" : stage.route;

          return (
            <li key={stage.id}>
              <Link
                href={href}
                title={stage.description}
                className={`group relative flex flex-col items-center gap-1.5 rounded-xl border px-2 py-3 text-center transition-all ${
                  isActive
                    ? "border-horizon-indigo/60 bg-horizon-indigo/10"
                    : done
                      ? "border-emerald-500/25 bg-emerald-500/5 hover:border-emerald-500/50"
                      : "border-void-border bg-void-card/50 hover:border-horizon-indigo/40"
                }`}
              >
                <span
                  className={`flex h-7 w-7 items-center justify-center rounded-full border text-[11px] font-mono ${
                    done
                      ? "border-emerald-400/40 bg-emerald-400/15 text-emerald-300"
                      : isActive
                        ? "border-horizon-indigo/60 bg-horizon-indigo text-white"
                        : "border-void-border text-gray-500"
                  }`}
                >
                  {done ? <Check className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}
                </span>
                <span className={`text-[11px] font-semibold ${isActive ? "text-white" : done ? "text-emerald-200" : "text-gray-400"}`}>
                  {stage.label}
                </span>
                <span className="hidden text-[9px] leading-tight text-gray-500 sm:block">{stage.tagline}</span>
              </Link>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
