# Section: roadmap (roadmap@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; external facts only from evidence or input; DOMAIN OVERLAYS; PERSONALISATION must visibly appear in the roadmap; STRICT JSON only.

## Question answered
"In what order should THIS student do the work, with realistic hour estimates, dependencies and done-when tests, given their weekly_hours, budget_usd, skills, country, education_level, goals and purpose?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence}. Other dossier sections: {sections} (especially `gaps`, `validation_plan`, `feasibility`, `tech_stack`, `funding_opportunities`).

## Required contents
- Milestones in dependency order: evidence refresh/prior-art check, user confirmation, data/licence acquisition, minimal build, validation test, risk/compliance gate, final artefact matching purpose (coursework|research|product).
- EXACT table columns: `milestone`, `tasks_with_hours`, `dependency`, `done_when`. `tasks_with_hours` must contain concrete tasks with hour numbers fitting weekly_hours and budget_usd; name those profile values in the item text.
- `dependency` names a prior milestone or "none"; `done_when` is observable, not "implementation complete".
- Plan itself is a `recommendation` with `effort` and `why`; sequencing derived from evidence is `inference` with `reasoning`.
- Domain gates: biotech regulatory/IP/biosafety/assay; policy_law jurisdiction/citation/authority; tech_builder licence/compute/benchmark/misuse review.
- Missing deadlines or costs go in `limitations` as "no evidence supplied for X".

## Output — STRICT JSON only
{{"section":"roadmap","summary":"max 3 sentences, project-specific, names the binding constraint","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"R1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[{{"title":"Milestone plan","columns":["milestone","tasks_with_hours","dependency","done_when"],"rows":[["...","...","...","..."]]}}],"limitations":["..."],"generated_by":{{"prompt":"roadmap@v1","model":"from config"}}}}

Table columns must be EXACT and in the order shown. Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation. No extra keys, no prose, no markdown fences.
