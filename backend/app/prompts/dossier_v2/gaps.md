# Section: gaps (gaps@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; external facts only from evidence or input; STRICT JSON only.

## Question answered
"What is missing — in prior art, evidence, data, capability, and the student's own setup — that blocks THIS project, and what is the smallest way to close each gap?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence}. Other dossier sections: {sections} (especially `related_work`, `novelty_assessment`, `problem_users`, `feasibility`, `validation_plan`).

## Required contents
- Capability gaps: what existing work fails to do that this project needs, compared against `related_work` rows.
- Evidence gaps: assertions lacking `[E#]`, or sections with `coverage: thin|none`.
- Data gaps: datasets/access/labels blocked by licence, budget_usd or country.
- Skill/resource gaps: mismatch of skills, weekly_hours, budget_usd, education_level with the planned work.
- Validation gaps: assumptions with no experiment in `validation_plan`.
- Every gap gets `severity` and a concrete `recommendation` with `effort` and `why`; use `inference` with `reasoning` when combining two evidence-backed facts.
- Domain overlays when applicable: biotech regulatory/IP/biosafety/assay validation; policy_law jurisdiction/stakeholders/instruments/comparative/citation; tech_builder licences/compute/misuse/benchmarks.

## Output — STRICT JSON only
{{"section":"gaps","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"G1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high","severity":"low|medium|high|critical"}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"gaps@v1","model":"from config"}}}}

Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation; `severity` for gaps. No extra keys, no prose, no markdown fences.
