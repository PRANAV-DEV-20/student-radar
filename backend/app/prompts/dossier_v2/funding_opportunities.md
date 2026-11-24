# Section: funding_opportunities (funding_opportunities@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; FUNDING FACTS, AMOUNTS, DEADLINES AND ELIGIBILITY ONLY FROM EVIDENCE OR EXPLICIT INPUT — never recall grants from memory; STRICT JSON only.

## Question answered
"Which funding or non-cash opportunities can THIS student realistically use for THIS project, given country, education_level, purpose, weekly_hours and budget_usd?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence} (grants, competitions, fellowships, free credits, data access). Other dossier sections: {sections} (especially `roadmap`).

## Required contents
- Only opportunities present in evidence with url, name, eligibility, amount/deadline and citation; if any field is missing write "no evidence supplied for X" and add it to `limitations`.
- Eligibility check against country, education_level, purpose (coursework|research|product) and stage: say "unknown" where evidence is lacking, never guess.
- Non-cash options (compute credits, API credits, dataset access, lab time, mentorship) treated the same way.
- Each candidate gets a `recommendation` with `effort` and `why` tied to the specific milestone it unlocks.
- Never state that the student "qualifies" unless evidence/eligibility plus profile values make it explicit; otherwise `inference` with `reasoning`.
- Domain overlays: biotech -> translation/regulatory-stage grants and biosafety compliance costs; policy_law -> jurisdiction-specific fellowships and citation requirements; tech_builder -> compute/model credit programmes and dataset licences.

## Output — STRICT JSON only
{{"section":"funding_opportunities","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"FU1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"funding_opportunities@v1","model":"from config"}}}}

Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation. No extra keys, no prose, no markdown fences.
