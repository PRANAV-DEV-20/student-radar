# Dossier v2 implementation decisions

Real-run results and the current provider-quota blocker are recorded in
[`dossier_v2_validation_report.md`](dossier_v2_validation_report.md).

| Spec question | Decision | Reason |
| --- | --- | --- |
| Model quality | `gemini-3.5-flash-lite`, `gemini-flash-lite-latest` and `gemini-3.1-flash-lite` in a paced chain for planning, relevance grading, synthesis and critic; Groq `openai/gpt-oss-20b` as the second-provider fallback | Live probes on 2026-11-24/25: the configured 2.5 models 404; `gemini-3-flash-preview` is quota-limited (429); `gemini-3.1-flash-lite` recovered from an earlier 503. Every call records real token usage and cost. No template fallback exists. |
| Web search provider | Tavily (already configured); Exa remains optional/unused; arXiv, OpenAlex, Semantic Scholar, GitHub, Hugging Face, Europe PMC/PubMed and local corpus are first-class sources | Tavily key is present and returned passage-bearing results during diagnosis. Retrieval is staged per research question, not a single global query. |
| Related people scope | Only people/organisations found in stored evidence or the local opportunity corpus; no model recall from memory | Prevents fabricated founders, investors or researchers. `people_community` must label inferences and cite evidence ids. |
| Quick vs deep | Quick = 8–10 research questions, basic Tavily depth, faster section loop; Deep = 10–20 questions, advanced Tavily depth, cross-section reasoning, critic/repair | Both modes use the same evidence-only pipeline. Quick is a smaller research plan, not a deterministic shortcut. |
| Missing provider | 503 `AI_PROVIDER_NOT_CONFIGURED` and an explicit UI state; never deterministic template text | Required by the spec and enforced in `DossierLLM`, the v2 API and the retired legacy generator. |
| Provider limits | Evidence prompts are capped at 8 passages / 900 chars each; Groq calls are serialised and capped at 3072 completion tokens | The first real runs hit Gemini 429/503 and Groq's 8k TPM request ceiling. Compaction keeps every provider usable without lowering evidence standards; full passages remain stored for citation checks. |
| Model chain | Dossier calls use `gemini-3.5-flash-lite`, `gemini-flash-lite-latest`, `gemini-3.1-flash-lite`, then Groq; a model returning 429/503/413/timeout is cooled down and requests are paced 5 s per Gemini model | Probes on 2026-11-25: 3-flash-preview 429 (excluded), 3.1-flash-lite 200 after recovering from an earlier 503, 3.5-flash-lite and flash-lite-latest 200 before the third run then 429 during a quota burst. Keeping three live-tested ids avoids a single-model quota wall. |
| Call budget | Relevance is graded in four-question batches; sections are synthesised three at a time (7 calls instead of 18); the critic and swap test run in one batched audit; a transient 503 gets at most two paced waves; the whole run has a 220 s deadline | A real run made ~90 model calls and spent 475 s, mostly on provider errors. Another run stalled at 15/18 sections and had to be killed at 600 s. Batching plus a hard deadline keeps the full pipeline inside the four-minute target while retaining the critic/repair loop. |
| Honest status | A run is `succeeded` only when all 18 sections were really generated; otherwise `partial`/`failed` | A real run exposed that synthesis failure placeholders were being labelled as success. Status now reflects generation reality. |
| Legacy generator | Deterministic dossier fallback removed from the active generation path; legacy ingest endpoints return `410 LEGACY_DOSSIER_GENERATOR_RETIRED` and point to v2 | No silent generic output. The heuristic helper remains only as a neutral input-grounded schema base for successful model parsing. |

## Configured keys

- `GEMINI_API_KEY` — required. Existing key is valid; obsolete model names were the issue.
- `GROQ_API_KEY` — configured in this repo and used as the dossier fallback model `openai/gpt-oss-20b` when Gemini is quota-limited.
- `TAVILY_API_KEY` — used for web retrieval.
- `EXA_API_KEY` — empty; no dependency on it.
- `GITHUB_TOKEN` — optional, raises GitHub API rate limit.
- `ANTHROPIC_API_KEY` — not present; adding Anthropic would be a separate provider integration.

See `backend/.env.example` for safe placeholder values.
