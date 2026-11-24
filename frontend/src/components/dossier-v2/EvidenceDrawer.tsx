"use client";

import React, { useEffect } from "react";
import { ExternalLink, X } from "lucide-react";
import { Evidence, normalizeEvidenceRef } from "@/lib/dossierV2Api";

interface EvidenceDrawerProps {
  open: boolean;
  refId: string | null;
  evidence: Evidence[];
  onClose: () => void;
}

export default function EvidenceDrawer({ open, refId, evidence, onClose }: EvidenceDrawerProps) {
  const normalizedRef = refId ? normalizeEvidenceRef(refId) : null;
  const found = evidence.find((entry) => normalizeEvidenceRef(entry.ref) === normalizedRef) || null;

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  return (
    <>
      <div
        className={`dv2-drawer-scrim ${open ? "is-open" : ""}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={`dv2-drawer ${open ? "is-open" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={`Evidence ${refId || ""}`}
        aria-hidden={!open}
      >
        <div className="dv2-drawer-head">
          <div>
            <p className="dv2-eyebrow">Evidence record</p>
            <h2 className="dv2-drawer-title">{refId || "No citation selected"}</h2>
          </div>
          <button type="button" className="dv2-icon-button" onClick={onClose} aria-label="Close evidence drawer">
            <X size={18} />
          </button>
        </div>

        {!found ? (
          <div className="dv2-drawer-body">
            <p className="dv2-muted">
              {refId
                ? `${refId} is cited in the dossier but was not included in this run's evidence set.`
                : "Select an [E#] chip in any claim to inspect its source passage."}
            </p>
          </div>
        ) : (
          <div className="dv2-drawer-body">
            <section className="dv2-drawer-section">
              <p className="dv2-eyebrow">Title</p>
              <p className="dv2-drawer-lead">{found.title || "Untitled source"}</p>
            </section>

            <dl className="dv2-detail-grid">
              <div>
                <dt>Source</dt>
                <dd>{found.source || "not reported"}</dd>
              </div>
              <div>
                <dt>Quality</dt>
                <dd>{found.source_quality || "not reported"}</dd>
              </div>
              <div>
                <dt>Retrieved</dt>
                <dd>{found.retrieved_at || "not reported"}</dd>
              </div>
              <div>
                <dt>Relevance</dt>
                <dd>{found.relevance === undefined || found.relevance === null ? "not reported" : String(found.relevance)}</dd>
              </div>
              <div>
                <dt>Question</dt>
                <dd>{found.question_id || "not reported"}</dd>
              </div>
            </dl>

            <section className="dv2-drawer-section">
              <p className="dv2-eyebrow">Exact passage</p>
              <blockquote className="dv2-passage">{found.passage || "No passage was stored for this reference."}</blockquote>
            </section>

            {found.url ? (
              <a
                className="dv2-primary-link"
                href={found.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open source <ExternalLink size={14} />
              </a>
            ) : (
              <p className="dv2-muted">No source URL was stored for this reference.</p>
            )}
          </div>
        )}
      </aside>
    </>
  );
}
