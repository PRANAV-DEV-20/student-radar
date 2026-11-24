"""Stage 2 of the Radar pipeline: messy input -> structured Concept Profile.

Search APIs return "random" results when a raw conversational paragraph is
passed through unchanged. This module converts the user's idea (or an extracted
GitHub README / PDF passage) into:

* must-have core entities, and
* four keyword-dense queries: trends, news, events, opportunities.

Groq is used for the semantic extraction. A deterministic fallback builds the
same shape from the input text so the pipeline still works without a key.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence

from app.services.groq_client import groq_client

RADAR_QUERY_KEYS: Sequence[str] = ("trends", "news", "events", "opportunities")
DOSSIER_QUERY_KEYS: Sequence[str] = ("competitors", "market_trends", "technical_connectors")

_STOPWORDS = {
    "about", "across", "after", "again", "against", "also", "and", "any", "are",
    "build", "building", "can", "could", "for", "from", "have", "help", "into",
    "its", "make", "many", "more", "most", "our", "out", "over", "project",
    "should", "some", "solution", "that", "the", "their", "this", "through",
    "tool", "using", "want", "was", "were", "what", "when", "where", "which",
    "with", "would", "your", "students", "student", "idea", "work", "need",
    "like", "just", "really", "please", "find", "show", "give", "want", "based",
}
_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}")


def _clean_text(value: Any, limit: int = 300) -> str:
    return " ".join(str(value or "").split())[:limit].strip()


def _tokens(text: str) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for match in _TOKEN_RE.finditer(text.lower()):
        token = match.group(0).strip(".-")
        if len(token) < 3 or token in _STOPWORDS or token in seen or token.isdigit():
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _fallback_profile(context: Dict[str, Any]) -> Dict[str, Any]:
    """Build a valid Concept Profile without any LLM call."""

    title = _clean_text(context.get("title"), 120)
    problem = _clean_text(
        context.get("problem_statement") or context.get("raw_idea"), 500
    )
    persona_label = _clean_text(context.get("persona_label"), 90)
    tech = [str(item).strip() for item in (context.get("tech_stack") or []) if str(item).strip()]
    terms = _tokens(f"{title} {problem} {' '.join(tech)}")
    keywords = terms[:6]
    # A persona label like "Engineering & AI Systems" is too broad to search.
    # The project's own concrete topic makes every bucket keyword-dense.
    domain = " ".join(keywords[:3]) or title or persona_label or "student innovation"
    keyword_text = " ".join(keywords[:4]) or domain.lower()
    year = datetime.now(timezone.utc).year
    next_year = year + 1

    entities = list(dict.fromkeys([title, *tech[:3], *keywords[:4]]))
    entities = [entity for entity in entities if entity][:8]

    return {
        "project_title": title or problem[:80] or "Student concept",
        "core_domain": domain,
        "problem_statement": problem,
        "tech_stack": tech[:8],
        "target_audience": "students and early-stage builders",
        "core_entities": entities,
        "radar_queries": {
            "trends": f"{domain} {keyword_text} market growth trends adoption {year}",
            "news": f"{keyword_text} breakthrough launch OR release OR funding",
            "events": f"{domain} {keyword_text} hackathon OR summit OR buildathon {year} {next_year}",
            "opportunities": f"{domain} {keyword_text} startup grant OR accelerator OR fellowship",
        },
        "dossier_queries": {
            "competitors": f"{keyword_text} similar product startup comparison",
            "market_trends": f"{domain} market adoption report {year}",
            "technical_connectors": f"{keyword_text} open source github dataset",
        },
        "source": "heuristic",
    }


_PROMPT_TEMPLATE = """You are a search planner for a student opportunity radar.

Convert the messy concept below into a STRUCTURED CONCEPT PROFILE. Do not answer the idea; only extract precise search inputs.

RULES:
- project_title, core_domain, problem_statement, tech_stack, target_audience: use ONLY facts present in the input. Do not invent.
- core_entities: 4-8 must-have keyword phrases that a relevant result must relate to (technology, problem, audience, location).
- radar_queries: exactly 4 keys, one per bucket, each 5-9 keyword-dense words and under 120 characters. Avoid long descriptive clauses:
  * trends: "{{industry/tech}} market growth trends adoption {year}"
  * news: "{{core domain}}" "{{core technology}}" breakthrough launch; keep domain words so generic AI news is rejected
  * events: "{{domain}}" hackathon OR summit OR buildathon {year} {next_year}; include India and global framing
  * opportunities: "{{sector}}" startup grant OR accelerator OR RFP; include India and global framing
- dossier_queries: exactly 3 keys: competitors, market_trends, technical_connectors (github/arxiv/dataset).
- Never add URLs, deadlines, prize amounts, or statistics.
- Return JSON only with exactly these keys: project_title, core_domain, problem_statement, tech_stack, target_audience, core_entities, radar_queries, dossier_queries.

CONCEPT CONTEXT:
{context}
"""


def _merge_profile(base: Dict[str, Any], parsed: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)

    # The model sometimes expands a concrete idea into a broad persona label
    # ("Artificial Intelligence, Agriculture, Edge Computing"). Keep the raw
    # idea's concrete anchors so search and relevance checks stay grounded.
    anchors = [
        str(item).lower()
        for item in (base.get("core_entities") or [])
        if str(item).strip() and len(str(item).strip()) > 3
    ]

    def grounded(value: str) -> bool:
        lowered = value.lower()
        return any(anchor in lowered for anchor in anchors)

    for key in ("project_title", "core_domain", "problem_statement", "target_audience"):
        value = parsed.get(key)
        if isinstance(value, str) and value.strip():
            cleaned = _clean_text(value, 400)
            if key in {"project_title", "core_domain"} and not grounded(cleaned):
                continue
            result[key] = cleaned

    for key in ("tech_stack", "core_entities"):
        value = parsed.get(key)
        if isinstance(value, list):
            cleaned = [_clean_text(item, 90) for item in value if str(item).strip()]
            if cleaned:
                result[key] = list(
                    dict.fromkeys([*(base.get(key) or []), *cleaned])
                )[:10]

    for section in ("radar_queries", "dossier_queries"):
        value = parsed.get(section)
        if not isinstance(value, dict):
            continue
        keys = RADAR_QUERY_KEYS if section == "radar_queries" else DOSSIER_QUERY_KEYS
        merged = dict(result.get(section) or {})
        for key in keys:
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                merged[key] = _clean_text(item, 140)
        result[section] = merged

    result["source"] = "groq"
    return result


async def build_concept_profile(
    context: Dict[str, Any],
    language: str = "en",
) -> Dict[str, Any]:
    """Normalize any raw concept into grounded, search-ready intent strings."""

    profile = _fallback_profile(context)
    if not groq_client.configured:
        return profile

    year = datetime.now(timezone.utc).year
    prompt = _PROMPT_TEMPLATE.format(
        context=str(context.get("summary") or context.get("raw_idea") or context)[:5000],
        year=year,
        next_year=year + 1,
    )
    parsed = await groq_client.generate_json(
        prompt,
        system=(
            "You extract structured search metadata from user ideas. "
            "Respond with JSON only. Never invent facts."
        ),
        max_tokens=1400,
    )
    if not parsed:
        return profile
    return _merge_profile(profile, parsed)
