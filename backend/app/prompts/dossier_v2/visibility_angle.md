# Section: visibility_angle (visibility_angle@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; external facts only from evidence or input; STRICT JSON only.

## Question answered
"What is the most credible way for THIS student to make THIS project visible to the right people, and what claim can they honestly make today?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence}. Other dossier sections: {sections} (especially `novelty_assessment`, `related_work`, `validation_plan`, `people_community`, `funding_opportunities`).

## Required contents
- The honest headline claim: only what evidence supports; no "novel", "first", "breakthrough" unless `novelty_assessment` supports it with a real search.
- Specific venues/channels from evidence (repos, communities, courses, competitions, journals, local groups) with `[E#]` and why they fit this domain and country.
- The artefact to show (demo, report, poster, dataset card, reproducible notebook) matched to purpose (coursework|research|product) and weekly_hours/budget_usd.
- A concrete sequence as `recommendation` items with `effort` and `why`; include what must be validated before claiming a result.
- Domain overlays: biotech -> preprint/ethics/biosafety disclosure and IP caution; policy_law -> jurisdiction labelling and citation accuracy; tech_builder -> licence attribution, benchmark table and misuse note.
- No invented audience numbers or "viral" claims; missing evidence goes in `limitations`.

## Output — STRICT JSON only
{{"section":"visibility_angle","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"A1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"visibility_angle@v1","model":"from config"}}}}

Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation. No extra keys, no prose, no markdown fences.
