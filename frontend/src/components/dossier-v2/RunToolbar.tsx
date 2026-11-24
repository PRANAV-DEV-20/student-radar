"use client";

import React from "react";
import { Download, FileJson, FileText, Loader2, Plus, RotateCcw } from "lucide-react";
import { DossierRun } from "@/lib/dossierV2Api";

interface RunToolbarProps {
  run: DossierRun | null;
  runId: string | null;
  onNewRun: () => void;
  onRerun: () => void;
  rerunning: boolean;
  onExport: (format: "markdown" | "json") => void;
  exporting: "markdown" | "json" | null;
  error?: string;
}

export default function RunToolbar({
  run,
  runId,
  onNewRun,
  onRerun,
  rerunning,
  onExport,
  exporting,
  error,
}: RunToolbarProps) {
  const status = run?.status || (runId ? "loading" : "idle");
  return (
    <div className="dv2-paper dv2-toolbar">
      <div className="dv2-toolbar-identity">
        <span className={`dv2-status-pill dv2-status-${status.toLowerCase()}`}>{status}</span>
        <div>
          <p className="dv2-eyebrow">Active run</p>
          <code>{runId || "none"}</code>
        </div>
      </div>
      <div className="dv2-toolbar-meta">
        {run?.mode && <span>mode: <strong>{String(run.mode)}</strong></span>}
        {run?.cost_usd !== undefined && <span>cost: <strong>${run.cost_usd}</strong></span>}
        {run?.duration_ms !== undefined && <span>duration: <strong>{Math.round(run.duration_ms / 1000)}s</strong></span>}
      </div>
      <div className="dv2-toolbar-actions">
        <button type="button" className="dv2-button dv2-button-quiet dv2-button-tiny" onClick={onNewRun}>
          <Plus size={13} /> New run
        </button>
        <button
          type="button"
          className="dv2-button dv2-button-quiet dv2-button-tiny"
          onClick={onRerun}
          disabled={!runId || rerunning}
        >
          <RotateCcw size={13} className={rerunning ? "dv2-spin" : ""} /> {rerunning ? "Re-running…" : "Re-run research"}
        </button>
        <button
          type="button"
          className="dv2-button dv2-button-quiet dv2-button-tiny"
          onClick={() => onExport("markdown")}
          disabled={!runId || exporting !== null}
        >
          {exporting === "markdown" ? <Loader2 size={13} className="dv2-spin" /> : <FileText size={13} />} Markdown
        </button>
        <button
          type="button"
          className="dv2-button dv2-button-quiet dv2-button-tiny"
          onClick={() => onExport("json")}
          disabled={!runId || exporting !== null}
        >
          {exporting === "json" ? <Loader2 size={13} className="dv2-spin" /> : <FileJson size={13} />} JSON
        </button>
      </div>
      {error && (
        <p className="dv2-toolbar-error" role="alert">
          <Download size={12} /> {error}
        </p>
      )}
    </div>
  );
}
