# Section: data_evaluation (data_evaluation@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; external facts only from evidence or input; STRICT JSON only.

## Question answered
"What data can THIS project actually get and use, under which licence and cost, and how will we know it is good enough for the stated method?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence} (dataset/repo/paper urls, licences, sizes). Other dossier sections: {sections} (especially `solution_design`).

## Required contents
- Candidate datasets/sources named from evidence only, each with url, licence, access route and cost/conditions cited `[E#]`.
- Suitability for the project's method: coverage, labels, domain match, country/jurisdiction relevance, and known gaps; no invented sizes or statistics.
- Licence and privacy constraints, including model/data licences for tech_builder, consent/PHI and biosafety/assay data for biotech, citation/authority and jurisdiction for policy_law.
- A concrete quality/acceptance test (e.g. label agreement, coverage check) as a `recommendation` with `effort` and `why`, bounded by weekly_hours/budget_usd.
- Any missing licence, size, or access fact goes in `limitations` as "no evidence supplied for X".
- No table is required; use `tables: []` unless a dataset comparison adds clarity (then use plain columns inside `tables`).

## Output — STRICT JSON only
{{"section":"data_evaluation","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"D1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"data_evaluation@v1","model":"from config"}}}}

Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation. No extra keys, no prose, no markdown fences.
