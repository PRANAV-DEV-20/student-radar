# Cross-section reasoning — tech stack (cross_tech_stack@v1)

## Shared rules
Include and obey ALL rules in `shared.md`: evidence-only factual claims with `[E#]`, labels grounded|input|inference|recommendation, reasoning for inference, effort/why for recommendation, project specificity, no filler, unknowns in limitations, no unsupported Novelty claims, external facts only from evidence or input, DOMAIN OVERLAYS, PERSONALISATION must visibly appear, STRICT JSON only.

## Inputs
Target section key: {section}; domain variant: {domain_variant} (`design_biotech` | `policy_law` | `tech_builder` | other); mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile} (skills, weekly_hours, budget_usd, country, education_level, goals, purpose).
Evidence: {evidence} — passages with `E#` ids covering tools, model licences, dataset licences, compute, and reference repos.
Other dossier sections: {sections} (generated JSON for `solution_design`, `data_evaluation`, `feasibility`, `related_work`, `validation_plan`).

## Question answered
"What concrete stack should THIS student use, layer by layer, given the design, data, licences, compute, skills, hours, budget and country — and what breaks if they don't?"

## Task
Synthesise ACROSS solution_design + data_evaluation + feasibility + related_work. For each layer (e.g. data collection, storage, model/analysis, evaluation, deployment/interface, compliance) give:
- a specific recommendation tied to the project's method and data.
- `why_for_this_project` citing `[E#]` where factual and naming the profile value where personal (e.g. "budget_usd=0", "weekly_hours=6", "skills=Python").
- alternatives with a real trade-off, not a list of brand names.
- `cost_and_free_tier` from evidence only; if no evidence, write "no evidence supplied" and add to limitations.
- `learning_effort_for_student` tied to skills/education_level/weekly_hours.
- `reference_repos` limited to urls present in evidence.
Tech_builder overlay: model and data licences, compute needs, misuse/abuse cases, benchmark baselines must appear. Biotech overlay: assay/reagent and biosafety constraints. Policy_law overlay: jurisdiction and citation/authority tooling.
Use the exact `tech_stack` table columns: `layer`, `recommendation`, `why_for_this_project`, `alternatives`, `cost_and_free_tier`, `learning_effort_for_student`, `reference_repos`.

## Output — STRICT JSON matching the `tech_stack` section schema
{{"section":"tech_stack","summary":"...","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"T1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[{{"title":"Recommended stack by layer","columns":["layer","recommendation","why_for_this_project","alternatives","cost_and_free_tier","learning_effort_for_student","reference_repos"],"rows":[["...","...","...","...","...","...","..."]]}}],"limitations":["..."],"generated_by":{{"prompt":"tech_stack@v1","model":"from config"}}}}

Rules: `summary` max 3 sentences and project-specific; exact table columns and order; personalisation visible; only keys shown; no extra keys; no prose; no markdown fences.
