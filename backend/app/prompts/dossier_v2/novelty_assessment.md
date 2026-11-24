# Section: novelty_assessment (novelty_assessment@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no filler/buzzwords; unknowns in limitations; NEVER call something Novel unless a prior-art search was actually run and found nothing close; external facts only from evidence or input; STRICT JSON only.

## Question answered
"Given the prior-art searches actually run, which specific claims are differentiated, which are already covered, and what would make a genuine novelty claim defensible?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence} — prior-art passages with `E#` plus the log of queries/sources actually run, if supplied. Other dossier sections: {sections} (especially `related_work`).

## Required contents
- Each candidate claim stated precisely (not a buzzword) with verdict `differentiated`, `partially covered`, `covered`, `unverified`, or `novel`.
- Use `novel` ONLY when {evidence} shows a real prior-art search log and no close match appears in the passages. Otherwise use `unverified` and record the missing search in `limitations`.
- Closest prior art named with its `E#` ids; explain overlap and the exact difference.
- `what_would_make_it_novel` is a concrete design or search change, not "do more research".
- Use exact table columns: `claim`, `verdict`, `closest_prior_art`, `evidence_ids`, `what_would_make_it_novel`.
- Wording rule: say "no close prior art found in the searched sources", never "nobody has done this".
- Domain overlays: biotech -> IP and assay novelty; policy_law -> comparative/citation checks; tech_builder -> benchmark baselines and licence constraints.

## Output — STRICT JSON only
{{"section":"novelty_assessment","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"N1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[{{"title":"Novelty claims vs prior art","columns":["claim","verdict","closest_prior_art","evidence_ids","what_would_make_it_novel"],"rows":[["...","...","...","E3","..."]]}}],"limitations":["..."],"generated_by":{{"prompt":"novelty_assessment@v1","model":"from config"}}}}

Table columns must be EXACT and in the order shown. Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation. No extra keys, no prose, no markdown fences.
