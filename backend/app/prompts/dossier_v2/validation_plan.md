# Section: validation_plan (validation_plan@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; external facts only from evidence or input; STRICT JSON only.

## Question answered
"Which assumptions of THIS project must be tested first, with what experiment, metric, threshold and time — and which ones cannot be tested yet?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence}. Other dossier sections: {sections} (especially `idea_restated`, `problem_users`, `solution_design`, `data_evaluation`, `gaps`).

## Required contents
- One table row per assumption using the EXACT columns: `assumption`, `risk_level`, `experiment`, `metric`, `threshold`, `time_needed`.
- `assumption` is specific and falsifiable for this project; `experiment` is runnable by the student within weekly_hours/budget_usd/country.
- `metric` is measurable and `threshold` is a number or explicit decision rule; do not invent benchmark numbers — label sourced numbers with `[E#]`, otherwise mark the threshold as `inference` with `reasoning` in the item text.
- Order rows by risk_level × cheapness; the first row is the cheapest high-risk test.
- For untestable assumptions, put them in `limitations` with the missing access/evidence.
- Domain overlays: biotech -> assay validation metrics and biosafety/regulatory gates; policy_law -> jurisdiction-specific stakeholder review and citation verification; tech_builder -> benchmark baselines, licence checks and misuse probes.
- Each chosen test is a `recommendation` with `effort` and `why`.

## Output — STRICT JSON only
{{"section":"validation_plan","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"V1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[{{"title":"Assumption tests","columns":["assumption","risk_level","experiment","metric","threshold","time_needed"],"rows":[["...","...","...","...","...","..."]]}}],"limitations":["..."],"generated_by":{{"prompt":"validation_plan@v1","model":"from config"}}}}

Table columns must be EXACT and in the order shown. Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation. No extra keys, no prose, no markdown fences.
