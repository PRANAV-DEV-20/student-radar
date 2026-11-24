"use client";

import React from "react";
import { SECTION_KEYS, SECTION_TITLES, Section, SectionKey } from "@/lib/dossierV2Api";

interface SectionNavProps {
  sections: Record<string, Section>;
  activeKey: SectionKey;
  onSelect: (key: SectionKey) => void;
}

function ConfidenceDot({ confidence, present }: { confidence?: string; present: boolean }) {
  const tone = !present ? "none" : confidence === "high" ? "high" : confidence === "medium" ? "medium" : confidence === "low" ? "low" : "none";
  return <span className={`dv2-confidence-dot is-${tone}`} title={confidence ? `${confidence} confidence` : "no confidence reported"} />;
}

function CoverageDots({ coverage, present }: { coverage?: string; present: boolean }) {
  const filled = !present ? 0 : coverage === "strong" ? 3 : coverage === "thin" ? 1 : 0;
  return (
    <span className="dv2-coverage-dots" title={coverage ? `${coverage} coverage` : "no coverage reported"}>
      {[0, 1, 2].map((index) => (
        <span key={index} className={index < filled ? "is-filled" : ""} />
      ))}
    </span>
  );
}

export default function SectionNav({ sections, activeKey, onSelect }: SectionNavProps) {
  return (
    <nav className="dv2-paper dv2-nav" aria-label="Dossier sections">
      <p className="dv2-eyebrow">Contents · 18 sections</p>
      <ol>
        {SECTION_KEYS.map((key, index) => {
          const section = sections[key];
          const present = Boolean(section);
          return (
            <li key={key}>
              <button
                type="button"
                className={`dv2-nav-item ${activeKey === key ? "is-active" : ""} ${!present ? "is-missing" : ""}`}
                onClick={() => onSelect(key)}
                aria-current={activeKey === key ? "true" : undefined}
              >
                <span className="dv2-nav-index">{String(index + 1).padStart(2, "0")}</span>
                <span className="dv2-nav-label">{SECTION_TITLES[key]}</span>
                <span className="dv2-nav-dots">
                  <ConfidenceDot confidence={section?.confidence} present={present} />
                  <CoverageDots coverage={section?.coverage} present={present} />
                </span>
              </button>
            </li>
          );
        })}
      </ol>
      <p className="dv2-nav-legend">
        <span><i className="dv2-confidence-dot is-high" /> high</span>
        <span><i className="dv2-confidence-dot is-medium" /> med</span>
        <span><i className="dv2-confidence-dot is-low" /> low</span>
      </p>
      <p className="dv2-nav-legend">
        <span className="dv2-coverage-dots"><i className="is-filled" /><i className="is-filled" /><i className="is-filled" /></span>
        <span>coverage: strong / thin / none</span>
      </p>
    </nav>
  );
}
