# Section: executive_brief (executive_brief@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and a why sentence required for recommendation; project-specific and no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without a real prior-art search; market/competitors/regulation/funding only from evidence or input; STRICT JSON only. PERSONALISATION: skills, weekly_hours, budget_usd, country, education_level, goals, purpose must visibly appear in the recommendations here.

## Question answered
"What is the honest one-page case for THIS project: what it is, for whom, what already exists, what is unproven, and what should THIS student do next given their actual constraints?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence}. Other dossier sections: {sections} (use only relevant ones).

## Required contents
- Concrete project statement and target users: name the project, domain and user; mark as `input` if from Project DNA.
- Closest prior art and the precise difference; cite `[E#]`; never imply novelty the `novelty_assessment` does not support.
- Top 2–3 gaps/risks with `severity` and evidence.
- Next 3 actions as `recommendation` items, each with `effort`, a `why` naming the relevant profile field and value (e.g. "weekly_hours=6", "budget_usd=0", "country=..." ).
- Confidence/limitations consistent with the rest of the dossier; no table needed.

## Output — STRICT JSON only
{{"section":"executive_brief","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"B1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high","severity":"low|medium|high|critical"}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"executive_brief@v1","model":"from config"}}}}

Only keys shown. Add `reasoning` for inference; add `effort` and a why sentence inside `text` for recommendation. `severity` only for risks/gaps. No extra keys, no prose, no markdown fences.
