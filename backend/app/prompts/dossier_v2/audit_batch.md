# Batched critic + specificity audit (audit_batch@v1)

## Shared rules
Follow ALL rules in `shared.md`, especially STRICT JSON output. This task audits existing text; it never writes dossier content.

## Inputs
Project DNA: {project_dna}
Student profile: {student_profile}
Sections: {sections} — JSON array with `section`, `summary`, `items`, `evidence_ids`, `limitations` for each section. `evidence_ids` is the complete list of valid references for that section.

## Task
Audit every supplied section and decide whether it passes all three checks:
- `Grounded`: every item labelled `grounded` carries at least one evidence id from that section's `evidence_ids`, and the claim does not state facts absent from the supplied context.
- `Specific`: the section names this project's concrete users, method or constraints. Replacing the project name, domain and student profile with a different project in the same domain would make the text false or incoherent. Generic advice fails this check.
- `Complete`: a project-specific summary exists and the section is not an error placeholder.

Be strict but fair. Do not invent evidence ids. Do not fail a section merely for being cautious in `limitations`. Return one audit per supplied section.

## Output — STRICT JSON only
{{"audits":[{{"section":"gaps","passed":false,"failures":[{{"check":"Grounded","reason":"E99 is not a supplied evidence id","fix":"Remove the citation"}}]}}]}}

Rules for output:
- Exactly one `audits` entry per supplied section, using the exact section key.
- `passed` is true only when `failures` is empty. `check` must be one of `Grounded`, `Specific`, `Complete`.
- Each `reason` and `fix` is one short concrete sentence. No extra keys, no prose, no markdown fences.
