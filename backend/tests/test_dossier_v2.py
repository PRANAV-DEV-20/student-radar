"""Automated QA gates for the research-grade Dossier v2 pipeline.

These tests use no network calls and no real credentials (see conftest.py).
"""
import asyncio
import uuid

import pytest

from app.core.config import settings
from app.schemas.dossier_v2 import (
    SECTION_KEYS,
    check_evidence_support,
    validate_section_payload,
)
from app.models.dossier_v2 import Evidence
from app.services.dossier_v2_pipeline import DossierPipeline
from app.services.dossier_v2_prompts import load_prompt
from app.services.dossier_v2_retrieval import RetrievedItem
from app.services.llm_client import DossierLLM, LLMNotConfigured, LLMResult, _normalize_usage


def _section(**overrides):
    payload = {
        "section": "related_work",
        "summary": "A specific comparison.",
        "confidence": "high",
        "coverage": "thin",
        "items": [],
        "tables": [],
        "limitations": [],
        "generated_by": {"prompt": "related_work@v1", "model": "fake"},
    }
    payload.update(overrides)
    return payload


def test_all_18_sections_are_declared():
    assert len(SECTION_KEYS) == 18
    assert len(set(SECTION_KEYS)) == 18


def test_fabricated_grounded_claim_without_evidence_is_rejected():
    payload = _section(items=[{
        "id": "W1", "label": "grounded",
        "text": "This project raised $4M in 2024.", "evidence": [],
    }])
    with pytest.raises(ValueError, match="without evidence"):
        validate_section_payload(payload, "related_work", {"E1"})


def test_unresolved_evidence_ids_are_rejected():
    payload = _section(items=[{
        "id": "W1", "label": "grounded",
        "text": "A cited claim.", "evidence": ["E9"],
    }])
    with pytest.raises(ValueError, match="Unresolved evidence id"):
        validate_section_payload(payload, "related_work", {"E1"})


def test_inference_without_reasoning_is_rejected():
    payload = _section(items=[{
        "id": "W1", "label": "inference", "text": "Nobody has done this.", "evidence": [],
    }])
    with pytest.raises(ValueError, match="without reasoning"):
        validate_section_payload(payload, "related_work", {"E1"})


def test_recommendation_without_effort_is_rejected():
    payload = _section(items=[{
        "id": "W1", "label": "recommendation", "text": "Do the thing.", "evidence": [],
    }])
    with pytest.raises(ValueError, match="without effort"):
        validate_section_payload(payload, "related_work", {"E1"})


def test_related_work_requires_real_linked_project():
    payload = _section(tables=[{
        "title": "Prior art",
        "columns": ["name", "url", "evidence_id"],
        "rows": [["Imagined Project", "not-a-url", "E1"]],
    }])
    with pytest.raises(ValueError, match="without a retrieved URL"):
        validate_section_payload(payload, "related_work", {"E1"})


def test_related_work_accepts_a_real_retrieved_link():
    payload = _section(tables=[{
        "title": "Prior art",
        "columns": ["name", "url", "evidence_id"],
        "rows": [["PlantVillage", "https://github.com/plantvillage/plantvillage", "E1"]],
    }])
    result = validate_section_payload(payload, "related_work", {"E1"})
    assert result["tables"][0]["rows"][0][1].startswith("https://")


def test_citation_verifier_rejects_unsupported_numeric_claim():
    assert check_evidence_support(
        "The system reaches 98.7% accuracy on field data.",
        "The repository README describes a web framework for Python.",
    ) is False


def test_citation_verifier_accepts_supported_claim():
    assert check_evidence_support(
        "FastAPI is a Python web framework.",
        "FastAPI is a modern, fast web framework for building APIs with Python.",
    ) is True


def test_thin_and_missing_coverage_produce_honest_limits():
    payload = _section(confidence="high", coverage="thin", limitations=[])
    confidence = DossierPipeline._finalize_coverage(payload, "thin", passed_review=True)
    assert confidence == "medium"
    assert payload["coverage"] == "thin"

    none_payload = _section(confidence="high", limitations=[])
    confidence = DossierPipeline._finalize_coverage(none_payload, "none", passed_review=True)
    assert confidence == "low"
    assert any("No retrieved evidence" in item for item in none_payload["limitations"])


def test_missing_provider_state_never_generates_template_text(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)

    async def run():
        llm = DossierLLM()
        try:
            with pytest.raises(LLMNotConfigured, match="AI provider not configured"):
                await llm.generate_json("rules", "prompt that must not be answered")
        finally:
            await llm.aclose()

    asyncio.run(run())


def test_rate_limited_models_are_skipped_until_cooldown(monkeypatch):
    from app.services import llm_client as client_module

    clock = [100.0]
    monkeypatch.setattr(client_module, "_MODEL_COOLDOWN", lambda: clock[0])
    monkeypatch.setattr(client_module, "_cooldown_until", {})
    llm = DossierLLM()

    chain = llm._chain("synthesis")
    assert "gemini-3.5-flash-lite" in chain
    llm._cool_down("gemini-3.5-flash-lite", 429)
    assert "gemini-3.5-flash-lite" not in llm._chain("synthesis")

    clock[0] += client_module._QUOTA_COOLDOWN_SECONDS + 1
    assert "gemini-3.5-flash-lite" in llm._chain("synthesis")


def test_specificity_swap_test_failure_is_detected():
    async def emit(*args, **kwargs):
        return None

    pipeline = DossierPipeline(uuid.uuid4(), emit)
    pipeline.dna = {"title": "Leaf Disease Detector", "problem": "Farmers in India"}
    pipeline.sections = {}

    class FakeLLM:
        async def generate_json(self, *args, **kwargs):
            return LLMResult(
                text='{"swap_test_passed": false, "reason": "generic"}',
                parsed={"swap_test_passed": False, "reason": "generic"},
                model="fake", latency_ms=1,
            )

    pipeline.llm = FakeLLM()
    payload = _section(summary="Build a useful app.")
    assert asyncio.run(pipeline._specificity_test("gaps", payload)) is False


def test_planner_prompt_carries_student_profile_into_research_plan():
    prompt = load_prompt(
        "planner",
        project_dna='{"title": "Offline crop diagnosis"}',
        student_profile='{"skills": ["Python"], "weekly_hours": 8, "budget_usd": 120, "country": "India"}',
        domain_variant="Biotech overlay",
        mode="quick",
    )
    assert "Offline crop diagnosis" in prompt
    assert "weekly_hours" in prompt
    assert "India" in prompt
    assert "Biotech overlay" in prompt


def test_provider_usage_fields_are_normalized_for_ai_runs():
    gemini = _normalize_usage({
        "promptTokenCount": 1200,
        "candidatesTokenCount": 340,
        "totalTokenCount": 1540,
    })
    assert gemini["prompt_token_count"] == 1200
    assert gemini["output_token_count"] == 340
    assert gemini["total_token_count"] == 1540

    groq = _normalize_usage({
        "prompt_tokens": 105,
        "completion_tokens": 55,
        "total_tokens": 160,
    })
    assert groq["prompt_token_count"] == 105
    assert groq["output_token_count"] == 55


def test_store_evidence_persists_evidence_rows_not_only_sources():
    class FakeResult:
        def scalars(self):
            return self

        def all(self):
            return []

        def __iter__(self):
            return iter([])

    class FakeDB:
        def __init__(self):
            self.added = []

        async def execute(self, *args, **kwargs):
            return FakeResult()

        def add(self, row):
            self.added.append(row)

        async def commit(self):
            return None

    async def emit(*args, **kwargs):
        return None

    db = FakeDB()
    pipeline = DossierPipeline(uuid.uuid4(), emit)
    item = RetrievedItem(
        url="https://github.com/fastapi/fastapi",
        title="FastAPI",
        source="github",
        source_quality="official",
        passage="FastAPI is a Python web framework.",
        question_id="Q1",
    )
    asyncio.run(pipeline._store_evidence(db, [item]))

    evidence_rows = [row for row in db.added if isinstance(row, Evidence)]
    assert len(evidence_rows) == 1
    assert evidence_rows[0].ref == "E1"
    assert pipeline.evidence_by_ref["E1"]["url"] == item.url


def test_run_status_is_honest_when_generation_failed():
    assert DossierPipeline._status_for([], []) == "succeeded"
    assert DossierPipeline._status_for([], ["gaps"]) == "partial"
    assert DossierPipeline._status_for(["gaps"], []) == "partial"
    assert DossierPipeline._status_for(list(SECTION_KEYS), []) == "failed"


def test_batched_synthesis_prompt_exists():
    prompt = load_prompt(
        "synthesis_batch",
        sections='[{"section":"gaps","instructions":"x","evidence":[],"coverage":"none"}]',
        project_dna="{}",
        student_profile="{}",
        prior_sections="{}",
        domain_variant="",
        mode="quick",
    )
    assert '"sections"' in prompt
    assert "one key per requested" in prompt


def test_batched_audit_prompt_exists():
    prompt = load_prompt(
        "audit_batch",
        sections='[{"section":"gaps","summary":"s","items":[],"evidence_ids":[],"limitations":[]}]',
        project_dna="{}",
        student_profile="{}",
    )
    assert "swap" in prompt.lower() or "Specific" in prompt
    assert '"audits"' in prompt


def test_batched_relevance_prompt_exists():
    prompt = load_prompt(
        "relevance_batch",
        questions='[{"id": "Q1", "question": "q", "passages": []}]',
        mode="quick",
    )
    assert "question_id" in prompt
    assert "Q1" in prompt


def test_all_cross_section_prompt_files_exist():
    from app.schemas.dossier_v2 import CROSS_SECTIONS
    from app.services.dossier_v2_prompts import PROMPT_DIR

    for section in CROSS_SECTIONS:
        assert (PROMPT_DIR / f"cross_{section}.md").exists()
