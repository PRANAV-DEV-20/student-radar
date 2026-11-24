# Relevance judge — passage batch scoring (relevance@v1)

## Shared rules
Follow ALL rules in `shared.md`, especially evidence-only claims and STRICT JSON output. This task judges retrieved text; it does not generate dossier content.

## Inputs
Question: {question} (one research question with its target section(s)).
Passages: {passages} (retrieved passages, each with a reference id `E#`, `source_type`, `title`, `url`, and text).
Mode: {mode}.

## Task
Rate every supplied passage from 0 to 3 for how directly it helps answer the question.
- `0` = irrelevant: wrong topic, wrong domain, or no usable claim.
- `1` = weak: tangential mention, or a claim too vague/old to use without more evidence.
- `2` = useful: partially answers the question or gives a concrete adjacent fact.
- `3` = direct: squarely answers the question with specific, citable detail.

Penalties (usually 0–1 even if text looks topical):
- Generic homepages, landing pages, login/signup pages, tag/category pages, search-result pages, or "resource lists" with no specific claim.
- Wrong-topic results that merely share a buzzword with the question.
- Marketing copy with no verifiable detail about the project's actual domain/users/methods.
- Passages whose facts cannot be tied to the named project or its domain.

Do NOT penalise: a source you dislike, a source you cannot recall, or a source with unfamiliar terminology — judge on the passage text only. Prefer precision over generosity; reserve `3` for passages you would actually cite.

## Output — STRICT JSON only
{{"ratings":[{{"ref":"E1","relevance":0,"reason":"short"}}]}}

Rules for output:
- One `ratings` entry per supplied passage, using its exact `E#` as `ref`. No missing or extra refs.
- `relevance` is an integer 0–3. `reason` is one short concrete sentence (max ~20 words) tied to the question.
- No extra keys, no prose, no markdown fences.
