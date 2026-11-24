# Dossier v2 validation report (2026-11-25)

This report records what was actually executed, what passed, and the one
remaining external blocker. It intentionally does not claim a successful
end-to-end run where none exists.

## What is implemented

- `005_dossier_v2` migration, ORM models, v2 schemas/validators and the
  evidence-only 8-stage pipeline with SSE progress.
- 18 v2 sections, versioned prompts, staged retrieval, relevance grading,
  batched synthesis, batched critic/swap-test audit and bounded repair.
- `ai_runs` accounting for model, tokens, latency, attempts, fallback, cache
  and cost for every successful call, plus explicit failed-call rows.
- Evidence IDs are validated against stored rows; grounded claims are checked
  against the cited passage and unsupported items are removed.
- Missing provider returns `503 AI_PROVIDER_NOT_CONFIGURED`; the legacy
  deterministic generator endpoints return `410 LEGACY_DOSSIER_GENERATOR_RETIRED`.
- QA suite, eval harness (`evals/dossier_v2/`) and run auditor
  (`evals/dossier_v2/audit_run.py`).

## Automated checks

| Check | Result |
| --- | --- |
| `python -m compileall -q app alembic/versions` | pass |
| `python -m pytest -q` (108 tests) | pass |
| `npx next build` from `frontend/` (after stopping a concurrent `next dev` that shared `.next`) | pass; `/dossier-v2` in route list |
| Missing-provider 503 and legacy-retirement tests | pass |

## Real GitHub runs

Input: `https://github.com/fastapi/fastapi`. Profile: Python/OpenCV, 8 h/week,
$120, India, undergraduate, research prototype goals. Mode: quick unless noted.

| Run | Status | Duration | Cost | Sections | Evidence | Notes |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `febb8361-beb3-4cff-95d8-532a3eeddb71` | failed | 615.57 s | — | 0 | — | Missing `cross_novelty_assessment.md`; prompt added and test locked it in. |
| `8b4624f9-724e-41f9-8cc3-528a4528e02f` | succeeded (wrongly) | 257.6 s | — | 18 | — | 17 sections were failure placeholders; honest status logic added. |
| `b420abfe-26cb-4f2d-b59f-66c87ae5abf1` | partial | 475.27 s | — | 18 | — | Placeholder synthesis under provider retries; pacing/cooldown added. |
| `de7e9b17-49e2-4268-a008-bed419c619e6` | failed | 23.7 s | $0.0007 | 18 placeholders | 112 | All models cooling after a 9-way relevance burst. |
| `bc409912-7da9-46d3-83c8-22763b341144` | partial | 240.82 s | $0.0221 | 18 (15 placeholders) | 108 | 49 `ai_runs`, 20 reviews / 18 failed; 2 grounded claims, 0 unsupported, 0 unresolved refs; no real related-work URLs, no `fastapi` in gaps, no profile terms in stack. |
| `a616e2f0-1b2f-4d68-970f-6af8bc876463` | failed | 49.34 s | $0.0000 | 0 | 0 | Both Gemini models 503, Groq 429 at run start. |
| `e8ffcad6-3e00-4c9d-a9c4-5ec5e5b164a6` | stuck → killed | >600 s | — | 15 | 11 | Repeated synthesis retries; hard 220 s deadline and batching added afterwards. |
| `cce351d6-5a20-4f50-a62b-286b777a25a0` | failed | 66.72 s | $0.0000 | 0 | 0 | Planner wave timed out during a provider connection reset. |
| `c064695f-d012-48f0-a060-86a0aa085c78` | failed | 220.08 s | $0.0032 | 8 | 32 | Honest deadline hit; batch synthesis failed under combined Gemini 429 / Groq daily cap. |
| `894be58a-bed2-4d71-9878-d44eb4f6f7ae` | failed | 67.4 s | $0.0000 | 0 | 0 | Gemini 429/503 and Groq 199,042/200,000 daily tokens. |

The audit command used for the best real run was:

```bash
python evals/dossier_v2/audit_run.py bc409912-7da9-46d3-83c8-22763b341144
```

## Current blocker

The configured free-tier provider quotas are exhausted. Live probes on
2026-11-25 returned:

- `gemini-3.5-flash-lite`: 429 quota
- `gemini-flash-lite-latest`: 429 quota
- `gemini-3.1-flash-lite`: 503 high demand (200 in an earlier probe)
- `gemini-3-flash-preview`: 429 quota (excluded from the chain)
- `groq:openai/gpt-oss-20b`: 199,042 / 200,000 daily tokens used

No deterministic fallback is enabled, so the correct behaviour is the honest
failed/partial state shown above. A successful <4 minute real run, the five-repo
eval sweep, the raw-idea control and the `/diff` demonstration still require
provider capacity to be restored or a paid/quota-increasing key.

## Next action

Re-run once provider capacity is available:

```bash
python "C:\Users\Pranav Dev\AppData\Local\Temp\opencode\run_real_dossier.py" quick github
python evals/dossier_v2/audit_run.py <run-id>
python evals/dossier_v2/run_eval.py --mode deep --out evals/dossier_v2/results/deep.json
```
