"use client";

import React from "react";
import { ArrowDownRight, Compass, Gauge, ShieldAlert, Sparkles } from "lucide-react";
import { ClaimText } from "./EvidenceChips";
import { Section } from "@/lib/dossierV2Api";

interface ExecutiveBriefProps {
  section?: Section;
  onOpenEvidence: (refId: string) => void;
  onJumpToQuestions: () => void;
}

interface BriefData {
  verdict: string;
  strongest: string;
  risk: string;
  moves: string[];
  movesSource: string;
}

const PATTERNS = {
  verdict: ["verdict", "bottom line", "overall assessment"],
  strongest: ["strongest angle", "strongest", "differentiator"],
  risk: ["biggest risk", "primary risk", "main risk", "largest risk"],
  moves: ["top 3", "next 3", "next moves", "next steps", "immediate actions"],
};

function matches(text: string, patterns: string[]): boolean {
  const lower = text.toLowerCase();
  return patterns.some((pattern) => lower.includes(pattern));
}

function splitMoves(text: string): string[] {
  return text
    .split(/\n|\(?\d+[.)]\s*/)
    .map((part) => part.trim())
    .filter((part) => part.length > 0)
    .slice(0, 3);
}

function extractBrief(section: Section | undefined): BriefData {
  if (!section) {
    return { verdict: "", strongest: "", risk: "", moves: [], movesSource: "" };
  }
  const items = section.items || [];
  const verdictItem = items.find((item) => matches(`${item.id} ${item.text}`, PATTERNS.verdict));
  const strongestItem = items.find((item) => matches(`${item.id} ${item.text}`, PATTERNS.strongest));
  const riskItem = items.find((item) => matches(`${item.id} ${item.text}`, PATTERNS.risk));
  const movesItem = items.find((item) => matches(`${item.id} ${item.text}`, PATTERNS.moves));

  let moves = movesItem ? splitMoves(movesItem.text) : [];
  let movesSource = movesItem ? "From the brief's next-moves item" : "";
  if (!moves.length) {
    moves = items
      .filter((item) => item.label === "recommendation")
      .slice(0, 3)
      .map((item) => item.text);
    movesSource = moves.length ? "Top recommendations from this run" : "";
  }

  return {
    verdict: verdictItem?.text || "",
    strongest: strongestItem?.text || "",
    risk: riskItem?.text || "",
    moves,
    movesSource,
  };
}

function confidencePercent(confidence: string | undefined): number {
  if (confidence === "high") return 100;
  if (confidence === "medium") return 64;
  if (confidence === "low") return 32;
  return 0;
}

function Meter({ confidence }: { confidence: string | undefined }) {
  const percent = confidencePercent(confidence);
  return (
    <div className="dv2-meter" aria-label={`Confidence: ${confidence || "not reported"}`}>
      <div className="dv2-meter-track">
        <div className={`dv2-meter-fill dv2-meter-${confidence || "unknown"}`} style={{ width: `${percent}%` }} />
      </div>
      <span className="dv2-meter-label">{confidence ? `${confidence} confidence` : "confidence not reported"}</span>
    </div>
  );
}

function Field({
  icon,
  label,
  text,
  onOpenEvidence,
}: {
  icon: React.ReactNode;
  label: string;
  text: string;
  onOpenEvidence: (refId: string) => void;
}) {
  return (
    <div className="dv2-brief-field">
      <p className="dv2-brief-label">{icon}{label}</p>
      {text ? (
        <p className="dv2-brief-text"><ClaimText text={text} onOpen={onOpenEvidence} /></p>
      ) : (
        <p className="dv2-brief-empty">Not reported in this run.</p>
      )}
    </div>
  );
}

export default function ExecutiveBrief({ section, onOpenEvidence, onJumpToQuestions }: ExecutiveBriefProps) {
  const brief = extractBrief(section);
  const hasSection = Boolean(section);

  return (
    <article className="dv2-paper dv2-brief">
      <div className="dv2-brief-head">
        <div>
          <p className="dv2-eyebrow">Pinned · executive brief</p>
          <h2 className="dv2-brief-title">The one-page read</h2>
        </div>
        <div className="dv2-brief-confidence">
          <Gauge size={16} />
          <Meter confidence={section?.confidence} />
        </div>
      </div>

      {!hasSection ? (
        <p className="dv2-brief-empty dv2-brief-missing">
          The executive brief has not been written yet. It is generated last and will appear here when the run reaches it.
        </p>
      ) : (
        <>
          <div className="dv2-brief-grid">
            <Field
              icon={<Compass size={14} />}
              label="Verdict"
              text={brief.verdict}
              onOpenEvidence={onOpenEvidence}
            />
            <Field
              icon={<Sparkles size={14} />}
              label="Strongest angle"
              text={brief.strongest}
              onOpenEvidence={onOpenEvidence}
            />
            <Field
              icon={<ShieldAlert size={14} />}
              label="Biggest risk"
              text={brief.risk}
              onOpenEvidence={onOpenEvidence}
            />
          </div>

          <div className="dv2-brief-moves">
            <p className="dv2-brief-label"><ArrowDownRight size={14} /> Top 3 next moves</p>
            {brief.moves.length ? (
              <ol>
                {brief.moves.map((move, index) => (
                  <li key={`${index}-${move.slice(0, 24)}`}>
                    <span className="dv2-move-index">{index + 1}</span>
                    <span><ClaimText text={move} onOpen={onOpenEvidence} /></span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="dv2-brief-empty">No next moves were reported in this run.</p>
            )}
            {brief.movesSource && <p className="dv2-fineprint">{brief.movesSource}</p>}
          </div>

          {section?.summary && (
            <div className="dv2-brief-summary">
              <p className="dv2-eyebrow">Section summary, verbatim</p>
              <p><ClaimText text={section.summary} onOpen={onOpenEvidence} /></p>
            </div>
          )}
        </>
      )}

      <button type="button" className="dv2-text-link" onClick={onJumpToQuestions}>
        Jump to open questions & missing evidence →
      </button>
    </article>
  );
}
