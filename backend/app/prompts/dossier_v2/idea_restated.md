# Section: idea_restated (idea_restated@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; external facts only from evidence or input; STRICT JSON only.

## Question answered
"What exactly is this idea, stated precisely in the student's terms, what problem does it target, and what is explicitly OUT of scope?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna} (name, domain, problem, users, goals, constraints, methods, stage). Student profile: {student_profile}.
Evidence: {evidence}. Other dossier sections: {sections} (use only relevant ones).

## Required contents
- One precise, testable description of the idea — inputs, method, outputs, and the user who would use it. Use `input` items for anything taken from Project DNA and name the field.
- The core hypothesis in one sentence and the assumptions it depends on.
- Explicit non-goals / boundaries (what the project will NOT do), each with a short reason.
- Domain boundary: biotech -> regulatory/IP/biosafety/assay scope; policy_law -> jurisdiction/stakeholders/instruments/citation scope; tech_builder -> model/data/compute/misuse boundaries.
- Do not claim novelty here, and do not add market numbers. If the idea is vague, say so in `limitations` rather than embellishing.

## Output — STRICT JSON only
{{"section":"idea_restated","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"I1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"..."}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"idea_restated@v1","model":"from config"}}}}

Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation. No extra keys, no prose, no markdown fences.
