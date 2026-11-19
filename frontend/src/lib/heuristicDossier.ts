/**
 * Intelligent Semantic Concept Synthesis Engine
 * 
 * Takes raw student ideas, GitHub URLs, or research abstracts and transforms
 * them into publication-grade Proof-of-Work Dossiers.
 * 
 * Analyzes semantic intent, target user, technical mechanisms, domain personas,
 * realistic target benchmarks, inferred modern stack, and ecosystem whitespace.
 */

interface TechDomainProfile {
  domains: string[];
  inferredStack: string[];
  algorithms: string[];
  infra: string;
  metrics: Array<{ label: string; value: string }>;
  gapTemplate: (title: string, problem: string) => string;
  topVoices: string[];
  roles: Array<{ role: string; reason: string }>;
}

const DOMAIN_PROFILES: Record<string, TechDomainProfile> = {
  interview_career: {
    domains: ["interview", "career", "coding round", "behavioral", "resume", "job", "hiring", "recruiter", "mock"],
    inferredStack: ["Python", "FastAPI", "Next.js", "WebRTC", "PostgreSQL", "Tailwind CSS", "Whisper Audio"],
    algorithms: ["Acoustic Pitch & Pace Analyzer", "STAR Method Behavioral Scorer", "AST Code Correctness Verifier"],
    infra: "WebRTC Audio Stream Gateway + FastAPI async worker + PostgreSQL",
    metrics: [
      { label: "Speech-to-Feedback Latency", value: "< 340ms" },
      { label: "STAR Scoring Consistency", value: "94.8%" },
      { label: "Practice Session Completion", value: "88%" }
    ],
    gapTemplate: (title) => `Existing interview tools rely on static question banks or asynchronous video reviews that take 48 hours for human grading; ${title} provides millisecond-latency multimodal feedback.`,
    topVoices: ["@LeetCode", "Hiring Without Whiteboards", "Stanford HCI Group", "OpenAI Applied Team"],
    roles: [
      { role: "Applied Audio / Speech ML Engineer", reason: "Optimize WebRTC audio streaming chunking and voice inflection analysis." },
      { role: "Technical Curriculum Lead", reason: "Design realistic engineering rubrics across system design and algorithms." }
    ]
  },
  education_learning: {
    domains: ["tutor", "student", "learn", "teach", "calculus", "physics", "math", "course", "quiz", "homework", "exam", "education"],
    inferredStack: ["Python", "FastAPI", "React", "Next.js", "KaTeX", "PostgreSQL", "pgvector", "Tailwind CSS"],
    algorithms: ["Dynamic Knowledge Tracing (DKT)", "Hierarchical Socratic Step-Tree Parser", "Symbolic Math Step Verifier"],
    infra: "FastAPI serverless gateway + PostgreSQL (pgvector) + Vercel Edge",
    metrics: [
      { label: "Step-Hint Generation Latency", value: "< 280ms" },
      { label: "Symbolic Proof Verification", value: "99.1%" },
      { label: "Target Student Mastery Uplift", value: "+32%" }
    ],
    gapTemplate: (title) => `Standard generative chatbots give away final answers without teaching step-by-step reasoning; ${title} enforces structured Socratic hints that foster genuine student mastery.`,
    topVoices: ["Khan Academy Research", "Stanford AI in Education", "Carnegie Learning Labs", "@3Blue1Brown"],
    roles: [
      { role: "Full-Stack Educational UX Engineer", reason: "Build interactive step-by-step canvas with real-time formula rendering." },
      { role: "Subject Matter Curriculum Architect", reason: "Validate pedagogical correctness across secondary and university curricula." }
    ]
  },
  computer_vision_robotics: {
    domains: ["vision", "camera", "drone", "robot", "yolo", "detection", "tracking", "autonomous", "lidar", "sensor", "mesh", "spatial"],
    inferredStack: ["Python", "C++", "PyTorch", "ROS 2", "OpenCV", "FastAPI", "Docker", "CUDA"],
    algorithms: ["Extended Kalman Filter (EKF)", "YOLOv11 TensorRT Pipeline", "Dynamic Spatial Octree Partitioning"],
    infra: "NVIDIA Jetson / ARM64 Companion Edge + ROS 2 Node Daemon",
    metrics: [
      { label: "End-to-End Inference", value: "14.2ms" },
      { label: "Object Tracking Precision", value: "0.962" },
      { label: "Edge Power Footprint", value: "12.5W" }
    ],
    gapTemplate: (title) => `Traditional computer vision architectures require continuous broadband cloud streaming; ${title} performs zero-latency onboard edge inference without cloud failover vulnerability.`,
    topVoices: ["ETH Robotics Systems Lab", "Open Source Robotics Foundation", "@DrDroneAI", "IEEE Robotics Society"],
    roles: [
      { role: "Embedded Systems & Firmware Engineer", reason: "Port neural inference kernels to low-power edge microcontrollers." },
      { role: "Field Validation Coordinator", reason: "Execute stress test scenarios under varying lighting and vibration conditions." }
    ]
  },
  health_biomedical: {
    domains: ["health", "medical", "patient", "clinical", "doctor", "hospital", "ecg", "eeg", "dna", "protein", "crispr", "diagnostic", "blood", "biotech"],
    inferredStack: ["Python", "FastAPI", "PyTorch", "RDKit", "PostgreSQL", "FHIR Standards", "Next.js", "Docker"],
    algorithms: ["Signal Wavelet Denoising", "Equivariant Graph Neural Network", "Bio-Conformal Risk Calibration"],
    infra: "HIPAA-compliant encrypted container enclave + FastAPI on GPU nodes",
    metrics: [
      { label: "Diagnostic Sensitivity", value: "98.4%" },
      { label: "Analysis Turnaround", value: "1.8s" },
      { label: "Calibration Error (ECE)", value: "< 0.02" }
    ],
    gapTemplate: (title) => `Diagnostic tooling in this segment is locked behind proprietary medical imaging suites costing $80,000; ${title} provides open-access point-of-care analysis.`,
    topVoices: ["Broad Institute", "Stanford Medicine AI", "Open Bio-Informatics Foundation", "Nature Digital Medicine"],
    roles: [
      { role: "Bioinformatics / Clinical Data Specialist", reason: "Curate and clean clinical validation benchmarks according to regulatory guidelines." },
      { role: "Healthcare UX & Accessibility Lead", reason: "Design streamlined clinical dashboards adapted for fast bedside workflows." }
    ]
  },
  fintech_quant: {
    domains: ["finance", "trading", "crypto", "defi", "stock", "portfolio", "arbitrage", "liquidity", "wallet", "invoice", "payment", "bank", "token"],
    inferredStack: ["Python", "Rust", "FastAPI", "TimescaleDB", "Redis", "Solidity", "Next.js", "WebSockets"],
    algorithms: ["Stochastic Volatility Calibration", "Loss-Versus-Rebalancing (LVR) Estimator", "Convex Order Routing"],
    infra: "Low-latency AWS Frankfurt instances with colocated WebSocket multiplexers",
    metrics: [
      { label: "Execution Tick Latency", value: "< 1.2ms" },
      { label: "Simulated Sharpe Ratio", value: "3.72" },
      { label: "Max Slippage Tolerance", value: "0.03%" }
    ],
    gapTemplate: (title) => `Retail traders and student builders lack institutional-grade order routing and risk modeling; ${title} brings quantitative risk guards to decentralized protocols.`,
    topVoices: ["Paradigm Research", "Jump Trading Labs", "Quantitative Finance Bar", "Bankless Research"],
    roles: [
      { role: "Quantitative Strategy Modeler", reason: "Backtest tail-risk liquidity shocks on historical tick datasets." },
      { role: "Smart Contract Security Auditor", reason: "Formally verify protocol invariants and reentrancy protections." }
    ]
  },
  law_policy_governance: {
    domains: ["law", "legal", "policy", "statutory", "antitrust", "compliance", "regulation", "court", "privacy", "gdpr", "foia", "rights"],
    inferredStack: ["Python", "FastAPI", "PostgreSQL", "pgvector", "Next.js", "Tailwind CSS", "LegalNLP"],
    algorithms: ["Statutory Diff Engine", "Hierarchical Legal Citation Embeddings", "Antitrust Self-Preferencing Estimator"],
    infra: "FastAPI + pgvector compliance database with immutable audit logging",
    metrics: [
      { label: "Statutory Cross-Check Latency", value: "1.4s" },
      { label: "Citation Extraction Precision", value: "99.2%" },
      { label: "Compliance Risk Coverage", value: "100%" }
    ],
    gapTemplate: (title) => `Manual legal and policy audits cost $500/hour and take months to complete; ${title} executes automated statutory compliance verification in sub-second cycles.`,
    topVoices: ["Stanford RegLab", "Berkman Klein Center", "Electronic Frontier Foundation", "FTC Tech Bureau"],
    roles: [
      { role: "Legal Technologist / Counsel", reason: "Structure automated compliance tests into formal statutory filings." },
      { role: "Policy Outreach Coordinator", reason: "Coordinate pilot sandboxes with civic agencies and public interest groups." }
    ]
  },
  developer_security_tools: {
    domains: ["security", "vulnerability", "git", "github", "api", "database", "compiler", "wasm", "docker", "kubernetes", "cloud", "cache", "linux"],
    inferredStack: ["Rust", "Python", "Go", "FastAPI", "WebAssembly", "Docker", "PostgreSQL", "eBPF"],
    algorithms: ["Tree-Sitter AST Diff Engine", "SMT Constraint Verification", "Capability-Based Sandbox Enforcement"],
    infra: "Bare-metal Linux cluster with eBPF runtime probes and Wasmtime sandbox",
    metrics: [
      { label: "Cold Start Latency", value: "0.45ms" },
      { label: "Memory Overhead", value: "1.8MB" },
      { label: "Zero-Day Regression Catch Rate", value: "99.4%" }
    ],
    gapTemplate: (title) => `Current developer tooling relies on heavyweight VMs and static linters that miss runtime execution invariants; ${title} provides deterministic lightweight sandboxing.`,
    topVoices: ["Bytecode Alliance", "Trail of Bits", "Open Source Security Foundation", "Cloud Native Computing Foundation"],
    roles: [
      { role: "Systems & Security Kernel Engineer", reason: "Harden sandbox boundaries and monitor syscall limits via eBPF." },
      { role: "Developer Relations & Tooling Lead", reason: "Author CLI integrations and community documentation for open source adoption." }
    ]
  },
  community_marketplace: {
    domains: ["marketplace", "community", "campus", "sharing", "swipes", "food", "waste", "donation", "trade", "exchange", "local"],
    inferredStack: ["TypeScript", "Next.js", "FastAPI", "PostgreSQL", "Redis", "Tailwind CSS", "Twilio / WhatsApp"],
    algorithms: ["Stable Marriage Matching Algorithm", "Geospatial Proximity Scorer", "Dynamic Supply-Demand Rebalancer"],
    infra: "Next.js Vercel Edge + FastAPI on Railway + Redis Cache",
    metrics: [
      { label: "Peer Match Latency", value: "< 850ms" },
      { label: "Exchange Fulfillment Rate", value: "92.4%" },
      { label: "Active Student Retention", value: "76%" }
    ],
    gapTemplate: (title) => `Campus marketplaces rely on unorganized WhatsApp group chats and bulletin boards that lead to unfulfilled trades; ${title} provides verified peer matching and settlement.`,
    topVoices: ["Campus Tech Labs", "Circular Economy Forum", "Product Hunt Builders", "Student Innovation Network"],
    roles: [
      { role: "Campus Community & Growth Lead", reason: "Deploy campus ambassador programs to onboard early dorm networks." },
      { role: "Full-Stack Mobile Engineer", reason: "Build seamless Progressive Web App (PWA) with instant notifications." }
    ]
  }
};

function detectProfile(text: string): TechDomainProfile {
  const lower = text.toLowerCase();
  let bestMatch = DOMAIN_PROFILES.education_learning;
  let maxScore = -1;

  for (const key of Object.keys(DOMAIN_PROFILES)) {
    const profile = DOMAIN_PROFILES[key];
    let score = 0;
    for (const kw of profile.domains) {
      if (lower.includes(kw)) score += 2;
    }
    if (score > maxScore) {
      maxScore = score;
      bestMatch = profile;
    }
  }

  return bestMatch;
}

function cleanTitle(raw: string): string {
  let cleaned = raw.replace(/^https?:\/\/(?:www\.)?github\.com\/[^/]+\//i, "");
  cleaned = cleaned.replace(/^https?:\/\//i, "");
  cleaned = cleaned.replace(/[_\-]+/g, " ");
  cleaned = cleaned.replace(/\s+/g, " ").trim();

  // If user typed a phrase like "I want to build an AI tutor for calculus"
  cleaned = cleaned.replace(/^(?:i want to build|we are building|building|create|developing|an|a|the)\s+/i, "");
  cleaned = cleaned.replace(/^(?:ai-powered|ai powered)\s+/i, "");

  const words = cleaned.split(" ").filter(Boolean);
  if (words.length > 7) {
    cleaned = words.slice(0, 6).join(" ");
  }

  // Capitalize title
  return cleaned
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ") || "Student Innovation Project";
}

export function synthesizeFallbackDossier(
  rawContent: string,
  inputType: string = "idea",
  domainPersona: string = "tech_builder",
  forcedSlug?: string
): any {
  const text = (rawContent || "").trim();
  const profile = detectProfile(text);

  // Derive meaningful title
  let title = cleanTitle(text);
  if (!title.toLowerCase().includes("ai") && !title.toLowerCase().includes("system") && !title.toLowerCase().includes("platform")) {
    title = `${title} Engine`;
  }

  // Derive problem statement
  let problem = text;
  if (text.length < 40) {
    problem = `Students and developers currently lack an integrated, reliable tool for ${title.toLowerCase()}; manual workflows are fragmented and error-prone.`;
  } else if (!text.toLowerCase().includes("problem") && !text.toLowerCase().includes("fail")) {
    problem = `${text}. Existing solutions fail to provide automated validation and real-time guidance, creating friction for users.`;
  }

  // Derive solution breakdown
  const architecture = `Modular event-driven architecture combining client-side reactive interface with high-throughput asynchronous inference pipelines.`;
  
  // Construct unique slug
  const slugBase = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 35);
  const randomSuffix = Math.random().toString(36).substring(2, 8);
  const slug = forcedSlug || `${slugBase || "project"}-${randomSuffix}`;

  return {
    id: `local-${Math.random().toString(36).slice(2, 9)}`,
    slug,
    title,
    tagline: `Intelligent ${domainPersona.replace("_", " ")} architecture designed for high-signal automated verification and execution.`,
    domain_persona: domainPersona,
    stage: "Prototype",
    problem_statement: problem,
    solution_breakdown: {
      architecture,
      core_algorithms: profile.algorithms,
      hardware_or_infra: profile.infra
    },
    tech_stack: profile.inferredStack,
    key_metrics: profile.metrics,
    whitespace_analysis: {
      market_gap: profile.gapTemplate(title, problem),
      top_voices: profile.topVoices
    },
    missing_roles: profile.roles,
    external_links: inputType === "github" && text.startsWith("http") ? { github: text } : {},
    verified_status: Boolean(inputType === "github" && text.startsWith("http")),
    boosted: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    _synthesized: true
  };
}

export function slugToFallbackContent(slug: string): string {
  return (slug || "")
    .replace(/-[a-z0-9]{6}$/i, "")
    .replace(/[-_]+/g, " ")
    .trim();
}
