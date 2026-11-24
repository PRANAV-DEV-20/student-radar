"use client";

import React from "react";
import { Layers, Wallet } from "lucide-react";
import { ClaimText } from "./EvidenceChips";
import { evidenceRefsInText, normalizeColumns, normalizeRows, Section } from "@/lib/dossierV2Api";

interface TechStackCardsProps {
  section?: Section;
  onOpenEvidence: (refId: string) => void;
}

interface StackLayer {
  layer: string;
  choice: string;
  alternatives: string[];
  cost: string;
  effort: string;
  text: string;
}

function findColumn(columns: string[], candidates: string[]): number {
  return columns.findIndex((column) =>
    candidates.some((candidate) => column.toLowerCase().includes(candidate)),
  );
}

function valueAt(cells: string[], index: number): string {
  return index >= 0 && index < cells.length ? cells[index].trim() : "";
}

function firstSentence(text: string): string {
  const match = text.match(/^[^.!?\n]+[.!?]?/);
  return (match ? match[0] : text).trim();
}

function extractLayers(section: Section | undefined): StackLayer[] {
  if (!section) return [];
  const layers: StackLayer[] = [];

  (section.tables || []).forEach((table) => {
    const columns = normalizeColumns(table.columns || []);
    const rows = normalizeRows(table.rows || [], columns);
    const layerIndex = findColumn(columns, ["layer", "tier", "category"]);
    const choiceIndex = findColumn(columns, ["technology", "tool", "choice", "name", "stack"]);
    const altIndex = findColumn(columns, ["alternative", "alt", "option"]);
    const costIndex = findColumn(columns, ["cost", "price", "pricing", "usd"]);
    const effortIndex = findColumn(columns, ["effort", "learning"]);

    rows.forEach((cells, rowIndex) => {
      const choice = valueAt(cells, choiceIndex) || valueAt(cells, 0);
      if (!choice) return;
      layers.push({
        layer: valueAt(cells, layerIndex) || `Layer ${rowIndex + 1}`,
        choice,
        alternatives: valueAt(cells, altIndex)
          .split(/,|\|/)
          .map((item) => item.trim())
          .filter(Boolean),
        cost: valueAt(cells, costIndex),
        effort: valueAt(cells, effortIndex),
        text: cells.join(" · "),
      });
    });
  });

  if (!layers.length) {
    (section.items || []).forEach((item, index) => {
      layers.push({
        layer: item.layer || `Layer ${index + 1}`,
        choice: firstSentence(item.text || ""),
        alternatives: Array.isArray(item.alternatives) ? item.alternatives.map(String) : [],
        cost: typeof item.cost === "string" ? item.cost : "",
        effort: typeof item.effort === "string" ? item.effort : "",
        text: item.text || "",
      });
    });
  }

  return layers;
}

export default function TechStackCards({ section, onOpenEvidence }: TechStackCardsProps) {
  const layers = React.useMemo(() => extractLayers(section), [section]);

  if (!layers.length) {
    return (
      <div className="dv2-special-empty">
        <Layers size={16} />
        <p>No stack layers were returned in this run.</p>
      </div>
    );
  }

  return (
    <div className="dv2-stack-wrap">
      <div className="dv2-special-head">
        <p className="dv2-eyebrow">Layered stack</p>
        <p className="dv2-fineprint">Focus or hover a card to reveal alternatives reported by the run.</p>
      </div>
      <div className="dv2-stack-grid">
        {layers.map((layer, index) => (
          <article key={`${layer.layer}-${index}`} className="dv2-stack-card" tabIndex={0}>
            <div className="dv2-stack-card-top">
              <span className="dv2-stack-layer">{layer.layer}</span>
              <span className="dv2-stack-number">{String(index + 1).padStart(2, "0")}</span>
            </div>
            <h4 className="dv2-stack-choice"><ClaimText text={layer.choice} onOpen={onOpenEvidence} /></h4>
            <div className="dv2-stack-badges">
              <span className={`dv2-mini-chip ${layer.cost ? "is-cost" : "is-unknown"}`}>
                <Wallet size={11} /> {layer.cost ? `cost: ${layer.cost}` : "cost not reported"}
              </span>
              <span className={`dv2-mini-chip ${layer.effort ? "is-effort" : "is-unknown"}`}>
                learning effort: {layer.effort || "not reported"}
              </span>
            </div>
            <div className="dv2-stack-alt">
              <p className="dv2-eyebrow">Alternatives</p>
              {layer.alternatives.length ? (
                <ul>
                  {layer.alternatives.map((alternative, altIndex) => (
                    <li key={`${alternative}-${altIndex}`}><ClaimText text={alternative} onOpen={onOpenEvidence} /></li>
                  ))}
                </ul>
              ) : (
                <p className="dv2-muted">No alternatives reported for this layer.</p>
              )}
              {evidenceRefsInText(layer.text).length > 0 && (
                <p className="dv2-fineprint">Citations in this row: {evidenceRefsInText(layer.text).join(" ")}</p>
              )}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
