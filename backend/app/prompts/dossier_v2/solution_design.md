# Section: solution_design (solution_design@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; external facts only from evidence or input; STRICT JSON only.

## Question answered
"What concrete design would solve THIS problem for THESE users with THESE constraints, and which design choices are still assumptions?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence}. Other dossier sections: {sections} (especially `idea_restated`, `problem_users`, `related_work`, `data_evaluation`, `gaps`).

## Required contents
- Concrete components and data flow tied to the project's method, inputs and outputs — not an architecture diagram of a generic app.
- The key design decisions with the alternative rejected and why (cite evidence where factual; label preference as `recommendation` with `effort` and `why`).
- Which parts are copied/adapted from prior art (with `[E#]`) and which are student-authored changes; do not call changes novel.
- Minimum viable version given weekly_hours/budget_usd/skills, and what is deliberately deferred.
- Assumptions in the design must be `inference` with `reasoning`, plus a link to `validation_plan` test where applicable.
- Domain overlays: biotech -> assay design, biosafety and regulatory checkpoints; policy_law -> jurisdiction, stakeholder workflow, citation provenance; tech_builder -> model/data flow, compute, misuse controls and benchmark baseline.
- No table required; use `tables: []`.

## Output — STRICT JSON only
{{"section":"solution_design","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"S1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"solution_design@v1","model":"from config"}}}}

Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation. No extra keys, no prose, no markdown fences.
