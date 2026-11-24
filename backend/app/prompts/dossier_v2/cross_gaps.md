# Cross-section reasoning — gaps (cross_gaps@v1)

## Shared rules
Include and obey ALL rules in `shared.md`: evidence-only factual claims with `[E#]`, labels grounded|input|inference|recommendation, reasoning for inference, effort/why for recommendation, project specificity, no filler, unknowns in limitations, no unsupported Novelty claims, external facts only from evidence or input, STRICT JSON only.

## Inputs
Target section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna} (name, domain, users, constraints, methods, stage). Student profile: {student_profile} (skills, weekly_hours, budget_usd, country, education_level, goals, purpose).
Evidence: {evidence} — all passages with `E#` ids used across those sections.
Other dossier sections: {sections} (especially `related_work`, `novelty_assessment`, `problem_users`, `feasibility`, `validation_plan`).

## Question answered
"What is genuinely missing — in prior art, in evidence, in data, in capability, and in the student's own setup — that blocks this project from working, and what is the smallest way to close each gap?"

## Task
Synthesise ACROSS sections, do not restate one section. Identify:
- capability gaps: what existing work does not do that this project needs (compare against `related_work` and `novelty_assessment` rows).
- evidence gaps: claims asserted without supporting `[E#]`, or sections with `coverage: thin|none`.
- data gaps: datasets/access/labels unavailable under budget_usd/country/licences.
- skill/resource gaps: mismatch between `student_profile` skills, weekly_hours, budget_usd and the proposed work.
- validation gaps: assumptions with no experiment in `validation_plan`.
For each gap give severity and a concrete `recommendation` with `effort` and `why`. Use `inference` with `reasoning` when combining two evidence-backed facts. State unknowns in `limitations`.

## Output — STRICT JSON matching the `gaps` section schema
{{"section":"gaps","summary":"...","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"G1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high","severity":"low|medium|high|critical"}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"gaps@v1","model":"from config"}}}}

Rules: `summary` max 3 sentences and project-specific; include only keys shown (add `reasoning` for inference, `effort` and `why` in text for recommendation, `severity` where relevant); no extra keys; no prose; no markdown fences.
