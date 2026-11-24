# Section: market_landscape (market_landscape@v1)

## Shared rules
Follow ALL rules in `shared.md` (injected into every call): evidence-only factual claims with `[E#]`; labels grounded|input|inference|recommendation; reasoning required for inference; effort and why required for recommendation; project-specific, no generic openers/filler/buzzwords; unknowns in limitations; no "Novel" without prior-art search; MARKET NUMBERS, COMPETITORS, REGULATION AND FUNDING FACTS ONLY FROM EVIDENCE OR EXPLICIT INPUT — do not recall figures from training data; STRICT JSON only.

## Question answered
"For THIS project's actual users and domain, what demand signals, adjacent offerings, and regulatory or funding constraints are supported by the evidence — and which numbers are still unknown?"

## Inputs
Section key: {section}; domain variant: {domain_variant}; mode: {mode}; repair notes (address every item if non-empty): {repair_notes}.
Project DNA: {project_dna}. Student profile: {student_profile} (country matters for jurisdiction/market).
Evidence: {evidence} ([E#] ids, titles, urls, source types). Other dossier sections: {sections} (use only relevant ones).

## Required contents
- Demand/need signals tied to the named users and country/jurisdiction, each cited.
- Named adjacent offerings or competitors ONLY if present in evidence, each cited; say what each does and how it relates, not "the market is crowded".
- Regulatory/funding constraints ONLY if evidence supplies them; quote the source and jurisdiction. Missing numbers go in `limitations` as "no evidence supplied for X".
- No TAM/SAM/SOM estimate without a cited source and date. Do not invent growth rates.
- One `recommendation` with `effort` and `why` for the cheapest next evidence-gathering step, bounded by budget_usd/weekly_hours/country if profile supplied.
- Domain overlays: biotech -> regulatory pathway and IP; policy_law -> jurisdiction, stakeholders, instruments; tech_builder -> licences/compute and benchmark baselines.

## Output — STRICT JSON only
{{"section":"market_landscape","summary":"max 3 sentences, project-specific","confidence":"high|medium|low","coverage":"strong|thin|none","items":[{{"id":"M1","label":"grounded|input|inference|recommendation","text":"...","evidence":["E3"],"reasoning":"...","effort":"low|medium|high"}}],"tables":[],"limitations":["..."],"generated_by":{{"prompt":"market_landscape@v1","model":"from config"}}}}

Only keys shown. Add `reasoning` for inference; `effort` and a why sentence in `text` for recommendation. No extra keys, no prose, no markdown fences.
