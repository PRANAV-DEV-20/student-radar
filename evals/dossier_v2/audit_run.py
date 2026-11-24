"""Audit a real Dossier v2 run against the acceptance checklist.

Usage:
    python evals/dossier_v2/audit_run.py <run-id>

Prints one JSON object. It reads only run state stored in Postgres; it never
reads credentials or calls a provider.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("APP_ENV", "production")
BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

from sqlalchemy import text  # noqa: E402

from app.core.database import engine  # noqa: E402
from app.schemas.dossier_v2 import SECTION_KEYS, check_evidence_support  # noqa: E402


def _text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, default=str) if not isinstance(value, str) else value


async def audit(run_id: str) -> dict:
    async with engine.connect() as conn:
        run = (await conn.execute(text("""
            select status, mode, input_type, domain_persona, cost_usd, duration_ms,
                   project_dna, profile, plan
            from dossier_runs where id=:r
        """), {"r": run_id})).mappings().first()
        if not run:
            raise SystemExit(f"Unknown run id: {run_id}")

        sections_rows = (await conn.execute(text(
            "select section, content, confidence, coverage from dossier_sections where run_id=:r"
        ), {"r": run_id})).mappings().all()
        sections = {row["section"]: dict(row["content"] or {}) for row in sections_rows}

        evidence_rows = (await conn.execute(text("""
            select ref, url, title, source, passage, relevance from evidence where run_id=:r
        """), {"r": run_id})).mappings().all()
        evidence = {row["ref"]: dict(row) for row in evidence_rows}

        calls = (await conn.execute(text("""
            select role, model, success, prompt_tokens, output_tokens, total_tokens,
                   latency_ms, attempts, fallback_used, cached, cost_usd
            from ai_runs where run_id=:r order by created_at
        """), {"r": run_id})).mappings().all()

        reviews = (await conn.execute(text("""
            select section, attempt, passed, failures from section_reviews where run_id=:r
        """), {"r": run_id})).mappings().all()

        versions = (await conn.execute(text(
            "select version from dossier_versions where run_id=:r order by version"
        ), {"r": run_id})).scalars().all()

    known_refs = set(evidence)
    all_refs: set[str] = set()
    supported = 0
    unsupported = 0
    unresolved = 0
    for section in sections.values():
        for item in section.get("items") or []:
            if item.get("label") != "grounded":
                continue
            refs = [str(ref) for ref in (item.get("evidence") or [])]
            all_refs.update(refs)
            for ref in refs:
                if ref not in known_refs:
                    unresolved += 1
                    continue
                if check_evidence_support(str(item.get("text") or ""), str(evidence[ref]["passage"] or "")):
                    supported += 1
                else:
                    unsupported += 1
        for table in section.get("tables") or []:
            columns = [str(c) for c in (table.get("columns") or [])]
            if "evidence_ids" in columns:
                index = columns.index("evidence_ids")
                for row in table.get("rows") or []:
                    if len(row) > index:
                        refs = re.findall(r"E\d+", _text(row[index]))
                        all_refs.update(refs)
                        unresolved += sum(1 for ref in refs if ref not in known_refs)

    related = sections.get("related_work") or {}
    related_urls = sorted({
        str(evidence[ref]["url"])
        for ref in all_refs
        if ref in known_refs and str(evidence[ref]["url"] or "").startswith("http")
        and _text(related).find(ref) >= 0
    })

    dna = dict(run["project_dna"] or {})
    profile = dict(run["profile"] or {})
    gaps_text = _text(sections.get("gaps") or {}).lower()
    stack_text = _text(sections.get("tech_stack") or {}).lower()
    repo_name = str(dna.get("url") or dna.get("title") or "").rstrip("/").split("/")[-1].lower()
    profile_terms = [str(v).lower() for v in (profile.get("skills") or [])]
    for key in ("country", "education_level"):
        if profile.get(key):
            profile_terms.append(str(profile[key]).lower())
    if profile.get("weekly_hours"):
        profile_terms.append(f"{profile['weekly_hours']} h")
    if profile.get("budget_usd"):
        profile_terms.append(f"${profile['budget_usd']}")

    failures = []
    for review in reviews:
        for failure in (review["failures"] or []):
            reason = str((failure or {}).get("reason") or "")
            kind = "provider_outage" if "All models failed" in reason else "content"
            failures.append((review["section"], review["attempt"], kind, reason[:120]))

    total_claims = supported + unsupported
    return {
        "run_id": run_id,
        "status": run["status"],
        "mode": run["mode"],
        "duration_seconds": round(int(run["duration_ms"] or 0) / 1000, 2),
        "under_four_minutes": int(run["duration_ms"] or 0) < 240_000,
        "cost_usd": float(run["cost_usd"] or 0),
        "section_count": len(sections),
        "missing_sections": sorted(set(SECTION_KEYS) - set(sections)),
        "placeholder_sections": sorted(
            key for key, value in sections.items()
            if "Generation failed" in str(value.get("summary") or "")
        ),
        "evidence_count": len(evidence),
        "evidence_by_source": {
            source: sum(1 for row in evidence.values() if row["source"] == source)
            for source in sorted({row["source"] for row in evidence.values()})
        },
        "ai_run_calls": len(calls),
        "ai_runs": [
            {
                "role": row["role"], "model": row["model"], "success": bool(row["success"]),
                "tokens": int(row["total_tokens"] or 0), "latency_ms": int(row["latency_ms"] or 0),
                "fallback_used": bool(row["fallback_used"]), "cached": bool(row["cached"]),
                "cost_usd": float(row["cost_usd"] or 0),
            }
            for row in calls
        ],
        "citation_check": {
            "grounded_claims_with_citations": total_claims,
            "supported": supported,
            "unsupported": unsupported,
            "unsupported_rate": round(unsupported / total_claims, 4) if total_claims else None,
            "unresolved_refs": unresolved,
        },
        "related_work": {
            "real_evidence_urls": related_urls,
            "has_real_links": bool(related_urls),
        },
        "repo_specific_gaps": {
            "repo_name": repo_name,
            "mentioned_in_gaps": bool(repo_name and repo_name in gaps_text),
        },
        "profile_aware_stack": {
            "terms": profile_terms,
            "matched": [term for term in profile_terms if term and term in stack_text],
        },
        "reviews": {
            "total": len(reviews),
            "failed": sum(1 for row in reviews if not row["passed"]),
            "provider_outage_failures": sum(1 for f in failures if f[2] == "provider_outage"),
            "content_failures": sum(1 for f in failures if f[2] == "content"),
        },
        "versions": list(versions),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(audit(args.run_id)), indent=2, ensure_ascii=False))
