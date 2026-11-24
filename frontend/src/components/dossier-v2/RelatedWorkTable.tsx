"use client";

import React, { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, Columns3 } from "lucide-react";
import CompareModal, { CompareRow } from "./CompareModal";
import { ClaimText } from "./EvidenceChips";
import {
  cellToString,
  normalizeColumns,
  normalizeRows,
  Section,
} from "@/lib/dossierV2Api";

interface RelatedWorkTableProps {
  section?: Section;
  ideaSummary: string;
  onOpenEvidence: (refId: string) => void;
}

function pickTitle(columns: string[], cells: string[]): string {
  const preferred = ["title", "name", "work", "paper", "project", "source"];
  for (const key of preferred) {
    const index = columns.findIndex((column) => column.toLowerCase().includes(key));
    if (index >= 0 && cells[index]) return cells[index];
  }
  return cells.find((cell) => cell.trim()) || "Untitled related work";
}

export default function RelatedWorkTable({ section, ideaSummary, onOpenEvidence }: RelatedWorkTableProps) {
  const [sortIndex, setSortIndex] = useState<number | null>(null);
  const [sortAsc, setSortAsc] = useState(true);
  const [compareRow, setCompareRow] = useState<CompareRow | null>(null);

  const table = useMemo(() => {
    if (!section?.tables?.length) return null;
    return (
      section.tables.find((item) => /related|compar|work|prior/i.test(item.title || "")) || section.tables[0]
    );
  }, [section]);

  const columns = useMemo(() => normalizeColumns(table?.columns || []), [table]);
  const baseRows = useMemo(() => normalizeRows(table?.rows || [], columns), [table, columns]);

  const rows = useMemo(() => {
    if (sortIndex === null) return baseRows;
    return [...baseRows].sort((a, b) => {
      const left = (a[sortIndex] || "").toLowerCase();
      const right = (b[sortIndex] || "").toLowerCase();
      const result = left.localeCompare(right);
      return sortAsc ? result : -result;
    });
  }, [baseRows, sortIndex, sortAsc]);

  const toggleSort = (index: number) => {
    if (sortIndex === index) {
      setSortAsc((current) => !current);
    } else {
      setSortIndex(index);
      setSortAsc(true);
    }
  };

  if (!table || !columns.length || !baseRows.length) {
    return (
      <div className="dv2-special-empty">
        <Columns3 size={16} />
        <p>No related-work table was returned in this run. Claims below may still describe prior art — check their evidence.</p>
      </div>
    );
  }

  return (
    <div className="dv2-related">
      <div className="dv2-special-head">
        <p className="dv2-eyebrow">Comparative table</p>
        <p className="dv2-fineprint">Click a column to sort. Compare places a row next to your idea summary.</p>
      </div>
      <div className="dv2-table-scroll">
        <table className="dv2-table">
          <thead>
            <tr>
              {columns.map((column, index) => (
                <th key={`${column}-${index}`} scope="col">
                  <button type="button" onClick={() => toggleSort(index)} title={`Sort by ${column}`}>
                    {column}
                    {sortIndex === index ? (
                      sortAsc ? <ArrowUp size={12} /> : <ArrowDown size={12} />
                    ) : (
                      <ArrowUpDown size={12} className="dv2-sort-idle" />
                    )}
                  </button>
                </th>
              ))}
              <th scope="col"><span className="dv2-sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((cells, rowIndex) => (
              <tr key={rowIndex}>
                {cells.map((cell, cellIndex) => (
                  <td key={cellIndex}>
                    <ClaimText text={cell} onOpen={onOpenEvidence} />
                  </td>
                ))}
                <td>
                  <button
                    type="button"
                    className="dv2-button dv2-button-quiet dv2-button-tiny"
                    onClick={() =>
                      setCompareRow({
                        title: pickTitle(columns, cells),
                        columns,
                        cells: cells.map((cell) => cellToString(cell)),
                      })
                    }
                  >
                    Compare
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <CompareModal
        open={Boolean(compareRow)}
        ideaSummary={ideaSummary}
        row={compareRow}
        onClose={() => setCompareRow(null)}
      />
    </div>
  );
}
