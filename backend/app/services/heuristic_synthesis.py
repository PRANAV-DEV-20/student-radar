"""Input-grounded intelligent dossier synthesis.

Transforms student project ideas, repositories, and abstracts into rich,
publication-grade Proof-of-Work Dossiers. Intelligently infers modern technology
stacks, target engineering metrics, core algorithmic foundations, and ecosystem
whitespace directly grounded in the student's concept.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from app.core.config import settings

# Semantic Domain Profiles for Intelligent Concept Grounding
_DOMAIN_PROFILES: Dict[str, Dict[str, Any]] = {
    "interview_career": {
        "keywords": ["interview", "career", "coding round", "behavioral", "resume", "job", "hiring", "recruiter", "mock"],
        "inferred_stack": ["Python", "FastAPI", "Next.js", "WebRTC", "PostgreSQL", "Tailwind CSS", "Whisper Audio"],
        "algorithms": ["Acoustic Pitch & Pace Analyzer", "STAR Method Behavioral Scorer", "AST Code Correctness Verifier"],
        "infra": "WebRTC Audio Stream Gateway + FastAPI async worker + PostgreSQL",
        "metrics": [
            {"label": "Speech-to-Feedback Latency", "value": "< 340ms"},
            {"label": "STAR Scoring Consistency", "value": "94.8%"},
            {"label": "Practice Session Completion", "value": "88%"}
        ],
        "market_gap": "Existing interview platforms rely on static question banks or asynchronous human reviews that take 48 hours for feedback; this architecture delivers sub-second multimodal evaluation.",
        "top_voices": ["@LeetCode", "Hiring Without Whiteboards", "Stanford HCI Group", "OpenAI Applied Team"],
        "roles": [
            {"role": "Applied Audio / Speech ML Engineer", "reason": "Optimize WebRTC audio streaming chunking and voice inflection analysis."},
            {"role": "Technical Curriculum Lead", "reason": "Design realistic engineering rubrics across system design and algorithms."}
        ]
    },
    "education_learning": {
        "keywords": ["tutor", "student", "learn", "teach", "calculus", "physics", "math", "course", "quiz", "homework", "exam", "education"],
        "inferred_stack": ["Python", "FastAPI", "React", "Next.js", "KaTeX", "PostgreSQL", "pgvector", "Tailwind CSS"],
        "algorithms": ["Dynamic Knowledge Tracing (DKT)", "Hierarchical Socratic Step-Tree Parser", "Symbolic Math Step Verifier"],
        "infra": "FastAPI serverless gateway + PostgreSQL (pgvector) + Vercel Edge",
        "metrics": [
            {"label": "Step-Hint Generation Latency", "value": "< 280ms"},
            {"label": "Symbolic Proof Verification", "value": "99.1%"},
            {"label": "Target Student Mastery Uplift", "value": "+32%"}
        ],
        "market_gap": "Standard generative chatbots hallucinate or reveal final answers prematurely without teaching step-by-step reasoning; this engine enforces structured Socratic hints that foster true student mastery.",
        "top_voices": ["Khan Academy Research", "Stanford AI in Education", "Carnegie Learning Labs", "@3Blue1Brown"],
        "roles": [
            {"role": "Full-Stack Educational UX Engineer", "reason": "Build interactive step-by-step canvas with real-time formula rendering."},
            {"role": "Subject Matter Curriculum Architect", "reason": "Validate pedagogical correctness across secondary and university curricula."}
        ]
    },
    "computer_vision_robotics": {
        "keywords": ["vision", "camera", "drone", "robot", "yolo", "detection", "tracking", "autonomous", "lidar", "sensor", "mesh", "spatial"],
        "inferred_stack": ["Python", "C++", "PyTorch", "ROS 2", "OpenCV", "FastAPI", "Docker", "CUDA"],
        "algorithms": ["Extended Kalman Filter (EKF)", "YOLOv11 TensorRT Pipeline", "Dynamic Spatial Octree Partitioning"],
        "infra": "NVIDIA Jetson / ARM64 Companion Edge + ROS 2 Node Daemon",
        "metrics": [
            {"label": "End-to-End Inference", "value": "14.2ms"},
            {"label": "Object Tracking Precision", "value": "0.962"},
            {"label": "Edge Power Footprint", "value": "12.5W"}
        ],
        "market_gap": "Traditional computer vision architectures require continuous broadband cloud streaming; this system performs zero-latency onboard edge inference without cloud failover vulnerability.",
        "top_voices": ["ETH Robotics Systems Lab", "Open Source Robotics Foundation", "@DrDroneAI", "IEEE Robotics Society"],
        "roles": [
            {"role": "Embedded Systems & Firmware Engineer", "reason": "Port neural inference kernels to low-power edge microcontrollers."},
            {"role": "Field Validation Coordinator", "reason": "Execute stress test scenarios under varying lighting and vibration conditions."}
        ]
    },
    "health_biomedical": {
        "keywords": ["health", "medical", "patient", "clinical", "doctor", "hospital", "ecg", "eeg", "dna", "protein", "crispr", "diagnostic", "blood", "biotech"],
        "inferred_stack": ["Python", "FastAPI", "PyTorch", "RDKit", "PostgreSQL", "FHIR Standards", "Next.js", "Docker"],
        "algorithms": ["Signal Wavelet Denoising", "Equivariant Graph Neural Network", "Bio-Conformal Risk Calibration"],
        "infra": "HIPAA-compliant encrypted container enclave + FastAPI on GPU nodes",
        "metrics": [
            {"label": "Diagnostic Sensitivity", "value": "98.4%"},
            {"label": "Analysis Turnaround", "value": "1.8s"},
            {"label": "Calibration Error (ECE)", "value": "< 0.02"}
        ],
        "market_gap": "Diagnostic tooling in this segment is locked behind proprietary medical imaging suites costing $80,000; this architecture democratizes open-access point-of-care analysis.",
        "top_voices": ["Broad Institute", "Stanford Medicine AI", "Open Bio-Informatics Foundation", "Nature Digital Medicine"],
        "roles": [
            {"role": "Bioinformatics / Clinical Data Specialist", "reason": "Curate and clean clinical validation benchmarks according to regulatory guidelines."},
            {"role": "Healthcare UX & Accessibility Lead", "reason": "Design streamlined clinical dashboards adapted for fast bedside workflows."}
        ]
    },
    "fintech_quant": {
        "keywords": ["finance", "trading", "crypto", "defi", "stock", "portfolio", "arbitrage", "liquidity", "wallet", "invoice", "payment", "bank", "token"],
        "inferred_stack": ["Python", "Rust", "FastAPI", "TimescaleDB", "Redis", "Solidity", "Next.js", "WebSockets"],
        "algorithms": ["Stochastic Volatility Calibration", "Loss-Versus-Rebalancing (LVR) Estimator", "Convex Order Routing"],
        "infra": "Low-latency AWS Frankfurt instances with colocated WebSocket multiplexers",
        "metrics": [
            {"label": "Execution Tick Latency", "value": "< 1.2ms"},
            {"label": "Simulated Sharpe Ratio", "value": "3.72"},
            {"label": "Max Slippage Tolerance", "value": "0.03%"}
        ],
        "market_gap": "Retail traders and student builders lack institutional-grade order routing and risk modeling; this system brings quantitative risk guards to decentralized protocols.",
        "top_voices": ["Paradigm Research", "Jump Trading Labs", "Quantitative Finance Bar", "Bankless Research"],
        "roles": [
            {"role": "Quantitative Strategy Modeler", "reason": "Backtest tail-risk liquidity shocks on historical tick datasets."},
            {"role": "Smart Contract Security Auditor", "reason": "Formally verify protocol invariants and reentrancy protections."}
        ]
    },
    "law_policy_governance": {
        "keywords": ["law", "legal", "policy", "statutory", "antitrust", "compliance", "regulation", "court", "privacy", "gdpr", "foia", "rights"],
        "inferred_stack": ["Python", "FastAPI", "PostgreSQL", "pgvector", "Next.js", "Tailwind CSS", "LegalNLP"],
        "algorithms": ["Statutory Diff Engine", "Hierarchical Legal Citation Embeddings", "Antitrust Self-Preferencing Estimator"],
        "infra": "FastAPI + pgvector compliance database with immutable audit logging",
        "metrics": [
            {"label": "Statutory Cross-Check Latency", "value": "1.4s"},
            {"label": "Citation Extraction Precision", "value": "99.2%"},
            {"label": "Compliance Risk Coverage", "value": "100%"}
        ],
        "market_gap": "Manual legal and policy audits cost $500/hour and take months to complete; this platform executes automated statutory compliance verification in sub-second cycles.",
        "top_voices": ["Stanford RegLab", "Berkman Klein Center", "Electronic Frontier Foundation", "FTC Tech Bureau"],
        "roles": [
            {"role": "Legal Technologist / Counsel", "reason": "Structure automated compliance tests into formal statutory filings."},
            {"role": "Policy Outreach Coordinator", "reason": "Coordinate pilot sandboxes with civic agencies and public interest groups."}
        ]
    },
    "developer_security_tools": {
        "keywords": ["security", "vulnerability", "git", "github", "api", "database", "compiler", "wasm", "docker", "kubernetes", "cloud", "cache", "linux"],
        "inferred_stack": ["Rust", "Python", "Go", "FastAPI", "WebAssembly", "Docker", "PostgreSQL", "eBPF"],
        "algorithms": ["Tree-Sitter AST Diff Engine", "SMT Constraint Verification", "Capability-Based Sandbox Enforcement"],
        "infra": "Bare-metal Linux cluster with eBPF runtime probes and Wasmtime sandbox",
        "metrics": [
            {"label": "Cold Start Latency", "value": "0.45ms"},
            {"label": "Memory Overhead", "value": "1.8MB"},
            {"label": "Zero-Day Regression Catch Rate", "value": "99.4%"}
        ],
        "market_gap": "Current developer tooling relies on heavyweight VMs and static linters that miss runtime execution invariants; this engine provides deterministic lightweight sandboxing.",
        "top_voices": ["Bytecode Alliance", "Trail of Bits", "Open Source Security Foundation", "Cloud Native Computing Foundation"],
        "roles": [
            {"role": "Systems & Security Kernel Engineer", "reason": "Harden sandbox boundaries and monitor syscall limits via eBPF."},
            {"role": "Developer Relations & Tooling Lead", "reason": "Author CLI integrations and community documentation for open source adoption."}
        ]
    },
    "community_marketplace": {
        "keywords": ["marketplace", "community", "campus", "sharing", "swipes", "food", "waste", "donation", "trade", "exchange", "local"],
        "inferred_stack": ["TypeScript", "Next.js", "FastAPI", "PostgreSQL", "Redis", "Tailwind CSS", "Twilio / WhatsApp"],
        "algorithms": ["Stable Marriage Matching Algorithm", "Geospatial Proximity Scorer", "Dynamic Supply-Demand Rebalancer"],
        "infra": "Next.js Vercel Edge + FastAPI on Railway + Redis Cache",
        "metrics": [
            {"label": "Peer Match Latency", "value": "< 850ms"},
            {"label": "Exchange Fulfillment Rate", "value": "92.4%"},
            {"label": "Active Student Retention", "value": "76%"}
        ],
        "market_gap": "Campus marketplaces rely on unorganized WhatsApp group chats and bulletin boards that lead to unfulfilled trades; this platform provides verified peer matching and settlement.",
        "top_voices": ["Campus Tech Labs", "Circular Economy Forum", "Product Hunt Builders", "Student Innovation Network"],
        "roles": [
            {"role": "Campus Community & Growth Lead", "reason": "Deploy campus ambassador programs to onboard early dorm networks."},
            {"role": "Full-Stack Mobile Engineer", "reason": "Build seamless Progressive Web App (PWA) with instant notifications."}
        ]
    }
}


_GENERIC_PROFILE: Dict[str, Any] = {
    "keywords": [],
    "inferred_stack": [],
    "algorithms": [],
    "infra": "Component architecture derived directly from the submitted artifact.",
    "metrics": [],
    "market_gap": "",
    "top_voices": [],
    "roles": [],
}

# Persona-owned roles keep the collaborator suggestions aligned with the
# selected domain rather than with incidental keywords in the concept text.
_PERSONA_ROLES: Dict[str, List[Dict[str, str]]] = {
    "tech_builder": [
        {"role": "Full-Stack Product Engineer", "reason": "Turn the submitted architecture into a working, testable prototype."},
        {"role": "Applied ML / Data Engineer", "reason": "Validate the data pipeline and measurable behaviour of the core model."},
    ],
    "policy_law": [
        {"role": "Policy / Regulatory Strategy Lead", "reason": "Map the concept to relevant statutory and compliance requirements."},
        {"role": "Legal Technologist", "reason": "Structure evidence, audit trails, and governance into the prototype."},
    ],
    "business_finance": [
        {"role": "Business Model & GTM Lead", "reason": "Define the target segment and a verifiable path to first users."},
        {"role": "Financial Analyst", "reason": "Build a unit-economics model tied to the submitted value proposition."},
    ],
    "design_biotech": [
        {"role": "Research / Domain Specialist", "reason": "Check the scientific assumptions behind the submitted concept."},
        {"role": "Accessible Experience Designer", "reason": "Translate complex domain workflows into an inclusive, testable interface."},
    ],
}

_GITHUB_REPO_RE = re.compile(r"github\.com/[^/\s]+/([^/\s?#]+)", re.IGNORECASE)
_TECH_CANONICAL: Tuple[Tuple[str, str], ...] = (
    ("postgresql", "PostgreSQL"),
    ("postgres", "PostgreSQL"),
    ("pgvector", "pgvector"),
    ("fastapi", "FastAPI"),
    ("next.js", "Next.js"),
    ("nextjs", "Next.js"),
    ("whatsapp", "WhatsApp"),
    ("twilio", "Twilio"),
    ("clip", "CLIP"),
    ("pytorch", "PyTorch"),
    ("tensorflow", "TensorFlow"),
    ("opencv", "OpenCV"),
    ("python", "Python"),
    ("rust", "Rust"),
    ("react", "React"),
    ("redis", "Redis"),
    ("docker", "Docker"),
    ("kubernetes", "Kubernetes"),
)
_METRIC_RE = re.compile(
    r"(?<![\w.])(?P<value>\d+(?:\.\d+)?\s?(?:%|x|ms|s|kg|km))(?![A-Za-z])",
    re.IGNORECASE,
)
_TRAILING_WORDS = {"and", "with", "for", "the", "a", "an", "of", "to", "via"}


def _detect_profile(text: str) -> Dict[str, Any]:
    lowered = text.lower()
    best_match = _GENERIC_PROFILE
    max_score = 0

    for profile in _DOMAIN_PROFILES.values():
        score = sum(2 for kw in profile["keywords"] if kw in lowered)
        if score > max_score:
            max_score = score
            best_match = profile

    return best_match


def _clean_title(raw: str, input_type: str = "idea") -> str:
    text = (raw or "").strip()

    if input_type == "github":
        match = _GITHUB_REPO_RE.search(text)
        repo = match.group(1) if match else text.split()[0] if text else ""
        repo = re.sub(r"\.git$", "", repo, flags=re.IGNORECASE)
        repo = re.sub(r"[_\-]+", " ", repo)
        repo = re.sub(r"\s+", " ", repo).strip()
        return " ".join(word.capitalize() for word in repo.split()) or "Repository Dossier"

    first = re.split(r"(?<=[.!?])\s+|\n", text, maxsplit=1)[0].strip()
    first = re.sub(r"^(?:i want to build|we are building|building|create|developing)\s+", "", first, flags=re.IGNORECASE)
    first = re.sub(r"^(?:a|an|the)\s+", "", first, flags=re.IGNORECASE)

    product_match = re.search(
        r"\b(?:called|named)\s+([A-Z][A-Za-z0-9]*(?:[A-Z][A-Za-z0-9]*)*|[A-Za-z][A-Za-z0-9]*)",
        first,
    )
    product = product_match.group(1).strip(".,;:") if product_match else None

    descriptive = re.sub(r"\b(?:called|named)\s+[A-Za-z0-9]+\b", "", first, flags=re.IGNORECASE)
    descriptive = re.sub(r"\s+", " ", descriptive).strip(" .,:;")
    words = descriptive.split()[:8]
    while words and words[-1].lower() in _TRAILING_WORDS:
        words.pop()
    descriptive_title = " ".join(word.title() for word in words)

    if product and descriptive_title:
        return f"{product} — {descriptive_title}"
    if product:
        return product
    return descriptive_title or "Student Innovation Project"


def _extract_tech_stack(text: str) -> List[str]:
    found: List[str] = []
    for needle, canonical in _TECH_CANONICAL:
        if canonical in found:
            continue
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(needle)}(?![A-Za-z0-9])", text, re.IGNORECASE):
            found.append(canonical)
    return found


def _extract_metrics(text: str) -> List[Dict[str, str]]:
    metrics: List[Dict[str, str]] = []
    seen: set[str] = set()
    for match in _METRIC_RE.finditer(text):
        value = match.group("value").strip()
        if value.lower() in seen:
            continue
        seen.add(value.lower())
        prefix = text[max(0, match.start() - 90) : match.start()].lower()
        if any(token in prefix for token in ("reduc", "cut ", "lower", "saving")):
            label = "Reduction"
        elif any(token in prefix for token in ("increas", "uplift", "improv", "gain")):
            label = "Improvement"
        elif "latency" in prefix:
            label = "Latency"
        elif "accur" in prefix or "precision" in prefix:
            label = "Accuracy"
        else:
            label = "Measured Value"
        metrics.append({"label": label, "value": value})
    return metrics


def synthesize_dossier(
    raw_content: str,
    domain_persona: str = "tech_builder",
    input_type: str = "idea",
) -> Dict[str, Any]:
    """Build an intelligent dossier directly grounded in the student's text."""
    text = (raw_content or "").strip()
    persona = (domain_persona or "tech_builder").strip().lower()
    if persona not in settings.KNOWN_PERSONAS:
        persona = "tech_builder"

    profile = _detect_profile(text)
    title = _clean_title(text, input_type)
    tech_stack = _extract_tech_stack(text)
    metrics = _extract_metrics(text)

    if len(text) < 40:
        problem = (
            f"Students and developers currently lack an integrated, reliable tool for "
            f"{title.lower()}; manual workflows are fragmented and error-prone."
        )
    else:
        # Use the submitted artifact verbatim. The synthesizer must not add
        # unverified market claims or performance numbers to the problem.
        problem = text

    integrations = [tech for tech in tech_stack if tech in {"WhatsApp", "Twilio", "Slack", "Discord"}]
    infra = profile["infra"]
    if integrations:
        infra = f"{infra} + {', '.join(integrations)} notification integration"

    market_gap = profile["market_gap"]
    if not market_gap:
        market_gap = (
            "Positioning hypothesis derived only from the submitted problem statement: "
            f"{problem[:220].strip()}"
        )

    external_links = {}
    if input_type == "github" and text.startswith(("http://", "https://")):
        external_links["github"] = text

    return {
        "title": title,
        "tagline": (
            f"Input-grounded {persona.replace('_', ' ')} concept with explicit assumptions "
            "and a verifiable architecture."
        ),
        "domain_persona": persona,
        "stage": "Prototype" if input_type in {"github", "repo"} else "Idea",
        "problem_statement": problem,
        "solution_breakdown": {
            "architecture": (
                "Modular component architecture derived from the submitted artifact: "
                f"{', '.join(tech_stack) if tech_stack else 'stack inferred from the brief'}."
            ),
            "core_algorithms": list(profile["algorithms"]),
            "hardware_or_infra": infra,
            "integration_signals": integrations,
        },
        "tech_stack": tech_stack,
        "key_metrics": metrics,
        "whitespace_analysis": {
            "market_gap": market_gap,
            "top_voices": [],
        },
        "missing_roles": list(_PERSONA_ROLES.get(persona, _PERSONA_ROLES["tech_builder"])),
        "external_links": external_links,
    }
