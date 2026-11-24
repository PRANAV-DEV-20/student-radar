# Cross-section reasoning — roadmap (cross_roadmap@v1)

## Shared rules
Include and obey ALL rules in `shared.md`: evidence-only factual claims with `[E#]`, labels grounded|input|inference|recommendation, reasoning for inference, effort/why for recommendation, project specificity, no filler, unknowns in limitations, no unsupported Novelty claims, external facts only from evidence or input, DOMAIN OVERLAYS, PERSONALISATION must visibly appear in roadmap, STRICT JSON only.

## Inputs
Target section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna} (name, domain, users, constraints, stage). Student profile: {student_profile} (skills, weekly_hours, budget_usd, country, education_level, goals, purpose).
Evidence: {evidence} — passages with `E#` ids for deadlines, costs, tooling, datasets, and domain requirements.
Other dossier sections: {sections} (generated JSON for `gaps`, `validation_plan`, `feasibility`, `tech_stack`, `funding_opportunities`, `open_questions_evidence`).

## Question answered
"In what order should THIS student do the work, with realistic hour estimates, dependencies, and an explicit done-when test for each milestone, under their actual weekly hours, budget, country and purpose?"

## Task
Synthesise ACROSS gaps, validation, feasibility and tech stack. Cover, in dependency order: evidence refresh / prior-art check, problem and user confirmation, data acquisition and licence check, minimal build, validation experiment, risk/compliance checkpoint, and a final artefact matching `purpose` (coursework|research|product). Each milestone:
- `tasks_with_hours` must show concrete tasks with hour numbers that fit `weekly_hours` and `budget_usd` (name the profile values in the item text).
- `dependency` names the prior milestone id or "none".
- `done_when` is an observable test, not "complete the implementation".
- include domain gates: regulatory/IP/biosafety/assay validation (biotech), jurisdiction/citation checks (policy_law), licence/compute/benchmark baseline/misuse review (tech_builder).
Use `inference` with `reasoning` when sequencing from evidence, `recommendation` with `effort` and `why` for the plan itself. Put unknowns (missing deadlines, costs) in `limitations`.
Use the exact `roadmap` table columns: `milestone`, `tasks_with_hours`, `dependency`, `done_when`.

## Output — STRICT JSON matching the `roadmap` section schema
{{"section":"roadmap","summary":"...","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"R1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[{{"title":"Milestone plan","columns":["milestone","tasks_with_hours","dependency","done_when"],"rows":[["...","...","...","..."]]}}],"limitations":["..."],"generated_by":{{"prompt":"roadmap@v1","model":"from config"}}}}

Rules: `summary` max 3 sentences and project-specific; exact table columns and order; personalisation visible; only keys shown; no extra keys; no prose; no markdown fences.
