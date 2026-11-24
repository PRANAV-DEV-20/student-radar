# Batched section synthesis (synthesis_batch@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected separately). Each section value must obey its own full instructions and exact output schema. Evidence-only factual claims, honest limitations, STRICT JSON only.

## Inputs
Project DNA: {project_dna}
Student profile: {student_profile}
Domain variant: {domain_variant}; mode: {mode}.
Sections to write: {sections} — JSON array. Each entry has `section` (exact key), `instructions` (the complete specification for that section, including its output contract), and `evidence` (the only passages you may cite).
Previously written sections: {prior_sections} (use only where a section's instructions ask for cross-section reasoning).

## Task
Write every listed section. Do not skip a section. Do not write prose outside the JSON object. Use only the supplied evidence and input fields. Never invent an `[E#]`. Keep table columns exactly as each section's instructions specify.

## Output — STRICT JSON only
{{"sections":{{"related_work":{{"section":"related_work","summary":"...","confidence":"low|medium|high","coverage":"none|thin|strong","items":[],"tables":[],"limitations":[],"generated_by":{{"prompt":"related_work@v1","model":"from config"}}}},"market_landscape":{{...}}}}}}

Rules for output:
- Exactly one key per requested `section`, using the exact key. Do not add or omit keys.
- Each value is the exact JSON object described by that section's `instructions`.
- No markdown fences, no commentary, no extra top-level keys.
