from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.auth import UserRegisterRequest
from app.schemas.credit import PeerReviewRequest
from app.schemas.dossier import DossierResponse
from app.schemas.pr import PRGenerateRequest
from app.schemas.radar import ReprofileRequest
from app.models.dossier import ProjectDossier
from app.services.dedup_service import dedup_service


# ----------------------------------------------------------------------
# Deduplication primitives
# ----------------------------------------------------------------------
def test_fingerprint_normalizes_scheme_www_and_case():
    a = dedup_service.compute_sha256_fingerprint("https://www.Example.com/event/", "Global AI Hack")
    b = dedup_service.compute_sha256_fingerprint("http://example.com/event", "  global ai hack ")
    assert a == b
    assert len(a) == 64


def test_cosine_similarity_and_semantic_duplicate_threshold():
    vector = [1.0, 0.0, 0.0]
    assert dedup_service.cosine_similarity(vector, vector) == pytest.approx(1.0)
    assert dedup_service.cosine_similarity(vector, [0.0, 1.0, 0.0]) == pytest.approx(0.0)
    assert dedup_service.cosine_similarity(vector, []) == 0.0

    match = dedup_service.is_semantic_duplicate(
        [0.99, 0.01, 0.0],
        [("opp-1", [1.0, 0.0, 0.0])],
        threshold=0.88,
    )
    assert match == "opp-1"


# ----------------------------------------------------------------------
# Request schemas / aliases
# ----------------------------------------------------------------------
def test_pr_request_accepts_platform_alias_and_field_name():
    dossier_id = uuid4()
    by_alias = PRGenerateRequest(dossier_id=dossier_id, platform="cold_pitch")
    by_name = PRGenerateRequest(dossier_id=dossier_id, playbook_type="linkedin")
    assert by_alias.playbook_type == "cold_pitch"
    assert by_name.playbook_type == "linkedin"


def test_reprofile_accepts_persona_alias():
    req = ReprofileRequest(persona="policy_law")
    assert req.persona_id == "policy_law"
    with pytest.raises(ValidationError):
        ReprofileRequest(persona="unknown_persona")


def test_peer_review_requires_80_character_rubric():
    with pytest.raises(ValidationError):
        PeerReviewRequest(
            dossier_id=uuid4(),
            rubric={"strength": "good", "bottleneck": "slow", "suggestion": "cache"},
        )

    valid = PeerReviewRequest(
        dossier_id=uuid4(),
        rubric={
            "strength": "The architecture has a clean event-driven boundary and clear failure isolation.",
            "bottleneck": "The current indexing pass is single-threaded and blocks writes during rebalance.",
            "suggestion": "Move index compaction to a background worker with a double-buffered snapshot.",
        },
    )
    assert valid.dossier_id is not None


def test_registration_normalizes_persona_and_skills():
    req = UserRegisterRequest(
        email="student@example.com",
        password="supersecret",
        full_name="Test Student",
        active_persona_id=" TECH_BUILDER ",
        verified_skills=[" Rust ", "Rust", "", "PyTorch"],
    )
    assert req.active_persona_id == "tech_builder"
    assert req.verified_skills == ["Rust", "PyTorch"]

    with pytest.raises(ValidationError):
        UserRegisterRequest(
            email="student@example.com",
            password="supersecret",
            full_name="Test Student",
            active_persona_id="unknown_persona",
        )


# ----------------------------------------------------------------------
# Dossier serialization from ORM model properties
# ----------------------------------------------------------------------
def test_dossier_response_reads_product_spec_aliases():
    now = datetime.now(timezone.utc)
    user_id = uuid4()
    dossier = ProjectDossier(
        id=uuid4(),
        user_id=user_id,
        slug="edge-llm-kernel-abc123",
        title="Edge LLM Kernel",
        tagline="Sub-millisecond ternary inference",
        domain_persona="tech_builder",
        stage="MVP",
        problem_statement="Microcontrollers cannot run attention layers.",
        solution_breakdown={"architecture": "Custom SIMD kernel with ternary weights."},
        tech_stack=["Rust", "C++"],
        key_metrics=[{"label": "Latency", "value": "12ms"}],
        whitespace_analysis={"market_gap": "No open edge inference stack.", "top_voices": []},
        trend_radar_cache={"last_scouted": now.isoformat()},
        missing_roles=[{"role": "Embedded Engineer", "reason": "Optimize NEON paths."}],
        external_links={"github": "https://github.com/example/repo"},
        verified_status=False,
        boosted=True,
        boosted_until=now + timedelta(hours=48),
        created_at=now,
        updated_at=now,
    )

    response = DossierResponse.model_validate(dossier)
    assert response.owner_id == user_id
    assert response.domain == "tech_builder"
    assert response.solution_architecture.startswith("Custom SIMD")
    assert response.verified_links["github"].endswith("/repo")
    assert response.is_boost_active is True
    assert response.boost_expires_at == response.boosted_until
    assert response.stage == "MVP"
    # Guest session IDs are a claim secret and must never be serialized.
    assert "guest_session_id" not in DossierResponse.model_fields
