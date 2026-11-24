# Section: open_questions_evidence (open_questions_evidence@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; external facts only from evidence or input; STRICT JSON only.

## Question answered
"Which questions remain unanswered for THIS project, what evidence is missing for each, and what is the cheapest way to get it under the student's actual constraints?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence} (with `E#` ids, source types, and any search log). Other dossier sections: {sections} (all generated section JSONs).

## Required contents
- One item per genuinely open question, naming what is unknown and why it matters for this project (not generic "more research needed").
- For each, name the source_type that could answer it: `local_corpus`, `github`, `papers`, `web`, `opportunities`, `datasets`; cite existing partial evidence `[E#]` where present.
- Mark each as `inference` with `reasoning` when derived from a gap, or `recommendation` with `effort` and `why` when proposing the next lookup; bound it by weekly_hours, budget_usd and country.
- Explicitly list contradictions between passages or sections in `limitations` with their ids.
- Do not present an unanswered question as a finding. Do not invent facts to close a gap.
- Domain overlays: biotech -> regulatory/IP/biosafety/assay unknowns; policy_law -> jurisdiction/citation/authority unknowns; tech_builder -> licence/compute/misuse/benchmark unknowns.

## Output — STRICT JSON only
{{"section":"open_questions_evidence","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"O1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"open_questions_evidence@v1","model":"from config"}}}}

Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation. No extra keys, no prose, no markdown fences.
