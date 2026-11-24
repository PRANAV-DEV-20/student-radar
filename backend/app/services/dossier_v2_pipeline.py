"""Dossier v2 research pipeline (stages 1-8).

Runs as a background job. Progress and completed sections are emitted through
an async callback so the API can stream them over SSE. There is no template
path: a missing or unusable model produces an explicit failed state.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.dossier import ProjectDossier
from app.models.dossier_v2 import (
    AIRun,
    DossierRun,
    DossierSection,
    DossierSource,
    DossierVersion,
    Evidence,
    SectionReview,
)
from app.schemas.dossier_v2 import (
    CROSS_SECTIONS,
    FIRST_PASS_SECTIONS,
    SECTION_KEYS,
    check_evidence_support,
    validate_section_payload,
)
from app.services.dossier_v2_ingest import build_project_dna
from app.services.dossier_v2_prompts import load_prompt, prompt_version
from app.services.dossier_v2_retrieval import RetrievedItem, DossierRetriever
from app.services.ingestion_agent import IngestionAgent
from app.services.llm_client import DossierLLM, LLMCallError, LLMNotConfigured, parse_json_text

logger = logging.getLogger(__name__)

Emitter = Callable[[str, Dict[str, Any]], Awaitable[None]]
DOMAIN_VARIANTS = {
    "tech_builder": "AI/tech: model and data licences, compute and cost, misuse/security, benchmark baselines.",
    "design_biotech": "Biotech: regulatory pathway, IP/patent timing, biosafety, assay validation.",
    "policy_law": "Law/policy: jurisdiction map, stakeholders, instruments, comparative approaches, citation checks.",
    "business_finance": "Business: unit economics, paying customer, adoption barriers, funding evidence.",
}


def _json(value: Any, limit: int = 30000) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, indent=2)[:limit]


class PipelineError(RuntimeError):
    pass


class DossierPipeline:
    def __init__(self, run_id: uuid.UUID, emit: Emitter, session_factory: async_sessionmaker = AsyncSessionLocal):
        self.run_id = run_id
        self.emit = emit
        self.session_factory = session_factory
        self.cost_usd = 0.0
        self.started = time.perf_counter()
        self.llm: Optional[DossierLLM] = None
        self.run: Optional[DossierRun] = None
        self.dna: Dict[str, Any] = {}
        self.profile: Dict[str, Any] = {}
        self.questions: List[Dict[str, Any]] = []
        self.evidence_by_ref: Dict[str, Dict[str, Any]] = {}
        self.evidence_rows: Dict[str, Evidence] = {}
        self.curated: Dict[str, List[Dict[str, Any]]] = {}
        self.coverage: Dict[str, str] = {}
        self.sections: Dict[str, Dict[str, Any]] = {}
        self.rating_fallback_used = False
        self.failed_critic: List[str] = []
        self.failed_sections: List[str] = []

    # ------------------------------------------------------------------ utils
    async def _record_call(self, result: Any, role: str) -> None:
        self.cost_usd += float(result.cost_usd or 0.0)
        try:
            async with self.session_factory() as db:
                db.add(AIRun(
                    run_id=self.run_id,
                    role=role,
                    model=result.model,
                    success=True,
                    prompt_tokens=result.prompt_tokens,
                    output_tokens=result.output_tokens,
                    total_tokens=int(result.usage.get("total_token_count") or 0),
                    latency_ms=result.latency_ms,
                    attempts=result.attempts,
                    fallback_used=result.attempts > 1,
                    cached=False,
                    cost_usd=result.cost_usd,
                ))
                await db.commit()
        except Exception as exc:
            logger.warning("Could not persist ai_runs row: %s", exc)

    async def _record_error(self, role: str, chain: List[str], attempts: int, error: str) -> None:
        try:
            async with self.session_factory() as db:
                db.add(AIRun(
                    run_id=self.run_id,
                    role=role,
                    model=chain[-1] if chain else "unknown",
                    success=False,
                    attempts=attempts,
                    fallback_used=attempts > 1,
                    cost_usd=0,
                    error=error[:2000],
                ))
                await db.commit()
        except Exception as exc:
            logger.warning("Could not persist failed ai_runs row: %s", exc)

    async def _progress(self, stage: str, message: str, **extra: Any) -> None:
        payload = {
            "stage": stage,
            "message": message,
            "completed_sections": len(self.sections),
            "total_sections": len(SECTION_KEYS),
            **extra,
        }
        if self.run:
            self.run.progress = payload
        await self.emit("progress", payload)

    def _save_progress_sync(self) -> None:
        if self.run:
            self.run.progress = {
                "stage": "running",
                "message": "Research in progress",
                "completed_sections": len(self.sections),
                "total_sections": len(SECTION_KEYS),
            }

    async def _persist(self, db: AsyncSession) -> None:
        db.add(self.run)
        await db.commit()

    def _evidence_for(self, section: str) -> List[Dict[str, Any]]:
        refs: Set[str] = set()
        for question in self.questions:
            if section in (question.get("sections") or []):
                refs.update(item["ref"] for item in self.curated.get(str(question.get("id")), []))
        # Cross sections also see the strongest evidence from every first-pass
        # question so they can reason across the whole dossier.
        if section in CROSS_SECTIONS:
            for items in self.curated.values():
                refs.update(item["ref"] for item in items if item.get("relevance", 0) >= 3)
        items = [self.evidence_by_ref[ref] for ref in refs if ref in self.evidence_by_ref]
        # Keep model prompts small enough for the second provider's 8k TPM
        # ceiling. Full passages remain in evidence_by_ref for citation checks.
        return [
            {**item, "passage": str(item.get("passage") or "")[:900]}
            for item in sorted(items, key=lambda item: (-int(item.get("relevance") or 0), item["ref"]))[:8]
        ]

    @staticmethod
    def _coverage_for(items: Sequence[Dict[str, Any]]) -> str:
        strong = [item for item in items if int(item.get("relevance") or 0) >= 2]
        if len(strong) >= 5:
            return "strong"
        if strong:
            return "thin"
        return "none"

    @staticmethod
    def _finalize_coverage(payload: Dict[str, Any], coverage: str, passed_review: bool) -> str:
        """Downgrade confidence and state limitations when evidence is thin."""
        confidence = payload.get("confidence") or "low"
        if coverage == "none":
            confidence = "low"
            limitations = payload.setdefault("limitations", [])
            message = "No retrieved evidence covered this section."
            if message not in limitations:
                limitations.append(message)
        elif coverage == "thin" and confidence == "high":
            confidence = "medium"
        if not passed_review and confidence != "low":
            confidence = "medium"
        payload["confidence"] = confidence
        payload["coverage"] = coverage
        return confidence

    # ------------------------------------------------------------- stage 1-2
    async def _stage_ingest(self, db: AsyncSession) -> None:
        await self._progress("ingest", "Reading your " + ("repository" if self.run and self.run.input_type == "github" else "submission"))
        self.dna = await build_project_dna(
            input_type=self.run.input_type,
            raw_content=self.run.raw_content,
            domain_persona=self.run.domain_persona,
        )
        if self.dna.get("ingest_error"):
            raise PipelineError(self.dna["ingest_error"])
        self.run.project_dna = self.dna
        if self.dna.get("title"):
            self.dna.setdefault("title", "Student project")
        await self._persist(db)

    async def _stage_plan(self) -> None:
        await self._progress("plan", "Planning research questions")
        prompt = load_prompt(
            "planner",
            project_dna=_json(self.dna, 2500),
            student_profile=_json(self.profile, 1200),
            mode=self.run.mode if self.run else "deep",
            domain_variant=DOMAIN_VARIANTS.get(self.run.domain_persona if self.run else "tech_builder", ""),
        )
        result = await self.llm.generate_json(
            load_prompt("shared"), prompt, role="planning", max_output_tokens=4096,
            timeout_seconds=settings.DOSSIER_V2_LLM_TIMEOUT_SECONDS,
        )
        parsed = result.parsed if isinstance(result.parsed, dict) else {}
        questions = parsed.get("questions") if isinstance(parsed, dict) else None
        if not isinstance(questions, list):
            raise PipelineError("Research planner returned no questions")
        cleaned: List[Dict[str, Any]] = []
        for index, item in enumerate(questions, start=1):
            if not isinstance(item, dict):
                continue
            sections = [str(s) for s in (item.get("sections") or []) if s in SECTION_KEYS]
            queries = [str(q).strip()[:300] for q in (item.get("queries") or []) if str(q).strip()][:4]
            source_types = [str(s) for s in (item.get("source_types") or []) if s in {
                "local_corpus", "github", "papers", "web", "opportunities", "datasets"
            }]
            if not sections or not queries or not source_types:
                continue
            cleaned.append({
                "id": str(item.get("id") or f"Q{index}"),
                "question": str(item.get("question") or queries[0])[:500],
                "sections": sections,
                "queries": queries,
                "source_types": source_types,
            })
        minimum = 8 if self.run.mode == "quick" else 10
        if len(cleaned) < minimum:
            raise PipelineError(f"Research planner produced only {len(cleaned)} usable questions (minimum {minimum})")
        self.questions = cleaned[:20]
        self.run.plan = {
            "questions": self.questions,
            "prompt": "planner@v1",
            "model": result.model,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._progress("plan", f"Planned {len(self.questions)} research questions", questions=len(self.questions))

    # ------------------------------------------------------------ stage 3-4
    async def _stage_retrieve(self, db: AsyncSession) -> None:
        await self._progress("retrieve", f"Searching sources for {len(self.questions)} questions")
        import httpx

        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True,
                                     headers={"User-Agent": "LaunchPad-Dossier-v2/1.0"}) as client:
            retriever = DossierRetriever(db, client)
            semaphore = asyncio.Semaphore(settings.DOSSIER_V2_MAX_QUESTION_WORKERS)

            async def one(question: Dict[str, Any]) -> List[RetrievedItem]:
                async with semaphore:
                    return await retriever.retrieve_question(
                        question=question,
                        dna=self.dna,
                        domain_persona=self.run.domain_persona,
                        mode=self.run.mode,
                    )

            batches = await asyncio.gather(*(one(q) for q in self.questions), return_exceptions=True)
        rows: List[RetrievedItem] = []
        for batch in batches:
            if isinstance(batch, list):
                rows.extend(batch)
        await self._store_evidence(db, rows)
        await self._progress("retrieve", f"Stored {len(rows)} retrieved passages", passages=len(rows))

    async def _store_evidence(self, db: AsyncSession, items: Sequence[RetrievedItem], question_id: Optional[str] = None) -> None:
        existing = {row.ref for row in (await db.execute(select(Evidence.ref).where(Evidence.run_id == self.run_id))).scalars()}
        next_num = max([int(ref[1:]) for ref in existing if re.match(r"E\d+", ref)] or [0]) + 1
        seen_keys: Set[str] = set()
        added: List[Evidence] = []
        for item in items:
            if item.canonical_key in seen_keys:
                continue
            seen_keys.add(item.canonical_key)
            ref = f"E{next_num}"
            next_num += 1
            record = {
                "ref": ref,
                "title": item.title,
                "url": item.url,
                "source": item.source,
                "source_quality": item.source_quality,
                "passage": item.passage,
                "relevance": 0,
                "question_id": question_id or item.question_id,
                "canonical_key": item.canonical_key,
                "retrieved_at": item.retrieved_at,
            }
            self.evidence_by_ref[ref] = record
            row = Evidence(run_id=self.run_id, **record)
            self.evidence_rows[ref] = row
            added.append(row)
            db.add(row)
            db.add(DossierSource(
                run_id=self.run_id, ref=ref, url=item.url, title=item.title,
                source=item.source, source_quality=item.source_quality,
                retrieved_at=item.retrieved_at,
            ))
        await db.commit()

    async def _stage_curate(self, db: AsyncSession) -> None:
        await self._progress("curate", "Grading retrieved evidence")
        known_refs = set(self.evidence_by_ref)
        # One judge call per four questions. Nine parallel calls were enough to
        # exhaust every free-tier provider before section synthesis even began.
        grouped: List[Dict[str, Any]] = []
        for question in self.questions:
            qid = str(question["id"])
            items = [item for item in self.evidence_by_ref.values() if item["question_id"] == qid]
            passages = [
                {"ref": item["ref"], "title": item["title"], "url": item["url"],
                 "source": item["source"], "passage": item["passage"][:400]}
                for item in items[:8]
            ]
            grouped.append({"id": qid, "question": question["question"], "passages": passages})

        ratings: Dict[tuple[str, str], int] = {}
        for start in range(0, len(grouped), 4):
            chunk = grouped[start:start + 4]
            prompt = load_prompt(
                "relevance_batch", questions=_json(chunk, 14000), mode=self.run.mode
            )
            try:
                result = await self.llm.generate_json(
                    load_prompt("shared"), prompt, role="extraction", max_output_tokens=4096,
                    timeout_seconds=settings.DOSSIER_V2_LLM_TIMEOUT_SECONDS,
                )
                parsed = result.parsed if isinstance(result.parsed, dict) else {}
                raw_ratings = parsed.get("ratings") if isinstance(parsed, dict) else None
                for entry in raw_ratings if isinstance(raw_ratings, list) else []:
                    if not isinstance(entry, dict):
                        continue
                    qid = str(entry.get("question_id") or "")
                    ref = str(entry.get("ref") or "")
                    try:
                        score = max(0, min(3, int(entry.get("relevance", 0))))
                    except (TypeError, ValueError):
                        score = 0
                    if ref in known_refs:
                        ratings[(qid, ref)] = score
            except (LLMCallError, LLMNotConfigured) as exc:
                logger.warning("Relevance batch %s failed: %s", start // 4, exc)
                self.rating_fallback_used = True
                for entry in chunk:
                    terms = set(re.findall(r"[a-z0-9]{4,}", entry["question"].lower()))
                    for item in entry["passages"]:
                        overlap = sum(1 for term in terms if term in item["passage"].lower())
                        ratings[(entry["id"], item["ref"])] = 2 if overlap >= 2 else 1 if overlap == 1 else 0

        for question in self.questions:
            qid = str(question["id"])
            items = [item for item in self.evidence_by_ref.values() if item["question_id"] == qid]
            if not items:
                self.curated[qid] = []
                self.coverage[qid] = "none"
                continue
            best: List[Dict[str, Any]] = []
            for item in items:
                item["relevance"] = ratings.get((qid, item["ref"]), 0)
                row = self.evidence_rows.get(item["ref"])
                if row is not None:
                    row.relevance = item["relevance"]
                if item["relevance"] >= 2:
                    best.append(item)
            best = sorted(best, key=lambda item: (-item["relevance"], item["ref"]))[:12]
            self.curated[qid] = best
            self.coverage[qid] = self._coverage_for(best)

        self.run.coverage = self.coverage
        await db.commit()
        await self._progress("curate", "Evidence curated and coverage measured", coverage=self.coverage)

    # ------------------------------------------------------------- stage 5-7
    def _section_spec(self, section: str, repair_notes: str, cross: bool) -> tuple[str, List[Dict[str, Any]], str]:
        """Render the versioned specification for one section."""
        evidence = self._evidence_for(section)
        coverage = self._coverage_for(evidence)
        prompt_file = f"cross_{section}" if cross else section
        prompt = load_prompt(
            prompt_file,
            section=section,
            project_dna=_json(self.dna, 2500),
            student_profile=_json(self.profile, 1200),
            evidence=_json(evidence),
            sections=_json(self.sections, 6000) if cross else "{}",
            domain_variant=DOMAIN_VARIANTS.get(self.run.domain_persona, ""),
            repair_notes=repair_notes or "none",
            mode=self.run.mode,
        )
        return prompt, evidence, coverage

    async def _synthesize(self, section: str, repair_notes: str = "", cross: bool = False) -> Dict[str, Any]:
        prompt, _evidence, coverage = self._section_spec(section, repair_notes, cross)
        result = await self.llm.generate_json(
            load_prompt("shared"), prompt, role="synthesis", max_output_tokens=4096,
            timeout_seconds=settings.DOSSIER_V2_SECTION_TIMEOUT_SECONDS,
        )
        payload = result.parsed
        if not isinstance(payload, dict):
            raise PipelineError(f"{section}: model did not return a JSON object")
        payload = validate_section_payload(payload, section, set(self.evidence_by_ref))
        self._verify_citations(payload, section)
        payload["coverage"] = coverage
        payload["generated_by"] = {
            "prompt": prompt_version(section),
            "model": result.model,
            "attempt_tokens": result.output_tokens,
        }
        return payload

    async def _synthesize_batch(self, keys: Sequence[str], cross: bool) -> Dict[str, Dict[str, Any]]:
        """Write several sections in one provider call to respect free-tier limits."""
        entries: List[Dict[str, Any]] = []
        for key in keys:
            spec, evidence, coverage = self._section_spec(key, "", cross)
            compact = [
                {**item, "passage": str(item.get("passage") or "")[:450]}
                for item in evidence
            ]
            entries.append({
                "section": key,
                "instructions": spec,
                "evidence": compact,
                "coverage": coverage,
            })
        prompt = load_prompt(
            "synthesis_batch",
            sections=_json(entries, 24000),
            project_dna=_json(self.dna, 2500),
            student_profile=_json(self.profile, 1200),
            prior_sections=_json(self.sections, 6000) if cross else "{}",
            domain_variant=DOMAIN_VARIANTS.get(self.run.domain_persona, ""),
            mode=self.run.mode,
        )
        result = await self.llm.generate_json(
            load_prompt("shared"), prompt, role="synthesis", max_output_tokens=6144,
            timeout_seconds=settings.DOSSIER_V2_SECTION_TIMEOUT_SECONDS,
        )
        parsed = result.parsed
        if not isinstance(parsed, dict):
            raise PipelineError("Batch synthesis did not return a JSON object")
        raw_sections = parsed.get("sections")
        if not isinstance(raw_sections, dict):
            raw_sections = parsed
        known_refs = set(self.evidence_by_ref)
        produced: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            key = entry["section"]
            candidate = raw_sections.get(key)
            if not isinstance(candidate, dict):
                continue
            try:
                payload = validate_section_payload(candidate, key, known_refs)
            except ValueError as exc:
                logger.warning("Batch returned invalid %s section: %s", key, exc)
                continue
            self._verify_citations(payload, key)
            payload["coverage"] = entry["coverage"]
            payload["generated_by"] = {
                "prompt": prompt_version(key),
                "model": result.model,
                "attempt_tokens": result.output_tokens,
            }
            produced[key] = payload
        if not produced:
            raise PipelineError("Batch synthesis returned no usable sections")
        return produced

    def _verify_citations(self, payload: Dict[str, Any], section: str) -> None:
        """Drop grounded items whose cited passage does not support the claim."""
        kept = []
        removed = 0
        for item in payload.get("items", []):
            if item.get("label") != "grounded" or not item.get("evidence"):
                kept.append(item)
                continue
            supported = False
            for ref in item["evidence"]:
                passage = str(self.evidence_by_ref.get(ref, {}).get("passage") or "")
                if check_evidence_support(item["text"], passage):
                    supported = True
                    break
            if supported:
                kept.append(item)
            else:
                removed += 1
        if removed:
            payload["items"] = kept
            limitations = payload.setdefault("limitations", [])
            limitations.append(f"Citation verifier removed {removed} claim(s) not supported by their cited passage.")
            payload["confidence"] = "low"

    async def _critic(self, section: str, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        evidence = self._evidence_for(section)
        prompt = load_prompt(
            "critic",
            section_key=section,
            section_json=_json(payload),
            evidence=_json(evidence, 6000),
            student_profile=_json(self.profile, 1200),
            project_dna=_json(self.dna, 3000),
        )
        try:
            result = await self.llm.generate_json(
                load_prompt("shared"), prompt, role="critic", max_output_tokens=4096,
                timeout_seconds=settings.DOSSIER_V2_LLM_TIMEOUT_SECONDS,
            )
        except (LLMCallError, LLMNotConfigured) as exc:
            logger.warning("Critic unavailable for %s: %s", section, exc)
            return None
        parsed = result.parsed if isinstance(result.parsed, dict) else {}
        failures = parsed.get("failures") if isinstance(parsed, dict) else None
        if parsed.get("passed") is True and not failures:
            return None
        return parsed if isinstance(parsed, dict) else {"passed": False, "failures": [{"check": "Complete", "reason": "Unparseable critic result"}]}

    async def _specificity_test(self, section: str, payload: Dict[str, Any]) -> Optional[bool]:
        """Return True/False, or None when the audit model was unavailable."""
        prompt = "\n".join([
            "You are auditing a dossier section for generic filler. Answer STRICT JSON only: "
            '{"swap_test_passed": true|false, "reason": "short"}. '
            "The test passes only if replacing this project's name, users, method and student profile with a "
            "different project in the same domain would make the text false or incoherent.",
            f"SECTION KEY: {section}",
            f"PROJECT DNA: {_json(self.dna, 4000)}",
            f"SECTION: {_json(payload, 3000)}",
        ])
        try:
            result = await self.llm.generate_json(
                load_prompt("shared"), prompt, role="extraction", max_output_tokens=512,
                timeout_seconds=settings.DOSSIER_V2_LLM_TIMEOUT_SECONDS,
            )
            parsed = result.parsed if isinstance(result.parsed, dict) else {}
            if "swap_test_passed" not in parsed:
                return None
            return bool(parsed.get("swap_test_passed"))
        except (LLMCallError, LLMNotConfigured) as exc:
            logger.warning("Specificity audit unavailable for %s: %s", section, exc)
            return None

    async def _persist_section(
        self, db: AsyncSession, section: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        coverage = payload.get("coverage") or self._coverage_for(self._evidence_for(section))
        confidence = self._finalize_coverage(payload, coverage, section not in self.failed_sections)
        row = (await db.execute(
            select(DossierSection).where(DossierSection.run_id == self.run_id, DossierSection.section == section)
        )).scalars().first()
        if row is None:
            row = DossierSection(run_id=self.run_id, section=section)
            db.add(row)
        row.content = payload
        row.confidence = confidence
        row.coverage = coverage
        await db.commit()
        self.sections[section] = payload
        await self.emit("section", {
            "section": section, "content": payload,
            "confidence": confidence, "coverage": coverage,
        })
        await self._progress("synthesis", f"Wrote {section.replace('_', ' ')}")
        return payload

    async def _write_section(self, db: AsyncSession, section: str, cross: bool = False) -> Dict[str, Any]:
        """Synthesise one section. Audits happen in one batch after writing."""
        try:
            payload = await self._synthesize(section, "", cross)
        except (LLMCallError, ValueError, PipelineError) as exc:
            if section not in self.failed_sections:
                self.failed_sections.append(section)
            payload = {
                "section": section,
                "summary": f"Generation failed: {str(exc)[:220]}",
                "confidence": "low",
                "coverage": self._coverage_for(self._evidence_for(section)),
                "items": [],
                "tables": [],
                "limitations": [
                    "This section could not be generated from evidence. No template text was substituted.",
                    str(exc)[:300],
                ],
                "generated_by": {"prompt": prompt_version(section), "model": "none"},
            }
            db.add(SectionReview(run_id=self.run_id, section=section, attempt=1,
                                 passed=False, failures=[{"check": "Complete", "reason": str(exc)[:300]}]))
            await db.commit()
        return await self._persist_section(db, section, payload)

    async def _write_sections_batch(
        self, db: AsyncSession, keys: Sequence[str], cross: bool = False
    ) -> None:
        """Write at most BATCH_SIZE sections per model call, then fall back individually."""
        size = max(1, settings.DOSSIER_V2_SECTION_BATCH_SIZE)
        for start in range(0, len(keys), size):
            chunk = list(keys[start:start + size])
            try:
                produced = await self._synthesize_batch(chunk, cross)
            except (LLMCallError, ValueError, PipelineError) as exc:
                logger.warning("Batch synthesis failed for %s: %s", ",".join(chunk), exc)
                produced = {}
            for key in chunk:
                payload = produced.get(key)
                if payload is None:
                    await self._write_section(db, key, cross)
                else:
                    await self._persist_section(db, key, payload)

    async def _audit_batch(self, keys: Sequence[str], attempt: int) -> Dict[str, List[Dict[str, Any]]]:
        """Run one critic + swap-test call for all sections in `keys`."""
        compact = []
        for key in keys:
            section = self.sections.get(key) or {}
            items = section.get("items") or []
            compact.append({
                "section": key,
                "summary": str(section.get("summary") or "")[:600],
                "items": [{
                    "id": item.get("id"), "label": item.get("label"),
                    "text": str(item.get("text") or "")[:300],
                    "evidence": item.get("evidence") or [],
                } for item in items[:4]],
                "evidence_ids": sorted({
                    str(ref) for item in items for ref in (item.get("evidence") or [])
                }),
                "limitations": (section.get("limitations") or [])[:3],
            })
        prompt = load_prompt(
            "audit_batch",
            sections=_json(compact, 12000),
            project_dna=_json(self.dna, 2000),
            student_profile=_json(self.profile, 1000),
        )
        try:
            result = await self.llm.generate_json(
                load_prompt("shared"), prompt, role="critic", max_output_tokens=4096,
                timeout_seconds=settings.DOSSIER_V2_LLM_TIMEOUT_SECONDS,
            )
        except (LLMCallError, LLMNotConfigured) as exc:
            logger.warning("Batched audit unavailable: %s", exc)
            for key in keys:
                note = "Critic and specificity audit unavailable; swap test could not be run."
                self.sections[key].setdefault("limitations", []).append(note)
            return {}

        parsed = result.parsed if isinstance(result.parsed, dict) else {}
        audits = parsed.get("audits") if isinstance(parsed, dict) else None
        failures_by_section: Dict[str, List[Dict[str, Any]]] = {}
        for entry in audits if isinstance(audits, list) else []:
            if not isinstance(entry, dict):
                continue
            key = str(entry.get("section") or "")
            if key not in keys:
                continue
            raw = entry.get("failures") or []
            failures = [
                {
                    "check": str((f or {}).get("check") or "Complete"),
                    "reason": str((f or {}).get("reason") or "")[:400],
                    "fix": str((f or {}).get("fix") or "")[:400],
                }
                for f in raw if isinstance(f, dict)
            ]
            if entry.get("passed") is True:
                failures = []
            failures_by_section[key] = failures
        for key in keys:
            failures = failures_by_section.get(key, [])
            db_failures = failures or None
            async with self.session_factory() as audit_db:
                audit_db.add(SectionReview(run_id=self.run_id, section=key, attempt=attempt,
                                           passed=not failures, failures=db_failures))
                await audit_db.commit()
        return {key: value for key, value in failures_by_section.items() if value}

    async def _audit_and_repair(self, db: AsyncSession) -> None:
        keys = [key for key in SECTION_KEYS if key in self.sections and key not in self.failed_sections]
        if not keys:
            return
        await self._progress("audit", "Reviewing sections for grounding and specificity")
        failures = await self._audit_batch(keys, attempt=1)
        for key, items in failures.items():
            self.failed_critic.append(key)
            self.sections[key].setdefault("limitations", []).append(
                "Critic flagged: " + "; ".join(str(f.get("check")) for f in items[:4])
            )
            self.sections[key]["confidence"] = "low"
        elapsed = time.perf_counter() - self.started
        if (
            settings.DOSSIER_V2_MAX_REPAIRS < 1 or not failures
            or elapsed > settings.DOSSIER_V2_RUN_TIMEOUT_SECONDS * 0.7
        ):
            return

        repaired: List[str] = []
        for key in failures:
            notes = _json(failures[key], 3000)
            try:
                payload = await self._synthesize(
                    key, f"Fix these critic failures: {notes}", cross=key in CROSS_SECTIONS
                )
            except (LLMCallError, ValueError, PipelineError) as exc:
                logger.warning("Repair failed for %s: %s", key, exc)
                continue
            self.sections[key] = payload
            row = (await db.execute(
                select(DossierSection).where(DossierSection.run_id == self.run_id, DossierSection.section == key)
            )).scalars().first()
            if row is not None:
                row.content = payload
                row.confidence = payload.get("confidence") or "low"
                row.coverage = payload.get("coverage") or "thin"
            repaired.append(key)
        if repaired:
            await db.commit()
            remaining = await self._audit_batch(repaired, attempt=2)
            for key in repaired:
                if key in remaining:
                    self.sections[key].setdefault("limitations", []).append(
                        "Critic still failed after repair: "
                        + "; ".join(str(f.get("check")) for f in remaining[key][:4])
                    )

    @staticmethod
    def _status_for(failed_sections: Sequence[str], failed_critic: Sequence[str]) -> str:
        """A run is only 'succeeded' when every section was really generated."""
        if failed_sections:
            return "partial" if len(failed_sections) < len(SECTION_KEYS) else "failed"
        if failed_critic:
            return "partial"
        return "succeeded"

    # ---------------------------------------------------------------- stage 8
    async def _assemble(self, db: AsyncSession) -> None:
        snapshot = {
            "sections": self.sections,
            "dna": self.dna,
            "coverage": self.coverage,
            "plan": self.run.plan,
            "cost_usd": self.cost_usd,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        version = (await db.execute(
            select(DossierVersion.version).where(DossierVersion.run_id == self.run_id)
        )).scalars().all()
        db.add(DossierVersion(run_id=self.run_id, version=max(version or [0]) + 1, snapshot=snapshot))

        if not self.run.project_id:
            try:
                tech_section = self.sections.get("tech_stack", {})
                recommendations = []
                for table in tech_section.get("tables", []):
                    columns = [str(c).lower() for c in table.get("columns", [])]
                    if "recommendation" in columns:
                        idx = columns.index("recommendation")
                        recommendations.extend(str(row[idx]) for row in table.get("rows", []) if len(row) > idx)
                embedding = await self.llm.embed(f"{self.dna.get('title')} {self.dna.get('problem')}")
                project = ProjectDossier(
                    user_id=self.run.user_id,
                    guest_session_id=self.run.guest_session_id,
                    slug=IngestionAgent.generate_slug(str(self.dna.get("title") or "Dossier v2")),
                    title=str(self.dna.get("title") or "Dossier v2")[:200],
                    tagline=(self.sections.get("executive_brief", {}).get("summary") or "")[:300] or "Research-grade Dossier v2",
                    domain_persona=self.run.domain_persona,
                    stage=str(self.dna.get("stage") or "Idea")[:40],
                    problem_statement=str(self.dna.get("problem") or "")[:8000],
                    solution_breakdown={"architecture": self.sections.get("solution_design", {}).get("summary", "")},
                    tech_stack=recommendations[:8],
                    key_metrics=[],
                    whitespace_analysis=self.sections.get("novelty_assessment", {}),
                    trend_radar_cache=self.sections.get("market_landscape", {}),
                    benchmark_analysis=self.sections.get("related_work", {}),
                    missing_roles=[],
                    external_links=self._project_links(),
                    embedding=embedding,
                )
                db.add(project)
                await db.flush()
                self.run.project_id = project.id
            except Exception as exc:
                logger.warning("Could not create public dossier for run %s: %s", self.run_id, exc)

        self.run.status = self._status_for(self.failed_sections, self.failed_critic)
        self.run.cost_usd = round(self.cost_usd, 4)
        self.run.duration_ms = round((time.perf_counter() - self.started) * 1000)
        self.run.finished_at = datetime.now(timezone.utc)
        await db.commit()
        await self.emit("complete", {
            "status": self.run.status,
            "sections": list(self.sections),
            "cost_usd": self.run.cost_usd,
            "duration_ms": self.run.duration_ms,
        })

    def _project_links(self) -> Dict[str, str]:
        links: Dict[str, str] = {}
        url = str(self.dna.get("url") or "")
        if "github.com" in url:
            links["github"] = url
        if url.endswith(".pdf"):
            links["paper"] = url
        return links

    # ------------------------------------------------------------------- main
    async def execute(self) -> None:
        if not settings.llm_configured:
            await self._fail("AI provider not configured: set GEMINI_API_KEY or GROQ_API_KEY. Template generation is disabled.", code="AI_PROVIDER_NOT_CONFIGURED")
            return
        async with self.session_factory() as db:
            try:
                self.run = await db.get(DossierRun, self.run_id)
                if not self.run:
                    return
                self.run.status = "running"
                self.run.error = None
                self.profile = dict(self.run.profile or {})
                await db.commit()
                self.llm = DossierLLM(on_call=self._record_call, on_error=self._record_error)

                # A hard deadline keeps a provider outage from leaving a run
                # stuck in "running" forever. Partial work stays in the DB and
                # the terminal status is still honest.
                async with asyncio.timeout(settings.DOSSIER_V2_RUN_TIMEOUT_SECONDS):
                    await self._stage_ingest(db)
                    await self._stage_plan()
                    await self._stage_retrieve(db)
                    await self._stage_curate(db)

                    await self._write_sections_batch(db, FIRST_PASS_SECTIONS, cross=False)
                    cross_keys = [key for key in SECTION_KEYS if key in CROSS_SECTIONS]
                    await self._write_sections_batch(db, cross_keys, cross=True)

                    await self._audit_and_repair(db)
                    await self._assemble(db)
            except TimeoutError:
                await self._fail(
                    f"Run exceeded the {settings.DOSSIER_V2_RUN_TIMEOUT_SECONDS:.0f}s deadline; "
                    "partial sections were kept and no template text was substituted."
                )
            except (LLMNotConfigured, LLMCallError, PipelineError) as exc:
                await self._fail(str(exc))
            except Exception as exc:
                logger.exception("Dossier v2 pipeline failed")
                await self._fail(f"Unexpected pipeline failure: {exc}")
            finally:
                if self.llm:
                    await self.llm.aclose()

    async def _fail(self, message: str, code: str = "PIPELINE_FAILED") -> None:
        async with self.session_factory() as db:
            run = await db.get(DossierRun, self.run_id)
            if run:
                run.status = "failed"
                run.error = json.dumps({"code": code, "message": message})
                run.finished_at = datetime.now(timezone.utc)
                run.cost_usd = round(self.cost_usd, 4)
                run.duration_ms = round((time.perf_counter() - self.started) * 1000)
                await db.commit()
        await self.emit("error", {"code": code, "message": message})

    # --------------------------------------------------------------- deepen
    async def deepen(self, section: str) -> None:
        async with self.session_factory() as db:
            self.run = await db.get(DossierRun, self.run_id)
            if not self.run:
                return
            self.llm = DossierLLM(on_call=self._record_call, on_error=self._record_error)
            self.dna = dict(self.run.project_dna or {})
            self.profile = dict(self.run.profile or {})
            self.sections = {
                row.section: row.content
                for row in (await db.execute(
                    select(DossierSection).where(DossierSection.run_id == self.run_id)
                )).scalars()
            }
            # Restore curated evidence from storage.
            rows = (await db.execute(select(Evidence).where(Evidence.run_id == self.run_id))).scalars().all()
            for row in rows:
                self.evidence_rows[row.ref] = row
                self.evidence_by_ref[row.ref] = {
                    "ref": row.ref, "title": row.title, "url": row.url, "source": row.source,
                    "source_quality": row.source_quality, "passage": row.passage,
                    "relevance": int(row.relevance or 0), "question_id": row.question_id,
                    "id": str(row.id),
                }
                self.curated.setdefault(str(row.question_id), []).append(self.evidence_by_ref[row.ref])
            plan = dict(self.run.plan or {})
            self.questions = list(plan.get("questions") or [])

            await self._progress("deepen", f"Running a deeper research pass for {section}")
            prompt = "\n".join([
                load_prompt(
                    "planner",
                    project_dna=_json(self.dna, 2500),
                    student_profile=_json(self.profile, 1200),
                    mode="deep",
                    domain_variant=DOMAIN_VARIANTS.get(self.run.domain_persona, ""),
                ),
                f"\nDEEPEN SECTION ONLY: {section}",
                "\nReturn 3-5 additional research questions focused on this section only.",
            ])
            try:
                result = await self.llm.generate_json(
                    load_prompt("shared"), prompt, role="planning", max_output_tokens=4096,
                    timeout_seconds=settings.DOSSIER_V2_LLM_TIMEOUT_SECONDS,
                )
                extra = result.parsed.get("questions") if isinstance(result.parsed, dict) else []
            except (LLMCallError, LLMNotConfigured) as exc:
                await self.emit("error", {"code": "DEEPEN_FAILED", "message": str(exc)})
                return
            start = len(self.questions)
            for index, item in enumerate(extra or [], start=1):
                if not isinstance(item, dict):
                    continue
                queries = [str(q) for q in (item.get("queries") or []) if str(q).strip()][:4]
                source_types = [str(s) for s in (item.get("source_types") or []) if s in {
                    "local_corpus", "github", "papers", "web", "opportunities", "datasets"
                }]
                if not queries or not source_types:
                    continue
                self.questions.append({
                    "id": f"D{start + index}",
                    "question": str(item.get("question") or queries[0])[:500],
                    "sections": [section],
                    "queries": queries,
                    "source_types": source_types,
                })
            plan["questions"] = self.questions
            self.run.plan = plan
            await db.commit()

            import httpx

            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                retriever = DossierRetriever(db, client)
                for question in self.questions[-5:]:
                    items = await retriever.retrieve_question(
                        question=question, dna=self.dna,
                        domain_persona=self.run.domain_persona, mode="deep",
                    )
                    await self._store_evidence(db, items, str(question["id"]))
            await self._stage_curate(db)
            await self._write_section(db, section, cross=section in CROSS_SECTIONS)
            await self._audit_and_repair(db)
            versions = (await db.execute(
                select(DossierVersion.version).where(DossierVersion.run_id == self.run_id)
            )).scalars().all()
            db.add(DossierVersion(
                run_id=self.run_id,
                version=max(versions or [0]) + 1,
                snapshot={
                    "sections": self.sections,
                    "dna": self.dna,
                    "coverage": self.coverage,
                    "plan": self.run.plan,
                    "cost_usd": float(self.run.cost_usd or 0) + self.cost_usd,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "trigger": f"deepen:{section}",
                },
            ))
            self.run.cost_usd = round(float(self.run.cost_usd or 0) + self.cost_usd, 4)
            await db.commit()
            await self.emit("complete", {"status": "deepened", "section": section})
            await self.llm.aclose()

    # ------------------------------------------------------------------ chat
    async def chat(self, question: str) -> Dict[str, Any]:
        if not settings.llm_configured:
            return {"answer": "AI provider not configured.", "evidence": [], "abstained": True}
        async with self.session_factory() as db:
            self.run = await db.get(DossierRun, self.run_id)
            if not self.run:
                return {"answer": "Run not found.", "evidence": [], "abstained": True}
            self.dna = dict(self.run.project_dna or {})
            self.profile = dict(self.run.profile or {})
            sections = {
                row.section: row.content
                for row in (await db.execute(select(DossierSection).where(DossierSection.run_id == self.run_id))).scalars()
            }
            rows = (await db.execute(select(Evidence).where(Evidence.run_id == self.run_id))).scalars().all()
            evidence = [
                {"ref": row.ref, "title": row.title, "url": row.url, "source": row.source,
                 "source_quality": row.source_quality, "passage": row.passage[:1200], "relevance": row.relevance}
                for row in rows if int(row.relevance or 0) >= 2
            ][:30]
            prompt = "\n".join([
                "Answer ONLY from the supplied dossier sections and evidence. STRICT JSON: "
                '{"answer":"string","evidence":["E1"],"abstained":false}. '
                "If the answer is not present, set abstained=true and answer 'I don't know from this dossier.' "
                "Never add facts, links or numbers not in the supplied evidence.",
                f"QUESTION: {question}",
                f"DOSSIER SECTIONS: {_json(sections, 8000)}",
                f"EVIDENCE: {_json(evidence, 8000)}",
            ])
            self.llm = DossierLLM(on_call=self._record_call, on_error=self._record_error)
            try:
                result = await self.llm.generate_json(
                    load_prompt("shared"), prompt, role="extraction", max_output_tokens=1024,
                    timeout_seconds=settings.DOSSIER_V2_LLM_TIMEOUT_SECONDS,
                )
            except (LLMCallError, LLMNotConfigured) as exc:
                return {"answer": f"AI unavailable: {exc}", "evidence": [], "abstained": True}
            parsed = result.parsed if isinstance(result.parsed, dict) else {}
            refs = [str(ref) for ref in (parsed.get("evidence") or []) if str(ref) in {row.ref for row in rows}]
            abstained = bool(parsed.get("abstained")) or not refs
            await self.llm.aclose()
            return {
                "answer": str(parsed.get("answer") or "I don't know from this dossier.")[:3000],
                "evidence": refs,
                "abstained": abstained,
            }


def export_markdown(sections: Dict[str, Dict[str, Any]]) -> str:
    lines = ["# LaunchPad Dossier v2", ""]
    for key in SECTION_KEYS:
        section = sections.get(key)
        if not section:
            continue
        lines.extend([f"## {key.replace('_', ' ').title()}", "", str(section.get("summary") or ""), ""])
        for item in section.get("items", []):
            refs = ", ".join(item.get("evidence") or [])
            lines.append(f"- **{item.get('label', '').upper()}** {item.get('text')} [{refs}]")
        for table in section.get("tables", []):
            lines.extend(["", f"### {table.get('title', 'Table')}", ""])
            columns = table.get("columns") or []
            lines.append("| " + " | ".join(str(c) for c in columns) + " |")
            lines.append("| " + " | ".join("---" for _ in columns) + " |")
            for row in table.get("rows", []):
                lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |")
        if section.get("limitations"):
            lines.extend(["", "**Limitations:** " + "; ".join(section["limitations"])])
        lines.append("")
    return "\n".join(lines)
