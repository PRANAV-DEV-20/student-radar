# STEP 0 — Diagnosis of the legacy Dossier generator

Date: 2026-11-24. This record is kept so the rebuild is traceable.

## Method

One instrumented analysis was run on a real repository
(`https://github.com/fastapi/fastapi`) and one on a raw idea:

> App that detects leaf disease from a phone photo, trained on PlantVillage.
> Farmers in India should get offline advice in their local language.

Instrumentation wrapped Gemini calls, retrieval calls and final assembly. The
`ai_runs` table did not exist at diagnosis time, so token counts could not be
persisted; that absence is itself a finding.

## Observed runs

| Case | Model called | Outcome | Fallback used | Latency | Tokens |
| --- | --- | --- | --- | ---: | --- |
| GitHub repo | `gemini-2.5-flash` (twice) | HTTP 404 — “no longer available to new users” | yes, deterministic | 5255 ms | none recorded (no `ai_runs`) |
| Raw idea | `gemini-2.5-flash` (twice) | HTTP 404 — same message | yes, deterministic | 3628 ms | none recorded (no `ai_runs`) |

Additional failures:

- Embedding call used `text-embedding-004` and failed:
  “not found for API version v1, or is not supported for embedContent”.
- `ai_runs` table: `UndefinedTable('relation "ai_runs" does not exist')`.
- Dossier synthesis, benchmark synthesis and embeddings all silently used
  deterministic fallbacks.
- Exa retrieval returned 0 (no `EXA_API_KEY`). Tavily returned 5 peer and 5
  advanced URLs per run, but only titles/snippets were used; no passages,
  relevance grades or stable evidence ids were stored. `trend_scout` returned a
  Tavily answer and titles with no citable passage.

## Why the output was generic

- The leaf-disease idea received unrelated `community_marketplace` copy:
  “Stable Marriage Matching Algorithm”, “Geospatial Proximity Scorer”, and
  “Campus marketplaces rely on unorganized WhatsApp group chats…”.
  `tech_stack` was empty. This is hardcoded persona template text, not output
  grounded in the submitted idea or retrieved evidence.
- GitHub ingestion fetched only the first 12,000 characters of `README.md`
  from `raw.githubusercontent.com`. Raw HTML was dumped into
  `problem_statement`. No tree, manifest, licence, test, CI or secret scan was
  performed.
- `benchmark_analysis.query_basis` used a generic fallback tagline instead of
  the project's actual problem; README HTML polluted the search query.
- With Gemini down, related-work results copied real URLs/snippets but left
  `student_differentiator` empty, so “how yours differs” was never answered.
- No research plan, no per-question retrieval, no relevance grading, no critic,
  no repair loop, no evidence ids, no section reviews and no personalisation
  inputs existed.

## Resolution of provider configuration

Live probes with the existing `GEMINI_API_KEY` showed the key is valid but the
configured model names were obsolete or quota-limited:

- `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.5-flash-lite`: 404.
- `gemini-3.5-flash`, `gemini-3.6-flash`: initially 200, later 429 quota.
- `gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-flash-latest`: 503 high demand.
- `gemini-embedding-001`: 200, 768 dimensions.
- Working text models with real token counts:
  `gemini-3-flash-preview` (reasoning), `gemini-3.5-flash-lite`,
  `gemini-3.1-flash-lite`, `gemini-flash-lite-latest`.

Dossier v2 initially pinned `gemini-3.5-flash-lite` for bulk work and
`gemini-3-flash-preview` for the critic. Subsequent live probes showed
`3.1-flash-lite` returning 503 and `3-flash-preview` returning 429, so the
current chain uses `gemini-3.5-flash-lite`, `gemini-flash-lite-latest` and
`gemini-3.1-flash-lite` (reordered for critic calls), then the already-configured Groq
`openai/gpt-oss-20b` as a second provider with its own token/cost accounting.
Requests are paced and batched because Gemini still returns transient 503s
under sustained dossier load. Tavily is the configured web provider. No
Anthropic key exists in this repo; adding Anthropic would be a separate
provider decision.
