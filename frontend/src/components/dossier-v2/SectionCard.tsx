"use client";

import React from "react";
import { AlertTriangle, Lock, Pencil, RotateCw, Save, Unlock, X } from "lucide-react";
import { ClaimText, EvidenceChipList } from "./EvidenceChips";
import {
  asDossierV2Error,
  cellToString,
  normalizeColumns,
  normalizeRows,
  SECTION_KEYS,
  SECTION_TITLES,
  Section,
  SectionItem,
  SectionKey,
  SectionPatchBody,
  sectionContentPayload,
} from "@/lib/dossierV2Api";

interface SectionCardProps {
  sectionKey: SectionKey;
  section?: Section;
  onOpenEvidence: (refId: string) => void;
  onDeepen: (key: SectionKey) => void;
  deepening: boolean;
  onPatch: (key: SectionKey, body: SectionPatchBody) => Promise<void>;
  children?: React.ReactNode;
  hideItems?: boolean;
  hideTables?: boolean;
}

const LABEL_LABELS: Record<string, string> = {
  grounded: "Grounded",
  input: "From you",
  inference: "Inference",
  recommendation: "Recommendation",
};

function StatusBadge({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <span className={`dv2-status-badge dv2-badge-${tone}`}>
      {label}: {value}
    </span>
  );
}

export default function SectionCard({
  sectionKey,
  section,
  onOpenEvidence,
  onDeepen,
  deepening,
  onPatch,
  children,
  hideItems,
  hideTables,
}: SectionCardProps) {
  const [editing, setEditing] = React.useState(false);
  const [draftSummary, setDraftSummary] = React.useState("");
  const [draftItems, setDraftItems] = React.useState<SectionItem[]>([]);
  const [saving, setSaving] = React.useState(false);
  const [actionError, setActionError] = React.useState("");
  const index = SECTION_KEYS.indexOf(sectionKey) + 1;

  React.useEffect(() => {
    setDraftSummary(section?.summary || "");
    setDraftItems(section?.items || []);
    setEditing(false);
    setActionError("");
  }, [section]);

  const beginEdit = () => {
    setDraftSummary(section?.summary || "");
    setDraftItems(section?.items || []);
    setActionError("");
    setEditing(true);
  };

  const save = async () => {
    if (!section) return;
    setSaving(true);
    setActionError("");
    try {
      await onPatch(sectionKey, {
        content: sectionContentPayload(section, { summary: draftSummary, items: draftItems }),
        locked: Boolean(section.locked),
      });
      setEditing(false);
    } catch (err) {
      setActionError(asDossierV2Error(err).message);
    } finally {
      setSaving(false);
    }
  };

  const toggleLock = async () => {
    if (!section) return;
    setActionError("");
    try {
      await onPatch(sectionKey, {
        content: sectionContentPayload(section),
        locked: !section.locked,
      });
    } catch (err) {
      setActionError(asDossierV2Error(err).message);
    }
  };

  const limitations = section?.limitations || [];
  const showLimitationBanner = Boolean(section) && (section?.coverage !== "strong" || limitations.length > 0);

  return (
    <section
      id={`dv2-section-${sectionKey}`}
      data-dv2-section={sectionKey}
      className="dv2-paper dv2-section"
    >
      <header className="dv2-section-head">
        <div className="dv2-section-heading">
          <span className="dv2-section-index">{String(index).padStart(2, "0")}</span>
          <div>
            <h2 className="dv2-section-title">{SECTION_TITLES[sectionKey]}</h2>
            <p className="dv2-section-key">{sectionKey}</p>
          </div>
        </div>
        <div className="dv2-section-status">
          {section ? (
            <>
              <StatusBadge label="confidence" value={section.confidence || "unknown"} tone={section.confidence || "unknown"} />
              <StatusBadge label="coverage" value={section.coverage || "unknown"} tone={section.coverage || "unknown"} />
              {section.locked && <span className="dv2-status-badge dv2-badge-locked"><Lock size={11} /> locked</span>}
            </>
          ) : (
            <span className="dv2-status-badge dv2-badge-unknown">not written</span>
          )}
        </div>
      </header>

      <div className="dv2-section-tools">
        <button
          type="button"
          className="dv2-button dv2-button-quiet dv2-button-tiny"
          onClick={() => (editing ? setEditing(false) : beginEdit())}
          disabled={!section || section.locked || editing}
        >
          <Pencil size={13} /> Edit
        </button>
        <button
          type="button"
          className="dv2-button dv2-button-quiet dv2-button-tiny"
          onClick={() => void toggleLock()}
          disabled={!section}
        >
          {section?.locked ? <Unlock size={13} /> : <Lock size={13} />}
          {section?.locked ? "Unlock" : "Lock"}
        </button>
        <button
          type="button"
          className="dv2-button dv2-button-quiet dv2-button-tiny"
          onClick={() => onDeepen(sectionKey)}
          disabled={deepening || !section}
        >
          <RotateCw size={13} className={deepening ? "dv2-spin" : ""} />
          {deepening ? "Deepening…" : "Deepen this section"}
        </button>
        {editing && (
          <>
            <button
              type="button"
              className="dv2-button dv2-button-primary dv2-button-tiny"
              onClick={() => void save()}
              disabled={saving}
            >
              <Save size={13} /> {saving ? "Saving…" : "Save"}
            </button>
            <button type="button" className="dv2-button dv2-button-quiet dv2-button-tiny" onClick={() => setEditing(false)}>
              <X size={13} /> Cancel
            </button>
          </>
        )}
      </div>

      {actionError && <p className="dv2-inline-error" role="alert">{actionError}</p>}

      {!section ? (
        <div className="dv2-missing-section">
          <AlertTriangle size={16} />
          <p>
            This section has not been written in the current run. No placeholder content is shown — it will appear here
            when generated, or you can use “Deepen this section” to request more research.
          </p>
        </div>
      ) : (
        <>
          {showLimitationBanner && (
            <div className="dv2-limitations" role="status">
              <div>
                <AlertTriangle size={15} />
                <strong>{section.coverage === "strong" ? "Limitations noted" : `Coverage: ${section.coverage || "not reported"}`}</strong>
              </div>
              {limitations.length ? (
                <ul>
                  {limitations.map((limitation, index) => (
                    <li key={`${index}-${limitation.slice(0, 20)}`}>{limitation}</li>
                  ))}
                </ul>
              ) : (
                <p>No limitations were listed for this section. Treat sparse coverage as incomplete.</p>
              )}
            </div>
          )}

          <div className="dv2-section-summary">
            <p className="dv2-eyebrow">Summary</p>
            {editing ? (
              <textarea
                value={draftSummary}
                onChange={(event) => setDraftSummary(event.target.value)}
                rows={3}
                aria-label={`${SECTION_TITLES[sectionKey]} summary`}
              />
            ) : section.summary ? (
              <p className="dv2-summary-copy"><ClaimText text={section.summary} onOpen={onOpenEvidence} /></p>
            ) : (
              <p className="dv2-muted">No summary was returned for this section.</p>
            )}
          </div>

          {children}

          {!hideItems && section.items.length > 0 && (
            <div className="dv2-claims">
              <p className="dv2-eyebrow">Claims & provenance</p>
              <ul>
                {section.items.map((item, itemIndex) => (
                  <li key={item.id || `${sectionKey}-${itemIndex}`} className="dv2-claim">
                    <div className="dv2-claim-meta">
                      <span className={`dv2-label-chip dv2-label-${String(item.label).toLowerCase()}`}>
                        {LABEL_LABELS[String(item.label)] || String(item.label)}
                      </span>
                      <span className="dv2-claim-id">{item.id || `item ${itemIndex + 1}`}</span>
                      {item.severity && <span className="dv2-mini-chip">severity: {String(item.severity)}</span>}
                      {item.effort && <span className="dv2-mini-chip">effort: {String(item.effort)}</span>}
                    </div>
                    {editing ? (
                      <textarea
                        value={draftItems[itemIndex]?.text ?? item.text}
                        onChange={(event) => {
                          setDraftItems((current) =>
                            current.map((draft, index) =>
                              index === itemIndex ? { ...draft, text: event.target.value } : draft,
                            ),
                          );
                        }}
                        rows={3}
                        aria-label={`Edit claim ${item.id || itemIndex + 1}`}
                      />
                    ) : (
                      <p className="dv2-claim-text"><ClaimText text={item.text} onOpen={onOpenEvidence} /></p>
                    )}
                    {item.reasoning && !editing && (
                      <p className="dv2-reasoning">
                        <strong>Reasoning:</strong> <ClaimText text={item.reasoning} onOpen={onOpenEvidence} />
                      </p>
                    )}
                    {!editing && item.evidence.length > 0 && (
                      <div className="dv2-claim-evidence">
                        <span>Cited:</span> <EvidenceChipList refs={item.evidence} onOpen={onOpenEvidence} />
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {!hideTables && section.tables.length > 0 && (
            <div className="dv2-generic-tables">
              {section.tables.map((table, tableIndex) => {
                const columns = normalizeColumns(table.columns || []);
                const rows = normalizeRows(table.rows || [], columns);
                return (
                  <div key={`${table.title}-${tableIndex}`} className="dv2-table-block">
                    <p className="dv2-eyebrow">{table.title || `Table ${tableIndex + 1}`}</p>
                    {rows.length ? (
                      <div className="dv2-table-scroll">
                        <table className="dv2-table">
                          <thead>
                            <tr>
                              {columns.map((column, index) => <th key={`${column}-${index}`}>{column}</th>)}
                            </tr>
                          </thead>
                          <tbody>
                            {rows.map((cells, rowIndex) => (
                              <tr key={rowIndex}>
                                {cells.map((cell, cellIndex) => (
                                  <td key={cellIndex}><ClaimText text={cellToString(cell)} onOpen={onOpenEvidence} /></td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p className="dv2-muted">No rows were returned for this table.</p>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {section.generated_by && (
            <footer className="dv2-generated">
              generated_by: <code>{section.generated_by.prompt || "unknown prompt"}</code>
              {" · "}<code>{section.generated_by.model || "unknown model"}</code>
            </footer>
          )}
        </>
      )}
    </section>
  );
}
