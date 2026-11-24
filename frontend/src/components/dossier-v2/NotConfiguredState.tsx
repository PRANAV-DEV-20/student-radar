"use client";

import React from "react";
import { AlertTriangle, RefreshCw, ServerOff } from "lucide-react";
import { DossierV2Error } from "@/lib/dossierV2Api";

interface NotConfiguredStateProps {
  error: DossierV2Error;
  onRetry: () => void;
}

export default function NotConfiguredState({ error, onRetry }: NotConfiguredStateProps) {
  return (
    <section className="dv2-paper dv2-not-configured" role="alert">
      <div className="dv2-not-configured-icon"><ServerOff size={22} /></div>
      <p className="dv2-eyebrow">Run could not start · 503</p>
      <h2 className="dv2-section-title">AI provider not configured</h2>
      <p className="dv2-body-copy">
        The dossier service answered, but no AI provider is configured on the backend. No research was run and no
        content was generated — nothing below is a placeholder or a sample.
      </p>
      <div className="dv2-not-configured-steps">
        <p><strong>What to do</strong></p>
        <ol>
          <li>Configure an AI provider in the backend environment.</li>
          <li>Restart the API service so it picks up the configuration.</li>
          <li>Start the run again.</li>
        </ol>
      </div>
      {error.message && error.message !== "AI provider not configured" && (
        <p className="dv2-error-detail">Service detail: {error.message}</p>
      )}
      <button type="button" className="dv2-button dv2-button-primary" onClick={onRetry}>
        <RefreshCw size={15} /> Retry start
      </button>
    </section>
  );
}

export function GenericErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <section className="dv2-paper dv2-generic-error" role="alert">
      <AlertTriangle size={20} />
      <div>
        <h2 className="dv2-section-title">We couldn&apos;t complete that request</h2>
        <p className="dv2-body-copy">{message}</p>
        {onRetry && (
          <button type="button" className="dv2-button dv2-button-quiet" onClick={onRetry}>
            <RefreshCw size={14} /> Try again
          </button>
        )}
      </div>
    </section>
  );
}
