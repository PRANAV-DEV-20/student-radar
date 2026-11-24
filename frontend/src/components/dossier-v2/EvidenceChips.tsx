"use client";

import React from "react";
import { evidenceRefsInText, normalizeEvidenceRef } from "@/lib/dossierV2Api";

interface EvidenceChipProps {
  refId: string;
  onOpen: (refId: string) => void;
}

export function EvidenceChip({ refId, onOpen }: EvidenceChipProps) {
  return (
    <button
      type="button"
      className="dv2-evidence-chip"
      onClick={() => onOpen(normalizeEvidenceRef(refId))}
      title={`Open evidence ${refId}`}
    >
      {refId}
    </button>
  );
}

interface EvidenceChipListProps {
  refs: string[];
  onOpen: (refId: string) => void;
}

export function EvidenceChipList({ refs, onOpen }: EvidenceChipListProps) {
  if (!refs.length) return <span className="dv2-no-evidence">no evidence cited</span>;
  return (
    <span className="dv2-evidence-list">
      {refs.map((refId) => (
        <EvidenceChip key={refId} refId={refId} onOpen={onOpen} />
      ))}
    </span>
  );
}

interface ClaimTextProps {
  text: string;
  onOpen: (refId: string) => void;
}

/** Renders prose while turning inline [E#] citations into actionable chips. */
export function ClaimText({ text, onOpen }: ClaimTextProps) {
  const tokens = text.split(/(\[E\d+\])/g);
  return (
    <span>
      {tokens.map((token, index) =>
        /^\[E\d+\]$/.test(token) ? (
          <EvidenceChip key={`${token}-${index}`} refId={token} onOpen={onOpen} />
        ) : (
          <React.Fragment key={`text-${index}`}>{token}</React.Fragment>
        ),
      )}
    </span>
  );
}

export function InlineEvidenceText({ text, onOpen }: ClaimTextProps) {
  const refs = evidenceRefsInText(text);
  return <EvidenceChipList refs={refs} onOpen={onOpen} />;
}
