"""Two-tier ecosystem benchmark: grounded collection, synthesis, and persistence."""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import app.api.v1.dossiers as dossiers_module
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.dossier import ProjectDossier
from app.schemas.dossier import DossierResponse, EcosystemBenchmark
from app.services.benchmark_scout import BenchmarkScout, benchmark_scout
from app.services.gemini_client import gemini_service
from app.services.ingestion_agent import ingestion_agent


PEER_RESULT = {
    "url": "https://github.com/student/openarm-esp32",
    "title": "OpenArm ESP32",
    "content": "A 3-DOF arm controlled with MediaPipe and a serial bridge.",
}
ADVANCED_RESULT = {
    "url": "https://arxiv.org/abs/2401.01234",
    "title": "Vision-Language-Action Teleoperation",
    "content": "Production VLA stack for robotic manipulation.",
}


def _make_dossier() -> ProjectDossier:
    now = datetime.now(timezone.utc)
    return ProjectDossier(
        id=uuid4(),
        slug="robotic-arm-abc123",
        title="4-DOF Robotic Arm v2",
        tagline="Low-latency gesture-controlled arm",
        domain_persona="tech_builder",
        stage="Prototype",
        problem_statement="Student arms jitter under fixed gesture rules.",
        solution_breakdown={"architecture": "PCA9685 PWM driver."},
        tech_stack=["Python", "MediaPipe"],
        key_metrics=[{"label": "Latency", "value": "45ms"}],
        whitespace_analysis={"market_gap": "No low-cost VLA stack.", "top_voices": []},
        trend_radar_cache={},
        missing_roles=[],
        external_links={},
        verified_status=False,
        boosted=False,
        created_at=now,
        updated_at=now,
    )


def test_exa_payloads_use_two_targeted_queries_and_highlights(monkeypatch):
    captured = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [PEER_RESULT if "open source student" in " ".join(
                str(value) for value in captured[-1]["json"].values()
            ) else ADVANCED_RESULT]}

    class FakeClient:
        async def post(self, url, **kwargs):
            captured.append({"url": url, "json": kwargs.get("json") or {}, "headers": kwargs.get("headers") or {}})
            return FakeResponse()

        async def aclose(self):
            return None

    monkeypatch.setattr(settings, "EXA_API_KEY", "exa-test")
    scout = BenchmarkScout(client=FakeClient())

    async def fake_synthesis(**kwargs):
        assert len(kwargs["similar_results"]) == 1
        assert len(kwargs["advanced_results"]) == 1
        return kwargs["fallback"]

    monkeypatch.setattr(gemini_service, "generate_structured_benchmark", fake_synthesis)

    result = asyncio.run(
        scout.build_benchmark(
            {
                "title": "4-DOF Robotic Arm v2",
                "tagline": "Low-latency gesture-controlled arm",
                "problem_statement": "Student arms jitter under fixed gesture rules.",
                "tech_stack": ["Python"],
            }
        )
    )

    assert len(captured) == 2
    peer_payload = captured[0]["json"]
    advanced_payload = captured[1]["json"]
    assert "open source student project OR indie prototype" in peer_payload["query"]
    assert "category" not in peer_payload
    assert "objective" in peer_payload and peer_payload["objective"].strip()
    assert peer_payload["numResults"] == 5
    assert peer_payload["contents"] == {"highlights": True}
    assert "production architecture OR research breakthrough scaling" in advanced_payload["query"]
    assert captured[0]["headers"]["x-api-key"] == "exa-test"

    assert result["similar_projects"][0]["name"] == "OpenArm ESP32"
    assert result["advanced_upgrades"][0]["reference_url"] == ADVANCED_RESULT["url"]
    assert result["similar_projects"][0]["student_differentiator"] == ""
    assert result["selected_upgrades"] == []


def test_clean_results_rejects_root_and_search_pages():
    cleaned = BenchmarkScout._clean_results(
        [
            PEER_RESULT,
            PEER_RESULT,
            {"url": "https://github.com/", "title": "GitHub root"},
            {"url": "https://example.com/search?q=arm", "title": "Search results"},
            {"url": "https://www.google.com", "title": "Google"},
            {"url": "", "title": "No URL"},
        ]
    )
    assert len(cleaned) == 1
    assert cleaned[0]["url"] == PEER_RESULT["url"]
    assert cleaned[0]["source"] == "github.com"


def test_normalization_rejects_hallucinated_urls_and_caps_lengths():
    fallback = {
        "similar_projects": [
            {
                "name": "Real peer",
                "source_platform": "github.com",
                "url": PEER_RESULT["url"],
                "what_they_built": "Real summary",
                "student_differentiator": "",
            }
        ],
        "advanced_upgrades": [],
        "selected_upgrades": [],
    }
    parsed = {
        "similar_projects": [
            {
                "name": "Invented project",
                "source_platform": "github.com",
                "url": "https://github.com/invented/repo",
                "what_they_built": "Fabricated",
                "student_differentiator": "Fabricated edge",
            },
            {
                "name": "Real peer",
                "source_platform": "github.com",
                "url": PEER_RESULT["url"],
                "what_they_built": "Grounded summary",
                "student_differentiator": "Grounded edge",
            },
        ],
        "advanced_upgrades": [
            {
                "upgrade_title": "VLA stack",
                "inspired_by": "arxiv.org",
                "reference_url": ADVANCED_RESULT["url"],
                "architectural_impact": "Grounded impact",
                "difficulty": "Unvalidated",
            }
        ],
    }

    normalized = gemini_service._normalize_benchmark(
        parsed,
        fallback,
        allowed_similar={PEER_RESULT["url"]},
        allowed_advanced={ADVANCED_RESULT["url"]},
    )

    assert len(normalized["similar_projects"]) == 1
    assert normalized["similar_projects"][0]["name"] == "Real peer"
    assert normalized["advanced_upgrades"][0]["difficulty"] == "2-Week Milestone"
    assert "invented" not in str(normalized)


def test_ingestion_attaches_benchmark_to_dossier_data(monkeypatch):
    sentinel = {
        "similar_projects": [],
        "advanced_upgrades": [],
        "selected_upgrades": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    async def fake_dossier(**kwargs):
        return {
            "title": "Water Filter",
            "tagline": "Low-cost filtration",
            "problem_statement": "Unsafe rural water",
            "solution_breakdown": {"architecture": "Gravity filter"},
            "tech_stack": ["Ceramics"],
            "key_metrics": [],
            "whitespace_analysis": {},
            "missing_roles": [],
        }

    async def fake_trend(**kwargs):
        return {}

    async def fake_embedding(text):
        return []

    async def fake_benchmark(context):
        assert context["title"] == "Water Filter"
        return sentinel

    monkeypatch.setattr(gemini_service, "generate_structured_dossier", fake_dossier)
    monkeypatch.setattr("app.services.ingestion_agent.trend_scout.scout_whitespace", fake_trend)
    monkeypatch.setattr(gemini_service, "generate_embedding", fake_embedding)
    monkeypatch.setattr(benchmark_scout, "build_benchmark", fake_benchmark)

    result = asyncio.run(ingestion_agent.process_artifact("idea", "Water filter", "tech_builder"))
    assert result["benchmark_analysis"] == sentinel
    assert result["slug"].startswith("water-filter-")


def test_benchmark_analysis_serializes_in_dossier_response():
    dossier = _make_dossier()
    dossier.benchmark_analysis = {
        "similar_projects": [
            {
                "name": "OpenArm ESP32",
                "source_platform": "github.com",
                "url": PEER_RESULT["url"],
                "what_they_built": "3-DOF arm",
                "student_differentiator": "PCA9685 driver",
            }
        ],
        "advanced_upgrades": [
            {
                "upgrade_title": "Add VLA teleoperation",
                "inspired_by": "arxiv.org",
                "reference_url": ADVANCED_RESULT["url"],
                "architectural_impact": "Natural language commands",
                "difficulty": "2-Week Milestone",
            }
        ],
        "selected_upgrades": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    response = DossierResponse.model_validate(dossier)
    assert response.benchmark_analysis is not None
    assert response.benchmark_analysis.similar_projects[0].name == "OpenArm ESP32"
    assert response.benchmark_analysis.advanced_upgrades[0].difficulty == "2-Week Milestone"


def test_benchmark_schema_rejects_non_http_links():
    try:
        EcosystemBenchmark(
            similar_projects=[
                {
                    "name": "Bad",
                    "source_platform": "github",
                    "url": "javascript:alert(1)",
                    "what_they_built": "",
                    "student_differentiator": "",
                }
            ]
        )
    except ValueError:
        return
    raise AssertionError("Non-http benchmark URLs must be rejected")


def test_refresh_and_roadmap_endpoints_persist_benchmark(monkeypatch):
    dossier = _make_dossier()
    calls = {"commits": 0, "refreshes": 0}

    class FakeResult:
        def scalars(self):
            return self

        def first(self):
            return dossier

    class FakeDB:
        async def execute(self, statement):
            return FakeResult()

        async def commit(self):
            calls["commits"] += 1

        async def refresh(self, obj):
            calls["refreshes"] += 1

    async def fake_db():
        yield FakeDB()

    benchmark_payload = {
        "similar_projects": [],
        "advanced_upgrades": [
            {
                "upgrade_title": "Digital twin simulation",
                "inspired_by": "arxiv.org",
                "reference_url": ADVANCED_RESULT["url"],
                "architectural_impact": "In-browser kinematics review",
                "difficulty": "Weekend Sprint",
            }
        ],
        "selected_upgrades": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    async def fake_build(context):
        assert context["title"] == dossier.title
        return benchmark_payload

    monkeypatch.setattr(benchmark_scout, "build_benchmark", fake_build)
    app.dependency_overrides[get_db] = fake_db
    try:
        client = TestClient(app)
        refreshed = client.post("/api/v1/dossiers/robotic-arm-abc123/benchmark/refresh")
        saved = client.post(
            "/api/v1/dossiers/robotic-arm-abc123/roadmap",
            json={"selected_upgrades": benchmark_payload["advanced_upgrades"]},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["benchmark_analysis"]["advanced_upgrades"][0]["upgrade_title"] == (
        "Digital twin simulation"
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["benchmark_analysis"]["selected_upgrades"][0]["reference_url"] == (
        ADVANCED_RESULT["url"]
    )
    assert calls["commits"] == 2
    assert calls["refreshes"] == 2


def test_pr_fallback_includes_selected_roadmap():
    result = gemini_service._fallback_pr_synthesis(
        {
            "title": "Robotic Arm",
            "tagline": "Low-latency control",
            "problem_statement": "Jitter",
            "tech_stack": ["Python"],
            "key_metrics": [],
            "benchmark_analysis": {
                "selected_upgrades": [
                    {
                        "upgrade_title": "Digital twin simulation",
                        "inspired_by": "arxiv.org",
                        "reference_url": ADVANCED_RESULT["url"],
                        "architectural_impact": "Test kinematics in-browser",
                        "difficulty": "Weekend Sprint",
                    }
                ]
            },
        },
        "high_octane",
    )
    assert "Building in Public — Version 2.0 Roadmap" in result["body_markdown"]
    assert "Digital twin simulation" in result["body_markdown"]
    assert ADVANCED_RESULT["url"] in result["body_markdown"]
