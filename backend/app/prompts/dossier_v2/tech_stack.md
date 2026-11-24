# Section: tech_stack (tech_stack@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; external facts only from evidence or input; DOMAIN OVERLAYS; PERSONALISATION must visibly appear here; STRICT JSON only.

## Question answered
"What exact stack should THIS student use, layer by layer, given the design, data, licences, compute, skills, hours, budget and country — and what is the trade-off of each choice?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence}. Other dossier sections: {sections} (especially `solution_design`, `data_evaluation`, `feasibility`, `related_work`).

## Required contents
- One row per layer (data collection, storage, model/analysis, evaluation, interface/deployment, compliance as relevant) using the EXACT columns: `layer`, `recommendation`, `why_for_this_project`, `alternatives`, `cost_and_free_tier`, `learning_effort_for_student`, `reference_repos`.
- `why_for_this_project` cites `[E#]` for facts and names profile values (skills, weekly_hours, budget_usd, country, education_level, purpose) where they drive the choice.
- `cost_and_free_tier` from evidence only; if absent write "no evidence supplied" and add to `limitations`. `reference_repos` must be urls present in evidence — no invented links.
- Tech_builder overlay: model and data licences, compute needs, misuse/abuse cases, benchmark baselines. Biotech overlay: assay/reagent and biosafety tooling. Policy_law overlay: jurisdiction and citation/authority tooling.
- `learning_effort_for_student` must be tied to skills/education_level/weekly_hours, not a generic "medium".

## Output — STRICT JSON only
{{"section":"tech_stack","summary":"max 3 sentences, project-specific, names the binding constraint","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"T1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[{{"title":"Recommended stack by layer","columns":["layer","recommendation","why_for_this_project","alternatives","cost_and_free_tier","learning_effort_for_student","reference_repos"],"rows":[["...","...","...","...","...","...","..."]]}}],"limitations":["..."],"generated_by":{{"prompt":"tech_stack@v1","model":"from config"}}}}

Table columns must be EXACT and in the order shown. Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation. No extra keys, no prose, no markdown fences.
