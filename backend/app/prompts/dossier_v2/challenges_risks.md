# Section: challenges_risks (challenges_risks@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; external facts only from evidence or input; STRICT JSON only. Safe: flag dangerous, illegal or unethical paths instead of recommending them.

## Question answered
"What can concretely go wrong in THIS project, how bad is it, what evidence suggests it, and what is the cheapest way to reduce it?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence}. Other dossier sections: {sections} (especially `gaps`, `feasibility`, `data_evaluation`, `related_work`).

## Required contents
- Risks grouped by type with `severity` (`low|medium|high|critical`): technical, data/privacy, legal/IP or regulatory, resource (weekly_hours/budget_usd), user adoption, and safety/misuse.
- Each risk names the specific failure mode for this project (not "scope creep" alone) and cites `[E#]` or is labelled `inference` with `reasoning`.
- A mitigation `recommendation` per high/critical risk with `effort` and `why`, bounded by budget_usd, weekly_hours, country.
- Domain overlays: biotech -> biosafety, regulatory pathway, assay failure modes, IP; policy_law -> jurisdiction, legal-advice boundaries, citation/authority errors; tech_builder -> model/data licence violations, compute shocks, misuse cases, benchmark gaming.
- Do not pad with generic risks; if a category has no evidence, say so in `limitations`.

## Output — STRICT JSON only
{{"section":"challenges_risks","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"C1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high","severity":"low|medium|high|critical"}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"challenges_risks@v1","model":"from config"}}}}

Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation; `severity` for risks. No extra keys, no prose, no markdown fences.
