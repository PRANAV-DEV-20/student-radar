# Section: people_community (people_community@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; external facts only from evidence or input; STRICT JSON only.

## Question answered
"Which real people, communities and supervisors can help THIS student on THIS project, and what concrete help can they give given country, weekly_hours and purpose?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence} (community pages, labs, forums, courses, supervisors). Other dossier sections: {sections} (especially `problem_users`, `gaps`).

## Required contents
- Named communities/mentors/venues ONLY from evidence or input, each cited; say what each can actually provide (data access, review, domain expertise, equipment, feedback) for this project.
- Roles to fill where no named person exists in evidence; mark as `inference` with `reasoning`, and put the missing contact in `limitations`.
- How to approach them concretely, as `recommendation` items with `effort` and `why`, bounded by weekly_hours, budget_usd, country and purpose.
- Domain overlays: biotech -> lab PI, biosafety officer, assay expert, regulatory mentor; policy_law -> jurisdiction-specific practitioners, stakeholders, citation/authority reviewers; tech_builder -> maintainers of referenced repos, dataset owners, benchmark communities.
- Do not claim someone will respond or endorse the project without evidence.

## Output — STRICT JSON only
{{"section":"people_community","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"C1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"people_community@v1","model":"from config"}}}}

Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation. No extra keys, no prose, no markdown fences.
