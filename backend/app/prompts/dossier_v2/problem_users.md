# Section: problem_users (problem_users@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; market/competitor/regulation/funding facts only from evidence or input; STRICT JSON only.

## Question answered
"Who exactly has this problem, how do they handle it today, and what evidence do we have that the pain is real and frequent enough to justify this project?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence} (including any interview/user notes, labelled `input`). Other dossier sections: {sections} (use only relevant ones).

## Required contents
- Named user segments (role, setting, country/jurisdiction where relevant) tied to the project, not "everyone".
- Current workaround or baseline for each segment, cited `[E#]` or labelled `input`.
- Pain frequency/severity with evidence; if no evidence exists, state it in `limitations` and mark the claim `inference`.
- One `recommendation` for how to verify the user with `effort` and `why`, bounded by weekly_hours/budget_usd/country when profile is supplied.
- Domain overlays: biotech -> affected clinicians/lab staff and assay context; policy_law -> jurisdiction and affected stakeholders/instruments; tech_builder -> end-user plus potential misuse-affected parties.
- Never assert market size here; that belongs to `market_landscape` and still needs evidence.

## Output — STRICT JSON only
{{"section":"problem_users","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"P1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"problem_users@v1","model":"from config"}}}}

Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation. No extra keys, no prose, no markdown fences.
