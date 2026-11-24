# Shared rules (injected into every section call)

These rules apply to every dossier section and every reasoning task. Violating them is a failure.

## Evidence and labels
- Base every factual claim on the provided evidence passages. Cite each with its `[E#]` id inside the item text and list the same ids in `evidence`.
- Every `items[]` entry must have a `label` from exactly: `grounded`, `input`, `inference`, `recommendation`.
  - `grounded`: directly supported by an evidence passage with a cited `[E#]`.
  - `input`: comes from the student profile / Project DNA supplied in the prompt (not from evidence). Say which field it comes from.
  - `inference`: a conclusion drawn from evidence or input. MUST include a non-empty `reasoning` string explaining the logical step. Never label a guess as grounded.
  - `recommendation`: an action you propose. MUST include non-empty `effort` (`low|medium|high`) and a `why` sentence inside the item `text` stating why it matters for this project.
- Never invent an `[E#]`. Never cite an id not present in the supplied passages. If no evidence supports a claim, label it `inference` or put it in `limitations`.

## Specificity and style
- Be specific to THIS project: name the project, its domain, its users, its constraints, and the supplied student profile where relevant. Never write generic advice that fits any project.
- Ban filler and generic openers: no "In today's fast-paced world", "It is important to note", "This project aims to", "Overall", "Moreover", "delve", "landscape is evolving", "leverage synergies", "cutting-edge", "game-changing", "robust", "seamless", "best-in-class". Start with the concrete finding.
- No buzzwords without a cited, concrete meaning. If you cannot cite it, cut it.
- Say what is UNKNOWN explicitly in `limitations`. Missing evidence, weak coverage, and unresolved questions belong there, not in confident claims.

## Novelty honesty
- NEVER call something "Novel" or "novel" unless a prior-art search was actually run in this pipeline and returned no close match. Use `novelty_assessment` evidence only. If prior art is close, say so plainly.
- Absence of evidence in the supplied passages is not evidence of absence. State "no close prior art found in the searched sources" rather than "nobody has done this".

## External facts
- Market numbers, competitor claims, regulation, and funding facts may come ONLY from evidence passages (with `[E#]`) or explicit user input (labelled `input`). Do not recall figures from training data. If you lack a number, write "no evidence supplied for X" in `limitations`.

## Domain overlays (apply when the domain variant is active)
- `design_biotech`: address regulatory pathway, IP/freedom-to-operate, biosafety, and assay validation. Cite evidence or mark unknown.
- `policy_law`: address jurisdiction, stakeholders, legal instruments, comparative examples, and citation/authority checks.
- `tech_builder`: address model and data licences, compute needs, misuse/abuse cases, and benchmark baselines.

## Personalisation (apply in feasibility, tech_stack, roadmap, executive_brief)
The student profile fields `skills`, `weekly_hours`, `budget_usd`, `country`, `education_level`, `goals`, `purpose` (`coursework|research|product`) MUST visibly affect the Recommendations. Name the field and its value in the item text, e.g. "With 6 weekly_hours and $0 budget input, ...". Do not give advice that ignores these constraints.

## Output contract
- Output STRICT JSON only. No prose before or after. No markdown fences. No comments. Emit normal single braces in your JSON output (`{{` in the template is just the loader's escape and must not appear in your answer).
- Match the target schema exactly: no extra top-level keys, no missing required keys. Use empty arrays `[]` when a field has no content.
- `summary`: max 3 sentences, specific to the project. `confidence`: `high|medium|low`. `coverage`: `strong|thin|none`.
- Every item: `id`, `label`, `text`, `evidence` (array of `[E#]` ids, possibly empty), plus `reasoning` when label is `inference`, plus `effort` and a `why` sentence in `text` when label is `recommendation`. `severity` (`low|medium|high|critical`) is optional and used for risks/gaps.
- `generated_by.prompt` must be the exact version string given in the section prompt (e.g. `related_work@v1`). `generated_by.model` is supplied by config.
