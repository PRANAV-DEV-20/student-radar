import json

from app.services.gemini_client import gemini_service
from app.services.heuristic_synthesis import synthesize_dossier


def test_fallback_uses_submitted_concept() -> None:
    raw = (
        "A campus lost-and-found platform called FindIt. Students post items they lost or "
        "found, the app uses CLIP image embeddings to match photos, sends WhatsApp alerts "
        "to nearby students, and rewards verified returns with points. Built with Next.js, "
        "FastAPI, PostgreSQL and pgvector."
    )

    dossier = synthesize_dossier(raw, "tech_builder", "idea")

    assert "FindIt" in dossier["title"]
    assert "Campus Lost-And-Found Platform" in dossier["title"]
    assert "CLIP" in dossier["tech_stack"]
    assert "FastAPI" in dossier["tech_stack"]
    assert "PostgreSQL" in dossier["tech_stack"]
    assert "pgvector" in dossier["tech_stack"]
    assert "lost" in dossier["problem_statement"].lower()
    assert "WhatsApp" in json.dumps(dossier["solution_breakdown"])
    assert dossier["stage"] == "Idea"
    assert dossier["key_metrics"] == []


def test_fallback_does_not_reuse_static_drone_template() -> None:
    dossier = synthesize_dossier(
        "A meal-planning app for hostellers with dietary filters and a grocery budget tracker.",
        "tech_builder",
        "idea",
    )

    serialized = json.dumps(dossier).lower()
    assert "drone" not in serialized
    assert "raft" not in serialized
    assert "px4" not in serialized
    assert "meal-planning" in dossier["title"].lower()
    assert "meal" in dossier["problem_statement"].lower()


def test_fallback_extracts_grounded_metrics_and_persona_roles() -> None:
    dossier = synthesize_dossier(
        "A causal-inference scraper that audits self-preferencing marketplace algorithms. "
        "It reduced audit time by 34.2% for the FTC and the EU Digital Markets Act.",
        "policy_law",
        "idea",
    )

    assert dossier["key_metrics"][0] == {"label": "Reduction", "value": "34.2%"}
    roles = [item["role"] for item in dossier["missing_roles"]]
    assert any("Policy" in role or "Regulatory" in role for role in roles)
    assert not any("Quantitative" in role for role in roles)


def test_fallback_uses_github_repo_name_without_inventing_a_stack() -> None:
    dossier = synthesize_dossier(
        "https://github.com/student-radar/drone-swarm-mesh",
        "tech_builder",
        "github",
    )

    assert dossier["title"] == "Drone Swarm Mesh"
    assert dossier["tech_stack"] == []
    assert dossier["key_metrics"] == []
    assert "drone" not in dossier["tagline"].lower()


def test_gemini_fallback_delegates_to_input_grounded_synthesizer() -> None:
    dossier = gemini_service._fallback_dossier_synthesis(
        raw_content=(
            "A peer-to-peer textbook exchange app named BookLoop. It uses PostgreSQL and "
            "College students struggle to afford textbooks between semesters."
        ),
        domain_persona="tech_builder",
        input_type="idea",
    )

    assert "BookLoop" in dossier["title"]
    assert "PostgreSQL" in dossier["tech_stack"]
    assert "textbook" in dossier["tagline"].lower() or "textbook" in dossier["problem_statement"].lower()
