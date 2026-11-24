"use client";

import React, { useState } from "react";
import { ArrowRight, FileText, Github, Lightbulb, Loader2 } from "lucide-react";
import {
  DossierV2Error,
  InputType,
  RunMode,
  StartRunPayload,
  StudentProfile,
} from "@/lib/dossierV2Api";

interface RunInputFormProps {
  onStart: (payload: StartRunPayload) => void;
  isStarting: boolean;
  error: DossierV2Error | null;
}

const INPUT_TYPES: Array<{ value: InputType; label: string; hint: string; Icon: typeof Lightbulb }> = [
  { value: "idea", label: "Idea", hint: "Describe it in your own words", Icon: Lightbulb },
  { value: "github", label: "GitHub URL", hint: "Research an existing repository", Icon: Github },
  { value: "pdf_text", label: "PDF text", hint: "Paste extracted paper text", Icon: FileText },
];

const PERSONAS = ["tech_builder", "policy_law", "design_biotech", "business_finance"];

function parseList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function RunInputForm({ onStart, isStarting, error }: RunInputFormProps) {
  const [inputType, setInputType] = useState<InputType>("idea");
  const [rawContent, setRawContent] = useState("");
  const [persona, setPersona] = useState("tech_builder");
  const [mode, setMode] = useState<RunMode>("quick");
  const [skills, setSkills] = useState("");
  const [weeklyHours, setWeeklyHours] = useState("6");
  const [budget, setBudget] = useState("0");
  const [country, setCountry] = useState("");
  const [education, setEducation] = useState("undergraduate");
  const [goals, setGoals] = useState("");
  const [purpose, setPurpose] = useState<StudentProfile["purpose"]>("product");

  const notConfigured = error?.code === "AI_PROVIDER_NOT_CONFIGURED";

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!rawContent.trim() || isStarting) return;
    const profile: StudentProfile = {
      skills: parseList(skills),
      weekly_hours: Number.isFinite(Number(weeklyHours)) ? Number(weeklyHours) : 0,
      budget_usd: Number.isFinite(Number(budget)) ? Number(budget) : 0,
      country: country.trim(),
      education_level: education.trim(),
      goals: parseList(goals),
      purpose,
    };
    onStart({
      input_type: inputType,
      raw_content: rawContent.trim(),
      domain_persona: persona.trim() || "tech_builder",
      mode,
      profile,
    });
  };

  return (
    <section className="dv2-paper dv2-intake">
      <div className="dv2-intake-head">
        <div>
          <p className="dv2-eyebrow">LaunchPad dossier · v2</p>
          <h2 className="dv2-section-title">Start a grounded research run</h2>
          <p className="dv2-body-copy dv2-intake-subhead">
            Every claim in the resulting dossier carries a provenance label and, where possible, a source passage.
          </p>
        </div>
        <span className="dv2-mode-stamp">{mode === "deep" ? "DEEP · 10–20 questions" : "QUICK · 8–10 questions"}</span>
      </div>

      {error && (
        <div className={`dv2-form-alert ${notConfigured ? "is-config" : ""}`} role="alert">
          <strong>{notConfigured ? "AI provider not configured" : "Run could not start"}</strong>
          <span>
            {notConfigured
              ? "The backend is reachable but has no AI provider. No dossier was generated. Configure the provider, then retry."
              : error.message}
          </span>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <fieldset className="dv2-fieldset">
          <legend>Input type</legend>
          <div className="dv2-segmented" role="group" aria-label="Input type">
            {INPUT_TYPES.map(({ value, label, hint, Icon }) => (
              <button
                key={value}
                type="button"
                className={`dv2-segment ${inputType === value ? "is-active" : ""}`}
                onClick={() => setInputType(value)}
                aria-pressed={inputType === value}
              >
                <Icon size={15} />
                <span>
                  <strong>{label}</strong>
                  <small>{hint}</small>
                </span>
              </button>
            ))}
          </div>
        </fieldset>

        <label className="dv2-field">
          <span>
            {inputType === "github"
              ? "Repository URL"
              : inputType === "pdf_text"
                ? "Pasted paper text"
                : "Your idea"}
          </span>
          <textarea
            value={rawContent}
            onChange={(event) => setRawContent(event.target.value)}
            rows={inputType === "github" ? 2 : 4}
            placeholder={
              inputType === "github"
                ? "https://github.com/owner/repo"
                : inputType === "pdf_text"
                  ? "Paste the extracted text of the paper…"
                  : "What are you building, for whom, and what constraint matters most?"
            }
            required
            minLength={8}
          />
        </label>

        <div className="dv2-form-row">
          <label className="dv2-field">
            <span>Domain persona</span>
            <input
              list="dv2-personas"
              value={persona}
              onChange={(event) => setPersona(event.target.value)}
              placeholder="tech_builder"
            />
            <datalist id="dv2-personas">
              {PERSONAS.map((item) => <option key={item} value={item} />)}
            </datalist>
          </label>

          <fieldset className="dv2-fieldset dv2-mode-fieldset">
            <legend>Research mode</legend>
            <div className="dv2-segmented dv2-segmented-compact" role="group" aria-label="Research mode">
              <button
                type="button"
                className={`dv2-segment ${mode === "quick" ? "is-active" : ""}`}
                onClick={() => setMode("quick")}
                aria-pressed={mode === "quick"}
              >
                <strong>Quick</strong>
                <small>Fast coverage pass</small>
              </button>
              <button
                type="button"
                className={`dv2-segment ${mode === "deep" ? "is-active" : ""}`}
                onClick={() => setMode("deep")}
                aria-pressed={mode === "deep"}
              >
                <strong>Deep</strong>
                <small>Wider source sweep</small>
              </button>
            </div>
          </fieldset>
        </div>

        <div className="dv2-form-divider">
          <span>Your constraints</span>
          <small>These fields shape feasibility, stack and roadmap recommendations.</small>
        </div>

        <div className="dv2-profile-grid">
          <label className="dv2-field dv2-field-wide">
            <span>Skills <em>comma separated</em></span>
            <input
              value={skills}
              onChange={(event) => setSkills(event.target.value)}
              placeholder="TypeScript, Python, Figma"
            />
          </label>
          <label className="dv2-field">
            <span>Weekly hours</span>
            <input
              type="number"
              min={0}
              max={80}
              value={weeklyHours}
              onChange={(event) => setWeeklyHours(event.target.value)}
            />
          </label>
          <label className="dv2-field">
            <span>Budget (USD)</span>
            <input
              type="number"
              min={0}
              max={100000}
              value={budget}
              onChange={(event) => setBudget(event.target.value)}
            />
          </label>
          <label className="dv2-field">
            <span>Country</span>
            <input
              value={country}
              onChange={(event) => setCountry(event.target.value)}
              placeholder="e.g. India"
            />
          </label>
          <label className="dv2-field">
            <span>Education level</span>
            <input
              value={education}
              onChange={(event) => setEducation(event.target.value)}
              placeholder="undergraduate"
            />
          </label>
          <label className="dv2-field dv2-field-wide">
            <span>Goals <em>comma separated</em></span>
            <input
              value={goals}
              onChange={(event) => setGoals(event.target.value)}
              placeholder="course project, internship proof, published prototype"
            />
          </label>
          <label className="dv2-field">
            <span>Purpose</span>
            <select value={purpose} onChange={(event) => setPurpose(event.target.value as StudentProfile["purpose"])}>
              <option value="coursework">Coursework</option>
              <option value="research">Research</option>
              <option value="product">Product</option>
            </select>
          </label>
        </div>

        <div className="dv2-intake-actions">
          <button type="submit" className="dv2-button dv2-button-primary" disabled={isStarting || !rawContent.trim()}>
            {isStarting ? <Loader2 size={16} className="dv2-spin" /> : <ArrowRight size={16} />}
            {isStarting ? "Starting run…" : "Start research run"}
          </button>
          <p className="dv2-fineprint">202 response starts the run; sections stream in as they are written.</p>
        </div>
      </form>
    </section>
  );
}
