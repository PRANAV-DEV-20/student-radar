"use client";

import React from "react";
import { Check, ListChecks } from "lucide-react";
import { ClaimText } from "./EvidenceChips";

export interface RoadmapEntry {
  id: string;
  text: string;
  effort: string;
  section: string;
  added: boolean;
}

interface RoadmapChecklistProps {
  entries: RoadmapEntry[];
  doneMap: Record<string, boolean>;
  onToggle: (entry: RoadmapEntry, done: boolean) => void;
  onOpenEvidence: (refId: string) => void;
}

export default function RoadmapChecklist({ entries, doneMap, onToggle, onOpenEvidence }: RoadmapChecklistProps) {
  if (!entries.length) {
    return (
      <div className="dv2-special-empty">
        <ListChecks size={16} />
        <p>No roadmap items were returned. Add a gap from the ranked board to create one.</p>
      </div>
    );
  }

  const doneCount = entries.filter((entry) => doneMap[entry.id]).length;

  return (
    <div className="dv2-roadmap">
      <div className="dv2-special-head">
        <p className="dv2-eyebrow">Working checklist</p>
        <p className="dv2-fineprint">
          {doneCount} of {entries.length} done · toggles are saved to this run&apos;s roadmap section.
        </p>
      </div>
      <ul className="dv2-checklist">
        {entries.map((entry) => {
          const done = Boolean(doneMap[entry.id]);
          return (
            <li key={entry.id} className={done ? "is-done" : ""}>
              <label>
                <input
                  type="checkbox"
                  checked={done}
                  onChange={(event) => onToggle(entry, event.target.checked)}
                />
                <span className="dv2-checkbox-face">{done && <Check size={13} />}</span>
                <span className="dv2-checklist-text">
                  <ClaimText text={entry.text} onOpen={onOpenEvidence} />
                  <span className="dv2-checklist-meta">
                    <span className="dv2-mini-chip">effort: {entry.effort || "unknown"}</span>
                    {entry.added && <span className="dv2-mini-chip is-added">added from gaps</span>}
                  </span>
                </span>
              </label>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
