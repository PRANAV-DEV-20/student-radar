"""Stage 1: build structured Project DNA from an idea, repo URL or paper."""
from __future__ import annotations

import re
from typing import Any, Dict, List

from app.services.github_ingest import github_ingestor

_TECH_RE = re.compile(
    r"(?i)\b(python|javascript|typescript|react|next\.?js|fastapi|pytorch|tensorflow|scikit-learn|"
    r"opencv|postgres(?:ql)?|redis|docker|kubernetes|rust|go|java|flutter|swift|langchain|llm|"
    r"hugging ?face|tflite|onnx)\b"
)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def _sentences(text: str, limit: int = 40) -> List[str]:
    return [s.strip()[:400] for s in _SENTENCE_RE.split(text or "") if len(s.strip()) > 20][:limit]


def _pdf_sections(text: str) -> Dict[str, str]:
    headings = r"(?im)^\s*(abstract|introduction|methods?|methodology|results?|limitations?|conclusions?|discussion|dataset|datasets)\s*[:\.]?\s*$"
    matches = list(re.finditer(headings, text or ""))
    sections: Dict[str, str] = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[match.group(1).lower()] = text[match.end():end].strip()[:4000]
    return sections


async def build_project_dna(
    *, input_type: str, raw_content: str, domain_persona: str
) -> Dict[str, Any]:
    """Return input-grounded DNA. Unknowns stay unknown; assumptions are explicit."""
    if input_type == "github" and "github.com" in raw_content.lower():
        dna = await github_ingestor.ingest(raw_content)
        dna["domain_persona"] = domain_persona
        return dna

    text = (raw_content or "").strip()
    if input_type == "pdf_text":
        sections = _pdf_sections(text)
        abstract = sections.get("abstract", "")
        methods = sections.get("methods") or sections.get("methodology") or ""
        results = sections.get("results") or ""
        limitations = sections.get("limitations") or sections.get("discussion") or ""
        dna = {
            "source_type": "paper",
            "problem": (abstract[:1000] or (_sentences(text, 3) or ["Problem not stated in the supplied document"])[0]),
            "solution": methods[:1200] or "Method section not detected in the supplied document",
            "results": results[:1200],
            "stated_limitations": limitations[:1200],
            "datasets": [s.strip()[:160] for s in re.findall(r"(?i)dataset[:\s]+([^\n.]{3,160})", text)[:8]],
            "technique": ", ".join(sorted(set(match.group(0).lower() for match in _TECH_RE.finditer(text)))[:8]),
            "stage": "Research",
            "audience_guess": "Researchers evaluating this method",
            "paper_sections": list(sections.keys()),
            "assumptions": [
                "Section headings were detected by keyword matching; ambiguous text stayed in its nearest section.",
                "No external validation of the paper's reported results was performed during ingestion.",
            ],
            "unknowns": ["Real-world field performance", "Licence and availability of the described implementation"],
        }
        dna["title"] = _paper_title(text)
        return dna

    # Raw idea: keep the submitted text as the source of truth.
    sentences = _sentences(text)
    first = sentences[0] if sentences else text[:300]
    title = _idea_title(first)
    tech = sorted(set(match.group(0) for match in _TECH_RE.finditer(text)))[:10]
    claims = [s for s in sentences if re.search(r"(?i)\d+(\.\d+)?\s?%|accuracy|outperform|best|fastest|state of the art", s)][:8]
    dna = {
        "source_type": "idea",
        "title": title,
        "problem": first,
        "solution": sentences[1] if len(sentences) > 1 else "Solution not stated in the submitted idea.",
        "audience_guess": _audience_guess(text),
        "domain_persona": domain_persona,
        "stage": "Idea",
        "technique": ", ".join(tech),
        "claims": claims,
        "technologies_mentioned": tech,
        "assumptions": [
            "The first sentence of the submission describes the core problem.",
            "Audience was inferred only from explicitly named users in the text; it is marked as an assumption.",
            "No details were invented to fill gaps in the idea.",
        ],
        "unknowns": [
            "Target geography and language requirements were not stated.",
            "Validation data and baseline were not stated.",
            "Team skills, time and budget come from the student profile, not the idea text.",
        ],
        "raw_excerpt": text[:4000],
    }
    return dna


def _idea_title(first_sentence: str) -> str:
    cleaned = re.sub(r"(?i)^(i want to build|we are building|building|create|developing|a|an|the)\s+", "", first_sentence.strip())
    words = cleaned.split()[:10]
    return " ".join(word[:40] for word in words).strip(" .,:;")[:120] or "Student Project Idea"


def _paper_title(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    for line in lines[:12]:
        if 10 < len(line) < 200 and not line.lower().startswith(("abstract", "https://", "arxiv")):
            return line[:180]
    return "Submitted Research Paper"


def _audience_guess(text: str) -> str:
    lowered = (text or "").lower()
    hints = []
    for token, audience in (
        ("farmer", "farmers"), ("student", "students"), ("doctor", "clinicians"),
        ("teacher", "teachers"), ("lawyer", "legal practitioners"), ("developer", "developers"),
        ("patient", "patients"), ("researcher", "researchers"),
    ):
        if token in lowered:
            hints.append(audience)
    return ", ".join(hints[:4]) if hints else "Audience not explicitly named in the input"
