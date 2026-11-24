# Cross-section reasoning — novelty assessment (cross_novelty_assessment@v1)

## Shared rules
Include and obey ALL rules in `shared.md`: evidence-only factual claims with `[E#]`, labels grounded|input|inference|recommendation, reasoning for inference, effort/why for recommendation, project specificity, no filler, unknowns in limitations, NO "Novel" claim unless prior-art search actually ran and found nothing close, external facts only from evidence or input, STRICT JSON only.

## Inputs
Target section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence} — prior-art passages with `E#`, url, type, maturity, licence, plus the log of queries/sources actually run (empty log means no search was run).
Other dossier sections: {sections} (generated JSON for `related_work`, `idea_restated`, `solution_design`, `gaps`, `problem_users`).

## Question answered
"Given the prior art actually searched, which specific claims of this project are differentiated, which are already covered, and what would have to change for a real novelty claim?"

## Task
Synthesise ACROSS related_work + idea_restated + solution_design + gaps. For each candidate claim:
- state the claim precisely (not a buzzword).
- give a verdict from: `differentiated`, `partially covered`, `covered`, `unverified`, `novel` — use `novel` ONLY if {evidence} shows a real prior-art search log and no close match in its passages; otherwise use `unverified` and put the missing search in `limitations`.
- name the closest prior art with its `E#` ids, explain the overlap and the precise difference.
- require the `novelty` table columns exactly: `claim`, `verdict`, `closest_prior_art`, `evidence_ids`, `what_would_make_it_novel`.
Never infer novelty from absence of a passage. Put "no close prior art found in the searched sources" wording instead of absolute claims. Add concrete `recommendation` items with `effort` and `why` when a sharper search or design change is needed.

## Output — STRICT JSON matching the `novelty_assessment` section schema
{{"section":"novelty_assessment","summary":"...","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"N1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[{{"title":"Novelty claims vs prior art","columns":["claim","verdict","closest_prior_art","evidence_ids","what_would_make_it_novel"],"rows":[["...","...","...","E3","..."]]}}],"limitations":["..."],"generated_by":{{"prompt":"novelty_assessment@v1","model":"from config"}}}}

Rules: `summary` max 3 sentences and project-specific; exact table columns and order; only keys shown; no extra keys; no prose; no markdown fences.
