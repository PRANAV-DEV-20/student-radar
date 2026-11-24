"""Request/response and validation schemas for Dossier v2."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SECTION_KEYS: List[str] = [
    "executive_brief",
    "idea_restated",
    "problem_users",
    "market_landscape",
    "related_work",
    "novelty_assessment",
    "gaps",
    "challenges_risks",
    "feasibility",
    "solution_design",
    "tech_stack",
    "data_evaluation",
    "validation_plan",
    "roadmap",
    "people_community",
    "funding_opportunities",
    "visibility_angle",
    "open_questions_evidence",
]

# Sections that need cross-section reasoning and are written last.
CROSS_SECTIONS = {"gaps", "novelty_assessment", "tech_stack", "roadmap", "executive_brief"}
FIRST_PASS_SECTIONS = [key for key in SECTION_KEYS if key not in CROSS_SECTIONS]

LABELS = {"grounded", "input", "inference", "recommendation"}
CONFIDENCES = {"high", "medium", "low"}
COVERAGES = {"strong", "thin", "none"}
SEVERITIES = {"low", "medium", "high", "critical"}
EFFORTS = {"low", "medium", "high"}
PERSONAS = {"tech_builder", "policy_law", "business_finance", "design_biotech"}
MODES = {"quick", "deep"}

_REF_RE = re.compile(r"^E\d+$")
_URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)


class StudentProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    skills: List[str] = Field(default_factory=list, max_length=40)
    weekly_hours: float = Field(default=6.0, ge=0, le=80)
    budget_usd: float = Field(default=0.0, ge=0, le=100000)
    country: str = ""
    education_level: str = ""
    goals: List[str] = Field(default_factory=list, max_length=12)
    purpose: Literal["coursework", "research", "product"] = "product"


class RunCreateRequest(BaseModel):
    input_type: Literal["idea", "github", "pdf_text"] = "idea"
    raw_content: str = Field(..., min_length=8, description="Free-form input text. No upper length limit.")
    domain_persona: str = "tech_builder"
    mode: Literal["quick", "deep"] = "deep"
    profile: StudentProfile = Field(default_factory=StudentProfile)

    @field_validator("domain_persona")
    @classmethod
    def _persona(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in PERSONAS:
            raise ValueError(f"domain_persona must be one of: {', '.join(sorted(PERSONAS))}")
        return value


class DeepenRequest(BaseModel):
    section: str

    @field_validator("section")
    @classmethod
    def _valid_section(cls, value: str) -> str:
        if value not in SECTION_KEYS:
            raise ValueError(f"Unknown section: {value}")
        return value


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)


class RoadmapTask(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    section: str = "roadmap"
    effort: str = "low"


class RoadmapRequest(BaseModel):
    items: List[RoadmapTask] = Field(..., min_length=1, max_length=20)


class SectionPatch(BaseModel):
    content: Dict[str, Any]
    locked: bool = False


class SectionItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = ""
    label: str
    text: str
    evidence: List[str] = Field(default_factory=list)
    reasoning: str = ""
    effort: str = ""
    severity: str = ""

    @field_validator("label")
    @classmethod
    def _label(cls, value: str) -> str:
        if value not in LABELS:
            raise ValueError(f"Invalid label: {value}")
        return value

    @field_validator("evidence")
    @classmethod
    def _refs(cls, values: List[str]) -> List[str]:
        for ref in values:
            if not _REF_RE.match(str(ref)):
                raise ValueError(f"Invalid evidence ref: {ref}")
        return [str(v) for v in values]


class SectionTable(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = ""
    columns: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)


class SectionPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    section: str
    summary: str = ""
    confidence: str = "low"
    coverage: str = "none"
    items: List[SectionItem] = Field(default_factory=list)
    tables: List[SectionTable] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    generated_by: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("section")
    @classmethod
    def _section(cls, value: str) -> str:
        if value not in SECTION_KEYS:
            raise ValueError(f"Unknown section: {value}")
        return value

    @field_validator("confidence")
    @classmethod
    def _confidence(cls, value: str) -> str:
        if value not in CONFIDENCES:
            raise ValueError(f"Invalid confidence: {value}")
        return value

    @field_validator("coverage")
    @classmethod
    def _coverage(cls, value: str) -> str:
        if value not in COVERAGES:
            raise ValueError(f"Invalid coverage: {value}")
        return value


def validate_section_payload(
    payload: Dict[str, Any],
    expected_section: str,
    known_refs: Optional[set[str]] = None,
) -> Dict[str, Any]:
    """Validate a generated section. Raises ValueError on fabricated claims.

    Checks mirror the automated QA rules: every grounded item must cite an
    evidence id, every inference must show its reasoning, all cited refs must
    resolve, and related-work rows must carry a real retrieved URL + evidence
    id. This is deliberately strict: failing sections are repaired or shown
    as low-confidence, never silently accepted.
    """
    if not isinstance(payload, dict):
        raise ValueError("Section payload must be a JSON object")
    payload = dict(payload)
    if payload.get("section") != expected_section:
        payload["section"] = expected_section

    model = SectionPayload.model_validate(payload)
    data = model.model_dump()

    if not (data["summary"].strip() or data["items"] or data["tables"]):
        raise ValueError("Section is empty")

    seen_item_ids: set[str] = set()
    for item in data["items"]:
        label = item["label"]
        if label == "grounded" and not item["evidence"]:
            raise ValueError("Grounded claim without evidence id")
        if label == "inference" and not item["reasoning"].strip():
            raise ValueError("Inference without reasoning")
        if label == "recommendation" and not item["effort"]:
            raise ValueError("Recommendation without effort")
        if item["id"]:
            if item["id"] in seen_item_ids:
                raise ValueError(f"Duplicate item id: {item['id']}")
            seen_item_ids.add(item["id"])
        if known_refs is not None:
            for ref in item["evidence"]:
                if ref not in known_refs:
                    raise ValueError(f"Unresolved evidence id: {ref}")

    if known_refs is not None and expected_section == "related_work":
        for table in data["tables"]:
            columns = [str(c).lower() for c in table["columns"]]
            if "url" not in columns or "evidence_id" not in columns:
                raise ValueError("Related work table must include url and evidence_id columns")
            url_idx = columns.index("url")
            ref_idx = columns.index("evidence_id")
            for row in table["rows"]:
                if len(row) <= max(url_idx, ref_idx):
                    raise ValueError("Related work row is missing url or evidence_id")
                url = str(row[url_idx]).strip()
                ref = str(row[ref_idx]).strip()
                if not _URL_RE.match(url):
                    raise ValueError(f"Related work item without a retrieved URL: {url}")
                if ref not in known_refs:
                    raise ValueError(f"Related work item with unresolved evidence id: {ref}")

    if known_refs is not None:
        for table in data["tables"]:
            columns = [str(c).lower() for c in table["columns"]]
            for col in ("evidence_id", "evidence_ids", "evidence"):
                if col in columns:
                    idx = columns.index(col)
                    for row in table["rows"]:
                        if idx >= len(row):
                            continue
                        value = str(row[idx])
                        refs = re.findall(r"E\d+", value)
                        for ref in refs:
                            if ref not in known_refs:
                                raise ValueError(f"Unresolved evidence id in table: {ref}")

    return data


def check_evidence_support(claim: str, passage: str) -> bool:
    """Cheap citation verifier: require lexical overlap with the stored passage.

    Numbers, proper nouns and technical terms in a grounded claim should appear
    in (or be directly derivable from) the passage it cites. This catches
    hallucinated citations without needing another model call.
    """
    stopwords = {
        "the", "and", "for", "from", "this", "that", "with", "have", "has", "was",
        "are", "were", "into", "than", "then", "its", "it's", "their", "our", "you",
        "your", "can", "could", "should", "would", "about", "based", "using", "used",
    }
    claim_terms = {
        term for term in re.findall(r"[a-z0-9][a-z0-9.\-]{2,}", claim.lower())
        if term not in stopwords
    }
    if not claim_terms:
        return True
    haystack = passage.lower()
    overlap = sum(1 for term in claim_terms if term in haystack)
    return overlap >= 1
