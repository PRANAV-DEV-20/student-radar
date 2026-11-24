# Section: feasibility (feasibility@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; external facts only from evidence or input; STRICT JSON only.

## Question answered
"Can THIS student actually deliver THIS project with their skills, weekly_hours, budget_usd, country, education_level, goals and purpose — and what is the binding constraint?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile} (skills, weekly_hours, budget_usd, country, education_level, goals, purpose).
Evidence: {evidence}. Other dossier sections: {sections} (especially `data_evaluation`, `tech_stack`, `challenges_risks`).

## Required contents
- PERSONALISATION IS MANDATORY: name each relevant profile field AND value in the concrete item text (e.g. "skills=[Python, stats]", "weekly_hours=5", "budget_usd=0", "country=...", "education_level=...", "purpose=coursework"). Do not write advice that ignores these values.
- Feasibility verdict for dimensions: skill fit, time fit, budget fit, data/access fit (incl. country restrictions), domain compliance fit. Cite evidence for external costs/requirements.
- Identify the single binding constraint and express it with `inference` + `reasoning` when derived from two inputs.
- Concrete scope reductions as `recommendation` items with `effort` and `why` that fit the stated hours and budget.
- If a required licence, cost or deadline is not in evidence, put it in `limitations`.
- Domain overlays: biotech -> lab access/biosafety/assay/regulatory timeline vs weekly_hours; policy_law -> jurisdiction access and citation sources; tech_builder -> compute cost and model/data licences vs budget_usd.

## Output — STRICT JSON only
{{"section":"feasibility","summary":"max 3 sentences, project-specific, names the binding constraint","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"F1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high","severity":"low|medium|high|critical"}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"feasibility@v1","model":"from config"}}}}

Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation; `severity` where relevant. No extra keys, no prose, no markdown fences.
