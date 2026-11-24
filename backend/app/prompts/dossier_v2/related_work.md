# Section: related_work (related_work@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" claim without prior-art search; external facts only from evidence or input; STRICT JSON only.

## Question answered
"What specific prior work (papers, code/repos, datasets, products, documents) exists for THIS project, and exactly how does each item overlap with and differ from what the student is building?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile}.
Evidence: {evidence} (ids, title, url, type, maturity, licence). Other dossier sections: {sections} (use only relevant ones).

## Required contents
- Only works actually present in evidence. Do not recall famous papers or tools from memory.
- For each work: name, url, type, what it does, maturity, licence, overlap, what it misses, how YOURS differs, and the evidence id.
- Prefer close matches; put weak matches in `limitations` rather than padding the table.
- If licence/maturity is unknown, write "unknown" in the cell and add it to `limitations`.
- Domain overlays: biotech -> include regulatory guidance, IP and assay-validation precedents; policy_law -> include jurisdictional and comparative sources with authority checks; tech_builder -> include model/data licences, compute notes and benchmark baselines.
- No "novel" verdicts here; that is `novelty_assessment`.

## Output — STRICT JSON only
{{"section":"related_work","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"W1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"..."}}],"tables":[{{"title":"Prior art comparison","columns":["name","url","type","what_it_does","maturity","licence","overlap","what_it_misses","how_yours_differs","evidence_id"],"rows":[["...","...","...","...","...","...","...","...","...","E3"]]}}],"limitations":["..."],"generated_by":{{"prompt":"related_work@v1","model":"from config"}}}}

Table columns must be EXACT and in the order shown. Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation. No extra keys, no prose, no markdown fences.
