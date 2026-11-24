# Project DNA ingestion (ingest_dna@v1)

## Shared rules
Follow ALL rules in `shared.md` where applicable: evidence-only factual claims with `[E#]`, labels grounded|input|inference|recommendation, reasoning for inference, project specificity, no filler/buzzwords, unknowns in limitations, no "Novel" claim without prior-art search, and STRICT JSON only. This task structures raw input; it does not invent facts.

## Inputs
Input type: {input_type} (e.g. notes, brief, form, transcript).
Raw content: {raw_content}.
Domain persona: {domain_persona} (domain-specific lens to apply when interpreting the raw content).

## Task
Extract a clean, machine-usable Project DNA from the raw content.
- Preserve the student's own wording for the core idea; do not embellish.
- Fill each field only when the raw content supports it; use an empty string `""` when absent and list the absence under `unknowns`.
- `domain_persona` guides which domain-specific fields to probe (biotech: regulatory/IP/biosafety/assay; policy_law: jurisdiction/stakeholders/instruments/citation; tech_builder: model+data licences/compute/misuse/benchmarks) but never add facts that are not in the raw content.
- Mark any interpretation that is not literally in the raw content as an `inference` with `reasoning`.
- Keep user constraints concrete: skills, weekly_hours, budget_usd, country, education_level, goals, purpose (`coursework|research|product`) when present.
- Do not perform market, competitor, regulation, funding, or prior-art research here.

## Output — STRICT JSON only
{{"project_dna":{{"name":"","domain":"","problem":"","users":"","goals":"","constraints":"","methods":"","stage":"","skills":"","weekly_hours":"","budget_usd":"","country":"","education_level":"","goals_detail":"","purpose":""}},"inferences":[{{"field":"","value":"","reasoning":""}}],"unknowns":[""],"generated_by":{{"prompt":"ingest_dna@v1","model":"from config"}}}}

Only keys shown. No extra keys, no prose, no markdown fences.
