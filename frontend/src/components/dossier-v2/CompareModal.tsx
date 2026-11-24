"use client";

import React, { useEffect } from "react";
import { ArrowLeftRight, X } from "lucide-react";

export interface CompareRow {
  title: string;
  columns: string[];
  cells: string[];
}

interface CompareModalProps {
  open: boolean;
  ideaSummary: string;
  row: CompareRow | null;
  onClose: () => void;
}

export default function CompareModal({ open, ideaSummary, row, onClose }: CompareModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="dv2-modal-scrim" onMouseDown={onClose}>
      <div
        className="dv2-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Compare idea with related work"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="dv2-modal-head">
          <div>
            <p className="dv2-eyebrow">Side by side</p>
            <h2 className="dv2-section-title">Idea vs. related work</h2>
          </div>
          <button type="button" className="dv2-icon-button" onClick={onClose} aria-label="Close comparison">
            <X size={18} />
          </button>
        </div>

        <div className="dv2-compare-grid">
          <section className="dv2-compare-side">
            <p className="dv2-compare-label"><ArrowLeftRight size={13} /> Your idea</p>
            <p className="dv2-compare-copy">
              {ideaSummary || "No idea summary was generated in this run."}
            </p>
          </section>
          <section className="dv2-compare-side">
            <p className="dv2-compare-label"><ArrowLeftRight size={13} /> Related work</p>
            <h3 className="dv2-compare-title">{row?.title || "No row selected"}</h3>
            {row && row.cells.length > 0 ? (
              <dl className="dv2-compare-detail">
                {row.cells.map((cell, index) => (
                  <React.Fragment key={`${index}-${row.columns[index] || "cell"}`}>
                    <dt>{row.columns[index] || `Field ${index + 1}`}</dt>
                    <dd>{cell || "—"}</dd>
                  </React.Fragment>
                ))}
              </dl>
            ) : (
              <p className="dv2-muted">No fields were supplied for this row.</p>
            )}
          </section>
        </div>
        <p className="dv2-fineprint">
          Comparison is a reading aid, not a novelty verdict. Check the cited evidence before drawing conclusions.
        </p>
      </div>
    </div>
  );
}
