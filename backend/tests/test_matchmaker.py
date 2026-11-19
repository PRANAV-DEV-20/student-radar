import asyncio
import uuid
from types import SimpleNamespace

from app.services.matchmaker import _role_coverage, _tokens, matchmaker


class FakeResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, users):
        self.users = users

    async def execute(self, statement):
        return FakeResult(self.users)


def test_role_tokens_strip_job_title_noise():
    tokens = _tokens("Senior Embedded Systems Engineer")
    assert "embedded" in tokens
    assert "systems" in tokens
    assert "senior" not in tokens
    assert "engineer" not in tokens


def test_role_coverage_detects_portfolio_fit():
    skills = _tokens("Rust Embedded Systems LoRaWAN")
    assert _role_coverage("Embedded Systems Engineer", skills) == 1.0
    assert _role_coverage("Medicinal Chemist", skills) == 0.0


def test_matchmaker_ranks_skill_gap_fit():
    owner_id = uuid.uuid4()
    dossier = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=owner_id,
        slug="drone-swarm",
        domain_persona="tech_builder",
        missing_roles=[{"role": "Embedded Systems Engineer", "reason": "Tune radio stack."}],
        missing_roles_embedding=None,
    )
    candidate = SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Aarav Mehta",
        avatar_url=None,
        campus_or_org="IIT Bombay",
        city="Mumbai",
        active_persona_id="tech_builder",
        verified_skills=["Rust", "Embedded Systems", "LoRaWAN"],
        skills_embedding=None,
        dossiers=[SimpleNamespace(tech_stack=["Rust", "ROS 2"])],
    )

    response = asyncio.run(
        matchmaker.match_cobuilders(FakeSession([candidate]), dossier, limit=3)
    )

    assert response.dossier_slug == "drone-swarm"
    assert response.missing_roles == ["Embedded Systems Engineer"]
    assert len(response.matches) == 1
    match = response.matches[0]
    assert match.user_id == candidate.id
    assert match.match_score > 0.5
    assert "Embedded Systems Engineer" in match.matched_roles
    assert "Rust" in match.verified_skills
    assert match.active_dossiers_count == 1


def test_matchmaker_without_explicit_gap_still_returns_candidates():
    dossier = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        slug="open-project",
        domain_persona="tech_builder",
        missing_roles=[],
        missing_roles_embedding=None,
    )
    candidate = SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Meera Iyer",
        avatar_url=None,
        campus_or_org="NLSIU",
        city="Bengaluru",
        active_persona_id="policy_law",
        verified_skills=["Policy Analysis", "AI Governance"],
        skills_embedding=None,
        dossiers=[SimpleNamespace(tech_stack=["Python"])],
    )

    response = asyncio.run(
        matchmaker.match_cobuilders(FakeSession([candidate]), dossier, limit=5)
    )
    assert len(response.matches) == 1
    assert response.matches[0].match_score >= 0.05
