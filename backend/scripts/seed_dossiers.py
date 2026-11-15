import asyncio
import os
import sys
import uuid
import hashlib
from datetime import datetime, timezone, timedelta

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from app.core.database import Base
from app.models.user import User
from app.models.dossier import ProjectDossier
from app.models.opportunity import Opportunity
from app.services.gemini_client import gemini_service
from app.services.dedup_service import dedup_service

SAMPLE_DOSSIERS = [
    # --- TECH BUILDER (7 dossiers) ---
    {
        "title": "Autonomous Decentralized Drone Swarm Orchestrator",
        "tagline": "Mesh-based multi-agent coordination protocol operating in zero-GPS environments",
        "domain_persona": "tech_builder",
        "problem_statement": "Search and rescue operations fail when satellite navigation is degraded or jammed.",
        "solution_breakdown": {
            "architecture": "Decentralized consensus via Raft over sub-GHz LoRa mesh",
            "core_algorithms": ["Distributed Kalman Filter", "Dynamic Voronoi Partitioning"],
            "hardware_or_infra": "PX4 Autopilot with Raspberry Pi CM4 companion board"
        },
        "tech_stack": ["Rust", "ROS 2", "Python", "LoRaWAN", "FastAPI"],
        "key_metrics": [
            {"label": "Convergence Latency", "value": "12.4ms"},
            {"label": "Obstacle Avoidance F1", "value": "0.984"},
            {"label": "Max Swarm Nodes", "value": "32"}
        ],
        "whitespace_analysis": {
            "market_gap": "Commercial swarms rely on centralized LTE basestations which collapse during wildfires and disasters.",
            "top_voices": ["@DrDroneAI", "ETH Robotics Lab", "Open Source Autopilot Foundation"]
        },
        "missing_roles": [
            {"role": "Embedded Systems Engineer", "reason": "Optimize LoRa packet serialization in C/Rust"},
            {"role": "Field Test Coordinator", "reason": "Lead outdoor FAA Part 107 stress test flights"}
        ],
        "external_links": {"github": "https://github.com/student-radar/drone-swarm-mesh"},
        "verified_status": True,
        "boosted": True
    },
    {
        "title": "Sub-Millisecond Edge LLM Quantizer",
        "tagline": "Tri-state weight matrix kernel for CPU-only neural inference on low-power IoT microcontrollers",
        "domain_persona": "tech_builder",
        "problem_statement": "Edge microcontrollers cannot execute transformer attention layers due to high memory bandwidth bottlenecks.",
        "solution_breakdown": {
            "architecture": "Custom SIMD assembly kernel executing 1.58-bit ternary quantized weights",
            "core_algorithms": ["BitNet b1.58 GEMM Kernel", "Block-sparse Row Pruning"],
            "hardware_or_infra": "ARM Cortex-M55 / ESP32-S3 microcontroller"
        },
        "tech_stack": ["C++20", "ARM Assembly", "PyTorch", "Rust", "CMake"],
        "key_metrics": [
            {"label": "SRAM Footprint", "value": "340KB"},
            {"label": "Inference Speed", "value": "42 tok/s"},
            {"label": "Perplexity Degradation", "value": "< 0.08"}
        ],
        "whitespace_analysis": {
            "market_gap": "Quantization tools target Nvidia TensorRT, ignoring sub-dollar offline embedded chips.",
            "top_voices": ["TinyML Foundation", "Edge AI Research Group"]
        },
        "missing_roles": [
            {"role": "Assembly Optimization Specialist", "reason": "Hand-vectorize inner dot-products using Neon instructions"}
        ],
        "external_links": {"github": "https://github.com/student-radar/edge-llm-kernel"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Zero-Knowledge Database Query Verifier",
        "tagline": "Succinct zk-SNARK proof system verifying SQL aggregations over private multi-tenant datasets",
        "domain_persona": "tech_builder",
        "problem_statement": "Enterprises cannot verify that cloud analytics databases execute queries honestly without leaking raw client tables.",
        "solution_breakdown": {
            "architecture": "Plonky2 circuit generating proof of correct relational table JOIN and SUM execution",
            "core_algorithms": ["Polynomial IOP", "Merkle Sum Trees"],
            "hardware_or_infra": "Rust prover daemon + PostgreSQL foreign data wrapper"
        },
        "tech_stack": ["Rust", "Plonky2", "PostgreSQL", "C++", "Docker"],
        "key_metrics": [
            {"label": "Proof Generation Time", "value": "240ms"},
            {"label": "Verification Cost", "value": "1.2ms"},
            {"label": "Proof Size", "value": "48KB"}
        ],
        "whitespace_analysis": {
            "market_gap": "Current zk-query engines only handle simple key-value lookups, not complex analytical SQL.",
            "top_voices": ["Zero Knowledge Podcast", "Paradigm Research", "Cryptography Group"]
        },
        "missing_roles": [
            {"role": "Cryptographic Circuit Designer", "reason": "Implement constraint-optimized lookup tables for SQLite ops"}
        ],
        "external_links": {"github": "https://github.com/student-radar/zk-sql-verifier"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Autonomous Git Repository Vulnerability Auto-Remediator",
        "tagline": "Deterministic symbolic execution agent that writes verified regression tests before applying security patches",
        "domain_persona": "tech_builder",
        "problem_statement": "Automated security fix PRs introduce silent logic bugs because agents don't verify invariant conditions.",
        "solution_breakdown": {
            "architecture": "Tree-sitter AST delta engine combined with symbolic execution constraint solver",
            "core_algorithms": ["Z3 SMT Solver", "Mutation-Guided Test Generation"],
            "hardware_or_infra": "Ephemeral GitHub Actions runner daemon"
        },
        "tech_stack": ["Python", "Rust", "Z3 Solver", "Tree-Sitter", "FastAPI"],
        "key_metrics": [
            {"label": "Zero-Regression Pass Rate", "value": "99.1%"},
            {"label": "Time to Patch", "value": "18.3s"},
            {"label": "False Positive Suppression", "value": "94%"}
        ],
        "whitespace_analysis": {
            "market_gap": "Dependabot and Snyk alert on CVEs but cannot verify behavioral invariance post-patch.",
            "top_voices": ["GitHub Security Lab", "Trail of Bits", "OpenSSF"]
        },
        "missing_roles": [
            {"role": "Static Analysis Engineer", "reason": "Extend Tree-sitter query rules for Golang and Rust repos"}
        ],
        "external_links": {"github": "https://github.com/student-radar/security-auto-patcher"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Neuromorphic Event-Camera Optical Flow Tracker",
        "tagline": "Spiking neural network processing asynchronous microsecond photon events for supersonic vehicle stabilization",
        "domain_persona": "tech_builder",
        "problem_statement": "Traditional frame-based cameras blur at high angular velocities (> 1000 deg/sec), blinding avionics.",
        "solution_breakdown": {
            "architecture": "Event-by-event spike routing architecture directly mapped to neuromorphic silicon",
            "core_algorithms": ["Spike-Timing-Dependent Plasticity", "Temporal Contrast Maximization"],
            "hardware_or_infra": "Prophesee Metavision Sensor + Intel Loihi 2 emulator"
        },
        "tech_stack": ["Python", "C++", "PyTorch", "OpenCV", "ROS 2"],
        "key_metrics": [
            {"label": "Temporal Resolution", "value": "1.2µs"},
            {"label": "Dynamic Range", "value": "124dB"},
            {"label": "Power Consumption", "value": "85mW"}
        ],
        "whitespace_analysis": {
            "market_gap": "Frame-based computer vision pipelines max out at 120 FPS; event cameras require totally new algorithmic primitives.",
            "top_voices": ["Robotics and Perception Group", "IEEE Robotics Society"]
        },
        "missing_roles": [
            {"role": "Computer Vision Researcher", "reason": "Train low-latency SNN models on high-speed drone racing datasets"}
        ],
        "external_links": {"github": "https://github.com/student-radar/event-camera-tracker"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Decentralized Sub-GHz P2P Crisis Mesh Comms",
        "tagline": "Self-healing ad-hoc packet network with zero dependence on cell towers, satellites, or internet backbones",
        "domain_persona": "tech_builder",
        "problem_statement": "Civilian communication blackouts occur within 30 minutes of natural disasters.",
        "solution_breakdown": {
            "architecture": "Multi-hop routing protocol with cryptographic routing header obfuscation",
            "core_algorithms": ["AODV-Mesh Variant", "Diffie-Hellman Ephemeral Ratchet"],
            "hardware_or_infra": "Heltec v3 ESP32 SX1262 LoRa modules"
        },
        "tech_stack": ["C++", "FreeRTOS", "Bluetooth LE", "TypeScript", "Protobuf"],
        "key_metrics": [
            {"label": "Max Single Hop Range", "value": "14.2km"},
            {"label": "Network Self-Heal Time", "value": "1.4s"},
            {"label": "Standby Battery Life", "value": "7 days"}
        ],
        "whitespace_analysis": {
            "market_gap": "Meshtastic is hobbyist-centric; lacks structured emergency triage priority routing.",
            "top_voices": ["Crisis Telecom Group", "Disaster Relief Tech"]
        },
        "missing_roles": [
            {"role": "Mobile App Engineer", "reason": "Build React Native offline-first map sync over BLE"}
        ],
        "external_links": {"github": "https://github.com/student-radar/crisis-mesh-p2p"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Continuous WebAssembly Sandbox Orchestrator",
        "tagline": "Sub-millisecond cold start serverless micro-vm runtime with capability-based security isolation",
        "domain_persona": "tech_builder",
        "problem_statement": "Docker and gVisor containers suffer 150ms+ cold starts, rendering ephemeral AI agent tool calling sluggish.",
        "solution_breakdown": {
            "architecture": "Wasmtime engine embedded into a multi-threaded Rust scheduler with copy-on-write memory snapshots",
            "core_algorithms": ["Deterministic Memory Snapshotting", "POSIX WASI Sandbox Enforcer"],
            "hardware_or_infra": "Bare-metal Linux AMD64 / ARM64 servers"
        },
        "tech_stack": ["Rust", "WebAssembly", "WASI", "Linux eBPF", "gRPC"],
        "key_metrics": [
            {"label": "Cold Start Time", "value": "0.38ms"},
            {"label": "Memory Overhead", "value": "2.1MB"},
            {"label": "Isolation Boundary Escapes", "value": "0"}
        ],
        "whitespace_analysis": {
            "market_gap": "Cloudflare Workers is proprietary; no open-source micro-Wasm runtime tailored for autonomous agents.",
            "top_voices": ["Bytecode Alliance", "Cloud Native Computing Foundation"]
        },
        "missing_roles": [
            {"role": "Kernel / eBPF Developer", "reason": "Monitor and enforce syscall limits via eBPF probes"}
        ],
        "external_links": {"github": "https://github.com/student-radar/wasm-agent-sandbox"},
        "verified_status": True,
        "boosted": False
    },

    # --- POLICY & LAW (6 dossiers) ---
    {
        "title": "Algorithmic Antitrust & Self-Preferencing Auditor",
        "tagline": "Automated behavioral scraper detecting predatory algorithmic ranking in e-commerce and app store ecosystems",
        "domain_persona": "policy_law",
        "problem_statement": "Antitrust enforcement agencies lack empirical tools to prove algorithmic self-preferencing across millions of daily search queries.",
        "solution_breakdown": {
            "architecture": "Distributed proxy scraping cluster feeding a causal inference regression engine",
            "core_algorithms": ["Difference-in-Differences Econometric Estimator", "Synthetic Control Method"],
            "hardware_or_infra": "Automated headless browser farm with TLS fingerprint rotation"
        },
        "tech_stack": ["Python", "Playwright", "FastAPI", "Statsmodels", "PostgreSQL"],
        "key_metrics": [
            {"label": "Daily Query Audits", "value": "250,000"},
            {"label": "Causal Confidence", "value": "p < 0.001"},
            {"label": "Precedent Alignment", "value": "EU DMA & FTC Act"}
        ],
        "whitespace_analysis": {
            "market_gap": "Regulators rely on whistleblowers; this provides continuous automated evidence gathering.",
            "top_voices": ["FTC Bureau of Competition", "Open Markets Institute", "Stanford RegLab"]
        },
        "missing_roles": [
            {"role": "Antitrust Legal Analyst", "reason": "Structure empirical findings into formal FTC Section 5 complaint filings"}
        ],
        "external_links": {"github": "https://github.com/student-radar/algorithmic-antitrust-auditor"},
        "verified_status": True,
        "boosted": True
    },
    {
        "title": "Frontier AI Safety Pre-Deployment Red-Teaming Framework",
        "tagline": "Standardized statutory audit pipeline evaluating autonomous agent risk profiles against the EU AI Act",
        "domain_persona": "policy_law",
        "problem_statement": "Enterprise compliance teams cannot interpret 400+ pages of the EU AI Act into verifiable test fixtures.",
        "solution_breakdown": {
            "architecture": "Adversarial prompt generator coupled with statutory requirement translation layers",
            "core_algorithms": ["Semantic Rubric Scoring", "Automated Jailbreak Trajectory Search"],
            "hardware_or_infra": "Secure air-gapped auditing pipeline"
        },
        "tech_stack": ["Python", "FastAPI", "Next.js", "OpenAI/Gemini APIs", "Docker"],
        "key_metrics": [
            {"label": "Compliance Verification Time", "value": "12 mins"},
            {"label": "Statutory Article Coverage", "value": "100%"},
            {"label": "Adversarial Test Vectors", "value": "10,000+"}
        ],
        "whitespace_analysis": {
            "market_gap": "Existing red-teaming is qualitative; this generates auditable cryptographic compliance reports.",
            "top_voices": ["AI Safety Institute", "Center for AI Safety", "Partnership on AI"]
        },
        "missing_roles": [
            {"role": "AI Governance Fellow", "reason": "Keep audit rubrics synced with EU AI Office delegated acts"}
        ],
        "external_links": {"github": "https://github.com/student-radar/ai-act-compliance-auditor"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Municipal Civic Budget Transparency & Equity Visualizer",
        "tagline": "Automated OCR and NLP ingestion engine transforming opaque city council PDF budgets into accessible maps",
        "domain_persona": "policy_law",
        "problem_statement": "Municipal expenditure is locked inside scanned, non-searchable PDF tables, preventing community oversight.",
        "solution_breakdown": {
            "architecture": "PyMuPDF + Vision LLM extraction pipeline indexing expenditures into district GIS boundaries",
            "core_algorithms": ["Table Structure Reconstruction", "Gini Coefficient Spatial Distribution"],
            "hardware_or_infra": "Next.js Mapbox frontend + FastAPI geo-spatial backend"
        },
        "tech_stack": ["Python", "PyMuPDF", "PostGIS", "FastAPI", "Mapbox GL", "Next.js"],
        "key_metrics": [
            {"label": "PDF Ingestion Accuracy", "value": "99.4%"},
            {"label": "Municipalities Indexed", "value": "14"},
            {"label": "Discrepancies Flagged", "value": "$4.2M"}
        ],
        "whitespace_analysis": {
            "market_gap": "Open data portals only host pristine CSVs; real city budgets live in scanned PDFs.",
            "top_voices": ["Civic Tech Coalition", "Code for America", "Government Finance Officers Assoc"]
        },
        "missing_roles": [
            {"role": "Public Policy Fellow", "reason": "Liaise with local community advisory boards and city comptrollers"}
        ],
        "external_links": {"github": "https://github.com/student-radar/civic-budget-transparency"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Cross-Border Data Sovereignty & Transfer Risk Sentinel",
        "tagline": "Automated network route auditor mapping enterprise cloud egress against GDPR Chapter V transfer rules",
        "domain_persona": "policy_law",
        "problem_statement": "Multi-cloud apps unknowingly route encrypted telemetry through non-adequacy jurisdictions during cloud failover.",
        "solution_breakdown": {
            "architecture": "eBPF network packet tracker recording IP geolocation and routing autonomous systems (ASNs)",
            "core_algorithms": ["BGP Route Geolocation Mapping", "Statutory Jurisdictional Conflict Analysis"],
            "hardware_or_infra": "Kubernetes daemonset collector"
        },
        "tech_stack": ["Go", "eBPF", "Python", "ClickHouse", "React"],
        "key_metrics": [
            {"label": "Packet Inspection Overhead", "value": "< 0.2%"},
            {"label": "Jurisdictional Classification", "value": "Real-time"},
            {"label": "Regulatory Sanctions Avoided", "value": "3 High-Risk Paths"}
        ],
        "whitespace_analysis": {
            "market_gap": "Privacy officers use annual surveys; this provides real-time network telemetry auditing.",
            "top_voices": ["IAPP Privacy Bar", "EDPB", "Max Schrems / NOYB"]
        },
        "missing_roles": [
            {"role": "International Privacy Counsel", "reason": "Draft Standard Contractual Clause (SCC) automated remediation playbooks"}
        ],
        "external_links": {"github": "https://github.com/student-radar/data-sovereignty-sentinel"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Automated FOIA Request Generation & Appeal Tracker",
        "tagline": "Statutory legal drafting engine managing federal Freedom of Information Act deadlines and agency appeals",
        "domain_persona": "policy_law",
        "problem_statement": "Journalists and public researchers lose 60% of valid FOIA requests due to missed agency response statutory windows.",
        "solution_breakdown": {
            "architecture": "Statutory deadline engine with automated administrative appeal brief synthesis",
            "core_algorithms": ["Agency Exemption Classifier", "Legal Brief Template Engine"],
            "hardware_or_infra": "FastAPI + Celery email delivery worker"
        },
        "tech_stack": ["Python", "FastAPI", "PostgreSQL", "Celery", "Next.js"],
        "key_metrics": [
            {"label": "Statutory Window Compliance", "value": "100%"},
            {"label": "Successful Document Releases", "value": "84%"},
            {"label": "Time Saved Per Request", "value": "4.5 hrs"}
        ],
        "whitespace_analysis": {
            "market_gap": "MuckRock provides submission; lacks automated AI-drafted administrative appeal briefs when agencies unlawfully stall.",
            "top_voices": ["Reporters Committee for Freedom of the Press", "Electronic Frontier Foundation"]
        },
        "missing_roles": [
            {"role": "Investigative Journalism Fellow", "reason": "Test agency responsiveness across federal defense and environmental portals"}
        ],
        "external_links": {"github": "https://github.com/student-radar/foia-appeal-automation"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Copyright Fair-Use Verification & Provenance Watermark Validator",
        "tagline": "Cryptographic attribution ledger verifying training data consent and fair-use defense under US Code Title 17",
        "domain_persona": "policy_law",
        "problem_statement": "Generative model creators face multi-billion dollar class-action lawsuits due to inability to prove dataset provenance.",
        "solution_breakdown": {
            "architecture": "C2PA standard metadata verifier paired with perceptual hashing of training corpus samples",
            "core_algorithms": ["Robust Perceptual Hashes", "Four-Factor Fair Use Scorer"],
            "hardware_or_infra": "Rust parser + distributed verification index"
        },
        "tech_stack": ["Rust", "Python", "FastAPI", "PostgreSQL", "C2PA SDK"],
        "key_metrics": [
            {"label": "Attribution Verification Speed", "value": "50,000 files/sec"},
            {"label": "Provenance Collision Rate", "value": "< 10^-9"},
            {"label": "Statutory Four-Factor Fit", "value": "0.92"}
        ],
        "whitespace_analysis": {
            "market_gap": "Existing tools check watermarks; this links files directly to statutory fair-use defense parameters.",
            "top_voices": ["Creative Commons", "Content Authenticity Initiative", "Copyright Alliance"]
        },
        "missing_roles": [
            {"role": "IP Law Researcher", "reason": "Refine the four-factor fair use heuristic model based on recent 2nd Circuit rulings"}
        ],
        "external_links": {"github": "https://github.com/student-radar/fair-use-verifier"},
        "verified_status": True,
        "boosted": False
    },

    # --- BUSINESS & FINANCE (6 dossiers) ---
    {
        "title": "Cross-Venue DeFi Liquidity Sentinel & Impermanent Loss Protector",
        "tagline": "Dynamic fee curvature engine mitigating toxic order flow and loss-versus-rebalancing for liquidity providers",
        "domain_persona": "business_finance",
        "problem_statement": "Passive liquidity providers lose over $500M annually to arbitrageurs exploiting stale price curves.",
        "solution_breakdown": {
            "architecture": "Off-chain volatility oracle combined with automated on-chain dynamic spread adjuster",
            "core_algorithms": ["Loss-Versus-Rebalancing (LVR) Estimator", "Hawkes Process Jump Diffusion"],
            "hardware_or_infra": "Low-latency AWS Frankfurt instances with Flashbots private relays"
        },
        "tech_stack": ["Solidity", "Rust", "Python", "TimescaleDB", "Ethers.rs"],
        "key_metrics": [
            {"label": "LVR Reduction", "value": "34.2%"},
            {"label": "Net LP APR Boost", "value": "+6.8%"},
            {"label": "Max Slippage Tolerance", "value": "0.04%"}
        ],
        "whitespace_analysis": {
            "market_gap": "Uniswap v4 hooks allow dynamic fees, but lack quantitative volatility models that calculate optimal spreads.",
            "top_voices": ["Paradigm Research", "Jump Crypto", "Bankless"]
        },
        "missing_roles": [
            {"role": "Smart Contract Auditor", "reason": "Review EVM assembly gas optimization for the rebalancing hook"}
        ],
        "external_links": {"github": "https://github.com/student-radar/defi-liquidity-sentinel"},
        "verified_status": True,
        "boosted": True
    },
    {
        "title": "B2B SaaS Churn Predictor & Revenue Contraction Sentinel",
        "tagline": "Bayesian survival analysis engine tracking enterprise product adoption telemetry to prevent logo churn",
        "domain_persona": "business_finance",
        "problem_statement": "SaaS companies discover enterprise cancellations only during renewal calls, when it is too late to intervene.",
        "solution_breakdown": {
            "architecture": "Event-stream collector feeding an automated Bayesian time-to-event survival model",
            "core_algorithms": ["Cox Proportional Hazards Model", "Shapley Value Feature Attribution"],
            "hardware_or_infra": "Snowflake / ClickHouse telemetry pipeline + Next.js dashboard"
        },
        "tech_stack": ["Python", "ClickHouse", "FastAPI", "Lifelines", "Next.js"],
        "key_metrics": [
            {"label": "Churn Lead Time", "value": "72 Days"},
            {"label": "Precision @ Top Decile", "value": "0.89"},
            {"label": "Net Revenue Retention Impact", "value": "+4.1%"}
        ],
        "whitespace_analysis": {
            "market_gap": "Gainsight and Planhat provide rule-based alerts; this computes statistically verified decay probabilities.",
            "top_voices": ["SaaS Metrics Group", "OpenView Venture Partners", "Bessemer Cloud Index"]
        },
        "missing_roles": [
            {"role": "Enterprise Customer Success Strategist", "reason": "Design automated intervention workflows based on risk deciles"}
        ],
        "external_links": {"github": "https://github.com/student-radar/saas-churn-sentinel"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Algorithmic Supply Chain Working Capital Optimizer",
        "tagline": "Dynamic inventory discount orchestrator unlocking early invoice settlement for mid-market suppliers",
        "domain_persona": "business_finance",
        "problem_statement": "Suppliers wait 90-120 days for accounts receivable payments while bearing high interest rates on credit lines.",
        "solution_breakdown": {
            "architecture": "Multi-party auction engine matching corporate treasury excess cash with supplier working capital demands",
            "core_algorithms": ["Dynamic Discount Yield Optimization", "Default Probability Scoring"],
            "hardware_or_infra": "Cloud-native ledger with automated ACH / Wire payment triggers"
        },
        "tech_stack": ["Python", "FastAPI", "PostgreSQL", "React", "Tailwind CSS"],
        "key_metrics": [
            {"label": "Cash Conversion Cycle", "value": "-28 Days"},
            {"label": "Supplier Acceptance Rate", "value": "78%"},
            {"label": "Annualized Corporate Yield", "value": "9.4%"}
        ],
        "whitespace_analysis": {
            "market_gap": "Traditional factoring firms charge 15-25% APR; this peer-to-peer enterprise auction cuts rates in half.",
            "top_voices": ["Supply Chain Finance Forum", "Fintech Collective"]
        },
        "missing_roles": [
            {"role": "Credit Risk Modeler", "reason": "Refine mid-market default probability rating curves"}
        ],
        "external_links": {"github": "https://github.com/student-radar/working-capital-optimizer"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Real-Time Volatility Surface Arbitrage Bot",
        "tagline": "Asynchronous options order book market maker executing delta-neutral volatility smile mispricings",
        "domain_persona": "business_finance",
        "problem_statement": "Crypto options markets feature wide bid-ask spreads and severe local volatility surface dislocations.",
        "solution_breakdown": {
            "architecture": "Ultra-low-latency market data feed parser feeding an analytical implied volatility solver",
            "core_algorithms": ["SABR Model Calibration", "Black-Scholes Vectorized Root Finding"],
            "hardware_or_infra": "C++ core with async WebSocket multiplexer"
        },
        "tech_stack": ["C++20", "Rust", "Python", "Deribit API", "ZeroMQ"],
        "key_metrics": [
            {"label": "Order-to-Tick Latency", "value": "84µs"},
            {"label": "Sharpe Ratio (1 Yr)", "value": "4.12"},
            {"label": "Max Delta Exposure", "value": "< $500"}
        ],
        "whitespace_analysis": {
            "market_gap": "Institutional options market makers avoid mid-cap tokens due to liquidity risks; our model handles wide spreads.",
            "top_voices": ["Deribit Research", "Quantitative Finance Bar"]
        },
        "missing_roles": [
            {"role": "Quantitative Trader", "reason": "Calibrate jump-diffusion parameters during high-macro announcements"}
        ],
        "external_links": {"github": "https://github.com/student-radar/volatility-arbitrage-bot"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Venture Scout AI: Pre-Seed GitHub Signal Detector",
        "tagline": "Automated developer velocity crawler predicting breakout open-source projects before Hacker News indexing",
        "domain_persona": "business_finance",
        "problem_statement": "Venture scouts rely on manual Twitter/LinkedIn monitoring, discovering top technical founders weeks too late.",
        "solution_breakdown": {
            "architecture": "GitHub public archive ingestion crawler computing contributor velocity and repo star acceleration",
            "core_algorithms": ["PageRank on Developer Contribution Graphs", "Exponential Moving Star Velocity"],
            "hardware_or_infra": "Distributed worker pipeline parsing 4M daily GitHub events"
        },
        "tech_stack": ["Python", "ClickHouse", "FastAPI", "Celery", "Next.js"],
        "key_metrics": [
            {"label": "Lead Time vs Tech Blogs", "value": "24 Days"},
            {"label": "False Positive Ratio", "value": "< 12%"},
            {"label": "Repos Tracked Daily", "value": "120,000"}
        ],
        "whitespace_analysis": {
            "market_gap": "PitchBook tracks funding rounds; this tracks code commits before the entity is even incorporated.",
            "top_voices": ["Redpoint Ventures", "a16z Open Source", "Index Ventures"]
        },
        "missing_roles": [
            {"role": "Venture Scout / BD Lead", "reason": "Conduct initial outreach to high-ranking student repository authors"}
        ],
        "external_links": {"github": "https://github.com/student-radar/venture-scout-ai"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Carbon Credit Tokenization & Satellite Verification Ledger",
        "tagline": "Sentinel-2 multispectral vegetation index auditor issuing tamper-proof carbon offsets on public ledgers",
        "domain_persona": "business_finance",
        "problem_statement": "Voluntary carbon markets are crippled by phantom credits where certified forests don't physically exist.",
        "solution_breakdown": {
            "architecture": "European Space Agency satellite imagery pipeline computing normalized difference vegetation indices (NDVI)",
            "core_algorithms": ["Canopy Density Change Detection", "Biomass Carbon Stock Estimation"],
            "hardware_or_infra": "Google Earth Engine + Polygon smart contracts"
        },
        "tech_stack": ["Python", "Earth Engine API", "FastAPI", "Solidity", "PostgreSQL"],
        "key_metrics": [
            {"label": "Imagery Resolution", "value": "10m/pixel"},
            {"label": "Audit Verification Cadence", "value": "Bi-weekly"},
            {"label": "Fraudulent Credits Blocked", "value": "$12.8M"}
        ],
        "whitespace_analysis": {
            "market_gap": "Verra uses manual third-party auditors who inspect once every 3 years; this provides bi-weekly satellite audits.",
            "top_voices": ["ClimateTech VC", "World Bank Carbon Initiative"]
        },
        "missing_roles": [
            {"role": "Geospatial Data Scientist", "reason": "Calibrate cloud-masking algorithms over tropical rainforest biomes"}
        ],
        "external_links": {"github": "https://github.com/student-radar/carbon-satellite-ledger"},
        "verified_status": True,
        "boosted": False
    },

    # --- BIOTECH & DESIGN (6 dossiers) ---
    {
        "title": "Generative Protein-Ligand Complex Predictor",
        "tagline": "Equivariant graph diffusion model predicting flexible binding pocket conformations with Mol* 3D rendering",
        "domain_persona": "design_biotech",
        "problem_statement": "Rigid docking algorithms fail on induced-fit binding pockets, generating false negatives in antibiotic discovery.",
        "solution_breakdown": {
            "architecture": "SE(3)-equivariant diffusion model predicting continuous ligand translation and side-chain rotamers",
            "core_algorithms": ["Equivariant Message Passing", "Scoring by Generalized Born Surface Area"],
            "hardware_or_infra": "GPU inference cluster with Mol* interactive 3D WebGL viewer"
        },
        "tech_stack": ["PyTorch", "RDKit", "OpenMM", "FastAPI", "Three.js", "Mol*"],
        "key_metrics": [
            {"label": "Binding Pocket RMSD", "value": "1.18Å"},
            {"label": "Screening Speed", "value": "240 compounds/min"},
            {"label": "Kinase Selectivity F1", "value": "0.93"}
        ],
        "whitespace_analysis": {
            "market_gap": "Schrödinger Suite costs $50,000/seat; this democratizes state-of-the-art cofolding for university labs.",
            "top_voices": ["DeepMind Science", "Baker Lab", "Broad Institute", "Stanford Bio-X"]
        },
        "missing_roles": [
            {"role": "Medicinal Chemist", "reason": "Validate chemical synthesis feasibility and assay profiles of top candidate ligands"},
            {"role": "Biomolecular UI Designer", "reason": "Optimize Mol* 3D camera gesture controls for research presentations"}
        ],
        "external_links": {"github": "https://github.com/student-radar/protein-ligand-diffusion"},
        "verified_status": True,
        "boosted": True
    },
    {
        "title": "Accessible Spatial Eye-Tracking Communication Rig",
        "tagline": "Ultra-low-cost 120 FPS pupil glint tracker enabling non-verbal ALS patients to type via neural eye movements",
        "domain_persona": "design_biotech",
        "problem_statement": "Commercial AAC eye-trackers cost upwards of $10,000, leaving millions of ALS patients without communication tools.",
        "solution_breakdown": {
            "architecture": "3D printed ergonomic frame mounted with dual infrared cameras and an onboard Raspberry Pi Zero 2W",
            "core_algorithms": ["Dark Pupil Vector Corneal Reflection", "Predictive N-gram Keyboard Engine"],
            "hardware_or_infra": "3D printed SLS frame + USB IR illumination board ($65 total BOM)"
        },
        "tech_stack": ["Python", "C++", "OpenCV", "PyQt", "OnnxRuntime"],
        "key_metrics": [
            {"label": "Typing Speed", "value": "32 wpm"},
            {"label": "Gaze Precision", "value": "< 0.45 deg"},
            {"label": "Hardware Bill of Materials", "value": "$65"}
        ],
        "whitespace_analysis": {
            "market_gap": "Tobii Dynavox monopoly charges medical insurance $12k; this open-source rig can be fabricated at any maker space.",
            "top_voices": ["ALS Association", "Assistive Technology Industry Association", "MIT Media Lab"]
        },
        "missing_roles": [
            {"role": "Industrial Hardware Designer", "reason": "Ergonomically contour headstrap mounts for bed-bound patients"}
        ],
        "external_links": {"github": "https://github.com/student-radar/accessible-eye-tracker"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "CRISPR Off-Target Epigenetic Mutation Predictor",
        "tagline": "Transformer model trained on GUIDE-seq datasets predicting unintended double-strand breaks across diverse human genomes",
        "domain_persona": "design_biotech",
        "problem_statement": "In-silico CRISPR guide design algorithms overlook non-coding chromatin accessibility states, risking genotoxicity.",
        "solution_breakdown": {
            "architecture": "Multi-modal model combining genomic sequence transformers with ENCODE DNase-seq chromatin openness tracks",
            "core_algorithms": ["Attention-Weighted Mismatch Penalty", "Epigenetic Accessibility Cross-Attention"],
            "hardware_or_infra": "High-throughput genomic indexing database"
        },
        "tech_stack": ["PyTorch", "Biopython", "FastAPI", "PostgreSQL", "Next.js"],
        "key_metrics": [
            {"label": "Off-Target Recall", "value": "97.8%"},
            {"label": "Genome Scan Latency", "value": "4.2s"},
            {"label": "False Positive Reduction", "value": "48%"}
        ],
        "whitespace_analysis": {
            "market_gap": "Cas-OFFinder only checks linear DNA sequence; our architecture incorporates 3D chromatin accessibility.",
            "top_voices": ["Doudna Lab", "Zhang Lab", "Innovative Genomics Institute"]
        },
        "missing_roles": [
            {"role": "Computational Biologist", "reason": "Integrate single-cell ATAC-seq validation datasets from primary human T-cells"}
        ],
        "external_links": {"github": "https://github.com/student-radar/crispr-epigenetic-predictor"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Haptic VR Surgical Simulator for Orthopedic Residency",
        "tagline": "Physics-accurate bone drilling and tissue deformation haptic feedback rig for low-cost surgical training",
        "domain_persona": "design_biotech",
        "problem_statement": "Orthopedic residents train on plastic sawbones that lack accurate tactile force resistance and cortical bone transitions.",
        "solution_breakdown": {
            "architecture": "High-rate 1000Hz haptic physics loop coupled with volumetric CT-scan mesh voxelization",
            "core_algorithms": ["Finite Element Method (FEM) Soft Tissue", "Position-Based Bone Fracture Dynamics"],
            "hardware_or_infra": "Geomagic Touch haptic stylus + Meta Quest 3 headset"
        },
        "tech_stack": ["C++", "Unity", "CUDA", "OpenHaptics", "HLSL"],
        "key_metrics": [
            {"label": "Haptic Update Rate", "value": "1000Hz"},
            {"label": "Tactile Force Fidelity", "value": "±0.05N"},
            {"label": "Resident Skill Transfer Rate", "value": "+42%"}
        ],
        "whitespace_analysis": {
            "market_gap": "Surgical simulators cost $150k and sit locked in high-income university hospitals; this runs on consumer headsets.",
            "top_voices": ["American Academy of Orthopaedic Surgeons", "Surgical Innovation Lab"]
        },
        "missing_roles": [
            {"role": "Orthopedic Surgeon Advisor", "reason": "Validate force curves during pedicle screw insertion trials"}
        ],
        "external_links": {"github": "https://github.com/student-radar/haptic-surgical-sim"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Low-Cost Point-of-Care Microfluidic Pathogen Detector",
        "tagline": "Smartphone-coupled colorimetric isothermal LAMP assay reader diagnosing waterborne bacterial pathogens in 15 minutes",
        "domain_persona": "design_biotech",
        "problem_statement": "Rural clinics lack thermal cyclers and electrophoresis rigs needed for standard PCR diagnosis of cholera and E. coli.",
        "solution_breakdown": {
            "architecture": "Capillary-driven microfluidic chip with a 3D printed smartphone optical enclosure and automated turbidity analyzer",
            "core_algorithms": ["Colorimetric RGB Hue Delta Tracker", "Exponential Amplification Curve Fitting"],
            "hardware_or_infra": "3D printed optical jig + standard smartphone camera"
        },
        "tech_stack": ["Python", "OpenCV", "FastAPI", "React Native", "Fusion 360"],
        "key_metrics": [
            {"label": "Detection Time", "value": "14 mins"},
            {"label": "Limit of Detection", "value": "10 CFU/mL"},
            {"label": "Per-Test Consumable Cost", "value": "$1.20"}
        ],
        "whitespace_analysis": {
            "market_gap": "Lab PCR takes 48 hours for culture turnaround; our isothermal chip provides results right at the rural well site.",
            "top_voices": ["WHO Diagnostics Consortium", "Gates Foundation Global Health"]
        },
        "missing_roles": [
            {"role": "Microfluidics Fabrication Specialist", "reason": "Optimize PDMS soft lithography channel bonding for ambient storage"}
        ],
        "external_links": {"github": "https://github.com/student-radar/point-of-care-pathogen-detector"},
        "verified_status": True,
        "boosted": False
    },
    {
        "title": "Bio-Signal EEG Brain-Computer Interface for Wheelchair Navigation",
        "tagline": "Dry-electrode 8-channel EEG headset with spatial Riemannian geometry classifier for hands-free mobility",
        "domain_persona": "design_biotech",
        "problem_statement": "Paralyzed individuals cannot use standard joysticks, while commercial BCI headsets require conductive sticky gels.",
        "solution_breakdown": {
            "architecture": "Custom flexible PCB headset with spring-loaded gold-plated dry pins transmitting over BLE to wheelchair controller",
            "core_algorithms": ["Riemannian Covariance Manifold Classifier", "Motor Imagery Common Spatial Pattern"],
            "hardware_or_infra": "TI ADS1299 Analog Front End + motorized wheelchair CAN-bus driver"
        },
        "tech_stack": ["Python", "C", "MNE-Python", "PyQt", "Nordic nRF52"],
        "key_metrics": [
            {"label": "Intent Classification Accuracy", "value": "94.6%"},
            {"label": "Command Latency", "value": "180ms"},
            {"label": "Setup Time (No Gel)", "value": "< 45s"}
        ],
        "whitespace_analysis": {
            "market_gap": "Clinical EEG requires 30 minutes of skin abrasion and gel; this dry-pin headset slips on like a baseball cap.",
            "top_voices": ["IEEE Brain Initiative", "NeurotechX", "BCI Society"]
        },
        "missing_roles": [
            {"role": "Neuro-Engineering Researcher", "reason": "Benchmark Riemannian artifact rejection against eye-blink EMG signals"}
        ],
        "external_links": {"github": "https://github.com/student-radar/dry-eeg-wheelchair-bci"},
        "verified_status": True,
        "boosted": False
    }
]

SAMPLE_OPPORTUNITIES = [
    {
        "title": "Global Autonomous Robotics & Systems Hackathon 2026",
        "category": "hackathon",
        "canonical_source_url": "https://devpost.com/hackathons/global-autonomous-robotics-2026",
        "host_organization": "Open Robotics Foundation & DARPA Lab",
        "deadline": datetime.now(timezone.utc) + timedelta(days=2, hours=14),
        "description": "Build decentralized, mesh-resilient robotics or edge hardware systems capable of zero-GPS swarm navigation.",
        "tags": ["Robotics", "Rust", "Autonomous Systems", "Edge AI", "Mesh Networks"],
        "domain_personas": ["tech_builder"],
        "location_type": "hybrid",
        "reward_pool": "$75,000"
    },
    {
        "title": "Frontier AI Governance & Regulatory Sandbox Fellowship",
        "category": "fellowship",
        "canonical_source_url": "https://governance.ai/fellowships/2026-frontier-policy",
        "host_organization": "Center for AI Safety & European Tech Council",
        "deadline": datetime.now(timezone.utc) + timedelta(days=3, hours=8),
        "description": "12-month funded fellowship evaluating algorithmic antitrust, statutory audits, and EU AI Act compliance pipelines.",
        "tags": ["AI Policy", "Antitrust", "EU AI Act", "Civic Tech", "Regulatory Tech"],
        "domain_personas": ["policy_law"],
        "location_type": "in_person",
        "reward_pool": "$90,000 Stipend"
    },
    {
        "title": "DeFi Liquidity & Market Microstructure Builder Prize",
        "category": "grant",
        "canonical_source_url": "https://paradigm.xyz/grants/defi-microstructure-2026",
        "host_organization": "Paradigm Research Foundation",
        "deadline": datetime.now(timezone.utc) + timedelta(days=5, hours=18),
        "description": "Non-dilutive grant capital for researchers developing quantitative solutions to loss-versus-rebalancing (LVR) and toxic arbitrage.",
        "tags": ["DeFi", "Quant Finance", "Market Making", "Solidity", "TimescaleDB"],
        "domain_personas": ["business_finance"],
        "location_type": "virtual",
        "reward_pool": "$120,000"
    },
    {
        "title": "Bio-Design & Computational Therapeutics Challenge",
        "category": "hackathon",
        "canonical_source_url": "https://broadinstitute.org/innovation-prize-2026",
        "host_organization": "Broad Institute & Open Molecular Lab",
        "deadline": datetime.now(timezone.utc) + timedelta(days=1, hours=22),
        "description": "Design in-silico generative protein docking tools, accessible assistive bio-hardware, or point-of-care microfluidics.",
        "tags": ["Bioinformatics", "Diffusion Models", "Assistive Tech", "Microfluidics"],
        "domain_personas": ["design_biotech"],
        "location_type": "virtual",
        "reward_pool": "$50,000"
    },
    {
        "title": "Open Source Cyberinfrastructure Research Grant",
        "category": "grant",
        "canonical_source_url": "https://nsf.gov/funding/cyberinfrastructure-2026",
        "host_organization": "National Science Foundation (NSF)",
        "deadline": datetime.now(timezone.utc) + timedelta(days=14),
        "description": "Multi-year grant supporting student-led reproducible open-source software that accelerates scientific data pipelines.",
        "tags": ["Open Source", "High-Performance Computing", "Reproducibility"],
        "domain_personas": ["tech_builder", "policy_law", "business_finance", "design_biotech"],
        "location_type": "virtual",
        "reward_pool": "$250,000"
    }
]

async def seed():
    print(f"Connecting to database: {settings.DATABASE_URL}")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS \"vector\";")
        except Exception as e:
            print(f"Extension note: {e}")
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Check existing dossiers
        from sqlalchemy import select, func
        count_res = await session.execute(select(func.count(ProjectDossier.id)))
        existing_count = count_res.scalar() or 0
        if existing_count >= 25:
            print(f"Database already populated with {existing_count} dossiers. Seeding skipped.")
            return

        print(f"Seeding {len(SAMPLE_DOSSIERS)} cross-domain Proof-of-Work dossiers...")
        for item in SAMPLE_DOSSIERS:
            slug = f"{item['title'].lower().replace(' ', '-')[:40]}-{uuid.uuid4().hex[:6]}"
            embed_text = f"{item['title']}: {item['tagline']} {item['problem_statement']}"
            embedding = await gemini_service.generate_embedding(embed_text)

            dossier = ProjectDossier(
                slug=slug,
                title=item["title"],
                tagline=item["tagline"],
                domain_persona=item["domain_persona"],
                problem_statement=item["problem_statement"],
                solution_breakdown=item["solution_breakdown"],
                tech_stack=item["tech_stack"],
                key_metrics=item["key_metrics"],
                whitespace_analysis=item["whitespace_analysis"],
                missing_roles=item["missing_roles"],
                external_links=item.get("external_links", {}),
                verified_status=item.get("verified_status", True),
                boosted=item.get("boosted", False),
                embedding=embedding
            )
            session.add(dossier)

        print(f"Seeding {len(SAMPLE_OPPORTUNITIES)} Event Radar opportunities...")
        for opp in SAMPLE_OPPORTUNITIES:
            fingerprint = dedup_service.compute_sha256_fingerprint(opp["canonical_source_url"], opp["title"])
            opp_text = f"{opp['title']}: {opp['description']}"
            embedding = await gemini_service.generate_embedding(opp_text)

            opportunity = Opportunity(
                title=opp["title"],
                category=opp["category"],
                canonical_source_url=opp["canonical_source_url"],
                host_organization=opp["host_organization"],
                deadline=opp["deadline"],
                description=opp["description"],
                tags=opp["tags"],
                domain_personas=opp["domain_personas"],
                location_type=opp["location_type"],
                reward_pool=opp["reward_pool"],
                sha256_hash=fingerprint,
                embedding=embedding
            )
            session.add(opportunity)

        await session.commit()
        print("Database successfully seeded with 25 cross-domain dossiers and event opportunities!")

if __name__ == "__main__":
    asyncio.run(seed())

