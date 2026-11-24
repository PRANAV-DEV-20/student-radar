"use client";

import React from "react";
import { Plus, Target } from "lucide-react";
import { ClaimText } from "./EvidenceChips";
import { SECTION_TITLES, SectionItem, SectionKey } from "@/lib/dossierV2Api";

export interface RankedEntry {
  id: string;
  item: SectionItem;
  source: SectionKey;
}

interface RankedBoardProps {
  entries: RankedEntry[];
  onAdd: (entry: RankedEntry) => void;
  addingId: string | null;
  onOpenEvidence: (refId: string) => void;
}

function severityRank(value: string | undefined): number {
  const normalized = (value || "").toLowerCase();
  if (normalized === "critical") return 4;
  if (normalized === "high") return 3;
  if (normalized === "medium") return 2;
  if (normalized === "low") return 1;
  return 0;
}

function effortRank(value: string | undefined): number {
  const normalized = (value || "").toLowerCase();
  if (normalized === "high") return 3;
  if (normalized === "medium") return 2;
  if (normalized === "low") return 1;
  return 0;
}

function toneForRank(rank: number): string {
  if (rank >= 4) return "critical";
  if (rank === 3) return "high";
  if (rank === 2) return "medium";
  if (rank === 1) return "low";
  return "unknown";
}

function quadrant(entry: RankedEntry): string {
  const severity = severityRank(entry.item.severity);
  const effort = effortRank(entry.item.effort);
  if (severity >= 3 && effort > 0 && effort <= 2) return "first";
  if (severity >= 3) return "heavy";
  if (effort > 0 && effort <= 2) return "quick";
  return "monitor";
}

const QUADRANTS: Array<{ key: string; title: string; hint: string }> = [
  { key: "first", title: "Address first", hint: "high severity · low–medium effort" },
  { key: "heavy", title: "High impact, heavier lift", hint: "high severity · high or unknown effort" },
  { key: "quick", title: "Quick hygiene", hint: "lower severity · low–medium effort" },
  { key: "monitor", title: "Monitor", hint: "lower severity · heavier or unknown effort" },
];

export default function RankedBoard({ entries, onAdd, addingId, onOpenEvidence }: RankedBoardProps) {
  const sorted = React.useMemo(() => {
    return [...entries].sort((a, b) => {
      const severityDiff = severityRank(b.item.severity) - severityRank(a.item.severity);
      if (severityDiff !== 0) return severityDiff;
      return effortRank(a.item.effort) - effortRank(b.item.effort);
    });
  }, [entries]);

  if (!entries.length) {
    return (
      <div className="dv2-special-empty">
        <Target size={16} />
        <p>No ranked gaps or risks were returned in this run.</p>
      </div>
    );
  }

  return (
    <div className="dv2-board">
      <div className="dv2-special-head">
        <p className="dv2-eyebrow">Severity × effort board</p>
        <p className="dv2-fineprint">Ranking uses the severity and effort labels returned by the API. Unknown values are shown as such.</p>
      </div>

      <div className="dv2-quadrants">
        {QUADRANTS.map((quadrantDef) => {
          const items = sorted.filter((entry) => quadrant(entry) === quadrantDef.key);
          return (
            <section key={quadrantDef.key} className={`dv2-quadrant dv2-quadrant-${quadrantDef.key}`}>
              <h4>{quadrantDef.title}</h4>
              <p>{quadrantDef.hint}</p>
              <ul>
                {items.length ? (
                  items.map((entry) => (
                    <li key={entry.id} title={entry.item.text}>
                      {entry.item.id || "item"}
                    </li>
                  ))
                ) : (
                  <li className="dv2-quadrant-empty">none</li>
                )}
              </ul>
            </section>
          );
        })}
      </div>

      <ol className="dv2-ranked-list">
        {sorted.map((entry, index) => (
          <li key={entry.id} className="dv2-ranked-item">
            <span className="dv2-rank-number">{String(index + 1).padStart(2, "0")}</span>
            <div className="dv2-ranked-main">
              <div className="dv2-ranked-meta">
                <span className={`dv2-mini-chip dv2-severity-${toneForRank(severityRank(entry.item.severity))}`}>
                  severity: {entry.item.severity || "unknown"}
                </span>
                <span className={`dv2-mini-chip dv2-effort-${toneForRank(effortRank(entry.item.effort))}`}>
                  effort: {entry.item.effort || "unknown"}
                </span>
                <span className="dv2-mini-chip">{SECTION_TITLES[entry.source] || entry.source}</span>
              </div>
              <p className="dv2-claim-text"><ClaimText text={entry.item.text} onOpen={onOpenEvidence} /></p>
            </div>
            <button
              type="button"
              className="dv2-button dv2-button-quiet dv2-button-tiny"
              onClick={() => onAdd(entry)}
              disabled={addingId === entry.id}
            >
              <Plus size={13} /> {addingId === entry.id ? "Adding…" : "Add to roadmap"}
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
