"use client";

import React from "react";
import { AlertCircle, CheckCircle2, CircleDashed, Layers, Radio } from "lucide-react";

export type TimelineKind = "progress" | "section" | "complete" | "error" | "local";

export interface TimelineEvent {
  id: string;
  type: TimelineKind;
  message: string;
  at: number;
}

interface ProgressTimelineProps {
  status: string;
  stage: string;
  message: string;
  completed: number;
  total: number;
  events: TimelineEvent[];
  streamError: boolean;
}

function eventIcon(type: TimelineKind) {
  if (type === "complete") return <CheckCircle2 size={14} />;
  if (type === "error") return <AlertCircle size={14} />;
  if (type === "section") return <Layers size={14} />;
  if (type === "progress") return <Radio size={14} />;
  return <CircleDashed size={14} />;
}

function formatTime(at: number): string {
  try {
    return new Date(at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "";
  }
}

export default function ProgressTimeline({
  status,
  stage,
  message,
  completed,
  total,
  events,
  streamError,
}: ProgressTimelineProps) {
  const percent = total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 0;
  return (
    <section className="dv2-paper dv2-timeline" aria-label="Run progress">
      <div className="dv2-timeline-top">
        <div>
          <p className="dv2-eyebrow">Run stream</p>
          <h3 className="dv2-timeline-stage">{stage || (status ? `Status: ${status}` : "Preparing")}</h3>
          <p className="dv2-timeline-message">{message || "Waiting for the first stream event…"}</p>
        </div>
        <div className="dv2-timeline-count">
          <strong>{completed}</strong><span>/{total}</span>
          <small>sections written</small>
        </div>
      </div>

      <div className="dv2-progress-track" role="progressbar" aria-valuenow={completed} aria-valuemin={0} aria-valuemax={total}>
        <div className="dv2-progress-fill" style={{ width: `${percent}%` }} />
      </div>

      {streamError && (
        <p className="dv2-stream-note">Live stream interrupted — polling the run directly for updates.</p>
      )}

      <div className="dv2-event-log">
        {events.length === 0 ? (
          <p className="dv2-muted">No events received yet. Stages appear here as the run progresses.</p>
        ) : (
          events.map((event) => (
            <div key={event.id} className={`dv2-event dv2-event-${event.type}`}>
              <span className="dv2-event-icon">{eventIcon(event.type)}</span>
              <span className="dv2-event-message">{event.message}</span>
              <time>{formatTime(event.at)}</time>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
