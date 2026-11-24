# Dossier v2 evaluation pack

This pack contains the real, public GitHub repositories used for manual and
automated acceptance checks. No API keys or secrets are stored here.

## Inputs

- `repos.json` — five real public repositories, each with the persona and
  signals a correct dossier should surface.
- Raw-idea control case (used for the specificity/personalisation test):

  > App that detects leaf disease from a phone photo, trained on PlantVillage.
  > Farmers in India should get offline advice in their local language.

## How to run a real eval

1. Start the backend with `GEMINI_API_KEY`, `GROQ_API_KEY` (provider fallback)
   and `TAVILY_API_KEY` set.
2. Create a run:

   ```bash
   curl -X POST http://localhost:8000/api/v1/dossiers/v2/runs \
     -H 'Content-Type: application/json' \
     -H 'X-Guest-Session-ID: eval_leaf_001' \
     -d '{
       "input_type": "idea",
       "raw_content": "App that detects leaf disease from a phone photo, trained on PlantVillage. Farmers in India should get offline advice in their local language.",
       "domain_persona": "design_biotech",
       "mode": "deep",
       "profile": {
         "skills": ["Python", "OpenCV"],
         "weekly_hours": 8,
         "budget_usd": 120,
         "country": "India",
         "education_level": "undergraduate",
         "goals": ["usable offline prototype", "field validation"],
         "purpose": "research"
       }
     }'
   ```

3. Stream progress from the returned `stream_url`, then fetch the run state to
   inspect `sections`, `evidence`, `ai_runs`, `reviews`, `coverage`, `cost_usd`
   and `duration_ms`.

   For all five repositories at once, run:

   ```bash
   python evals/dossier_v2/run_eval.py --mode deep --out evals/dossier_v2/results/deep.json
   ```

## Acceptance checklist

- Each repo finishes in deep mode in under 4 minutes.
- Related work contains real, clickable URLs that resolve to retrieved evidence
  ids (`E#`). No invented projects, metrics, licences or competitors.
- GitHub ingestion reports tests/CI/licence from the repository tree; README
  performance claims without evaluation artifacts are flagged, not repeated as
  fact.
- The leaf-disease idea does **not** receive marketplace/Stable-Marriage copy.
- Feasibility, tech stack, roadmap and executive brief visibly use the profile
  (India, offline, 8 h/week, $120, Python/OpenCV).
- Thin sections say so in `limitations` and carry `coverage: thin|none`.
- If the provider key/model is unavailable the run fails with
  `AI_PROVIDER_NOT_CONFIGURED` (or an explicit provider error) and no template
  text is produced.
- `ai_runs` rows show model, token counts, latency, fallback flag and real cost
  for every model call.
- `GET /runs/{id}/diff?from=1&to=2` shows what a re-run/deepen changed.

## Auditing a completed run

```bash
python evals/dossier_v2/audit_run.py <run-id>
```

The audit reads stored Postgres state only. It reports duration, real model
calls and cost in `ai_runs`, evidence sources, unresolved/invalid citation ids,
unsupported-claim rate, real related-work URLs, repo-specific gaps, profile
awareness in the tech stack, and whether any section is a failure placeholder.

## Automated gates

Run `pytest -q tests/test_dossier_v2.py` from `backend/`. The tests cover
fabricated claims, unresolved evidence ids, real related-work links, citation
verification, specificity, thin-coverage honesty and the missing-key state.
