# Cross-section reasoning — executive brief (cross_executive_brief@v1)

## Shared rules
Include and obey ALL rules in `shared.md`: evidence-only factual claims with `[E#]`, labels grounded|input|inference|recommendation, reasoning for inference, effort/why for recommendation, project specificity, no filler, unknowns in limitations, no unsupported Novelty claims, market/competitor/regulation/funding only from evidence or input, PERSONALISATION must visibly appear, STRICT JSON only.

## Inputs
Target section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna} (name, domain, users, constraints, methods, stage). Student profile: {student_profile} (skills, weekly_hours, budget_usd, country, education_level, goals, purpose).
Evidence: {evidence} — passages with `E#` ids used by those sections.
Other dossier sections: {sections} (all generated section JSON, especially `idea_restated`, `problem_users`, `related_work`, `novelty_assessment`, `gaps`, `feasibility`, `validation_plan`, `roadmap`, `funding_opportunities`).

## Question answered
"What is the honest one-page case for this project: what it is, for whom, what is already out there, what is still unproven, and what THIS student should do next with their actual constraints?"

## Task
Synthesise ACROSS all sections. Lead with the concrete project and its user. State:
- the specific problem and users (from input or evidence, labelled accordingly).
- the closest prior art and the precise difference — never claim novelty without `novelty_assessment` backing.
- the top 2–3 gaps/risks with severity and evidence.
- the next 3 actions, each a `recommendation` with `effort` and a `why` that names the relevant profile field and value (skills, weekly_hours, budget_usd, country, education_level, goals, purpose).
- which claims are weakest and why (`confidence`/`coverage` must agree with the rest of the dossier).
Do not repeat section text verbatim; compress and cross-check. Put all unknowns in `limitations`. No table is required; use `tables: []` unless a short comparison adds clarity.

## Output — STRICT JSON matching the `executive_brief` section schema
{{"section":"executive_brief","summary":"...","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"B1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high","severity":"low|medium|high|critical"}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"executive_brief@v1","model":"from config"}}}}

Rules: `summary` max 3 sentences and project-specific; personalisation visible; only keys shown; no extra keys; no prose; no markdown fences.
