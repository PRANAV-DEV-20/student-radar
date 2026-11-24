# Relevance judge — multi-question passage scoring (relevance_batch@v1)

## Shared rules
Follow ALL rules in `shared.md`, especially STRICT JSON output. This task judges retrieved text; it does not generate dossier content.

## Inputs
Questions: {questions} — JSON array. Each entry has `id`, `question`, and `passages` (each passage has `ref`, `title`, `url`, `source`, and `passage`).
Mode: {mode}.

## Task
For EACH question, rate every one of its supplied passages from 0 to 3 for how directly it helps answer that question.
- `0` = irrelevant: wrong topic, wrong domain, or no usable claim.
- `1` = weak: tangential mention, or a claim too vague/old to use without more evidence.
- `2` = useful: partially answers the question or gives a concrete adjacent fact.
- `3` = direct: squarely answers the question with specific, citable detail.

Penalties (usually 0–1 even if text looks topical): generic homepages, login pages, tag/category pages, search-result pages, resource lists with no specific claim, wrong-topic buzzword matches, and marketing copy with no verifiable detail about the project's users or method. Judge on passage text only; do not penalise unfamiliar terminology. Reserve `3` for passages you would actually cite.

## Output — STRICT JSON only
{{"ratings":[{{"question_id":"Q1","ref":"E1","relevance":0,"reason":"short"}}]}}

Rules for output:
- One entry per supplied passage, using its exact `question_id` and `E#` ref. No missing or extra pairs.
- `relevance` is an integer 0–3. `reason` is one short concrete sentence (max ~20 words).
- No extra keys, no prose, no markdown fences.
