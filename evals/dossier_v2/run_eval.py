"""Run the five real GitHub repos through a live Dossier v2 backend.

Usage:
    python evals/dossier_v2/run_eval.py --mode deep --out evals/dossier_v2/results/deep.json

The script stores only run metadata and generated dossier state. It never
reads, prints, or writes API keys.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
DEFAULT_API = "http://localhost:8000/api/v1"
TERMINAL = {"succeeded", "partial", "failed"}


async def run_one(client: httpx.AsyncClient, api: str, repo: dict, mode: str, profile: dict) -> dict:
    payload = {
        "input_type": "github",
        "raw_content": repo["url"],
        "domain_persona": repo.get("domain_persona", "tech_builder"),
        "mode": mode,
        "profile": profile,
    }
    response = await client.post(
        f"{api}/dossiers/v2/runs",
        json=payload,
        headers={"X-Guest-Session-ID": f"eval_{repo['url'].rstrip('/').split('/')[-1]}"},
    )
    response.raise_for_status()
    launched = response.json()
    run_id = launched["run_id"]
    started = time.monotonic()

    while True:
        state = (await client.get(f"{api}/dossiers/v2/runs/{run_id}")).json()
        if state.get("status") in TERMINAL:
            state["eval"] = {
                "url": repo["url"],
                "why": repo.get("why"),
                "expected_signals": repo.get("expected_signals", []),
                "mode": mode,
                "wall_seconds": round(time.monotonic() - started, 2),
                "under_four_minutes": time.monotonic() - started < 240,
            }
            return state
        if time.monotonic() - started > 300:
            state["eval"] = {"url": repo["url"], "mode": mode, "timed_out": True}
            return state
        await asyncio.sleep(3)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--mode", choices=["quick", "deep"], default="deep")
    parser.add_argument("--out", default=str(HERE / "results" / "latest.json"))
    args = parser.parse_args()

    repos = json.loads((HERE / "repos.json").read_text(encoding="utf-8"))
    profile = {
        "skills": ["Python", "OpenCV"],
        "weekly_hours": 8,
        "budget_usd": 120,
        "country": "India",
        "education_level": "undergraduate",
        "goals": ["usable prototype", "field validation"],
        "purpose": "research",
    }
    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        for repo in repos:
            print(f"Running {repo['url']} ({args.mode})", flush=True)
            results.append(await run_one(client, args.api, repo, args.mode, profile))
            state = results[-1]
            print(
                "  ",
                state.get("status"),
                f"{state.get('eval', {}).get('wall_seconds')}s",
                f"sections={len(state.get('sections') or {})}",
                f"evidence={len(state.get('evidence') or [])}",
                f"cost={state.get('cost_usd')}",
                flush=True,
            )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
