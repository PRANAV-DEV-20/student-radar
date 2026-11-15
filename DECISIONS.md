# 🧠 Architectural Decision Records (ADRs)

This document formalizes the fundamental technical, product, and data decisions made across the **AI-Powered Student Radar** architecture.

---

## ADR 001: Single-Player Utility First, Multiplayer Network Second

### Context
Campus and student platforms repeatedly fail due to the **cold-start problem**: without an active user base, there is no content to consume, and early users immediately churn.

### Decision
Position the platform as an instant single-player utility first:
- Any student can input an unpolished project idea, GitHub link, or research paper PDF and immediately receive an **Editorial Proof-of-Work Dossier** and a ready-to-share **PR Launch Kit**.
- Every generated dossier automatically populates the public discovery feed (`/p/[slug]`), passively seeding the multiplayer network without requiring manual social posting.

### Consequences
- **Positive**: Immediate retention and viral sharing on day one; eliminates the empty-feed dilemma.
- **Negative**: Requires robust automated ingestion and high-fidelity output so users feel proud sharing the artifact.

---

## ADR 002: Domain-Agnostic Architecture via Declarative JSON Persona Configs

### Context
Hardcoding prompt schemas and query rubrics to software engineering would alienate Law, Finance, Policy, and Biotech students, fragmenting the codebase into disjointed verticals.

### Decision
Decouple all domain-specific taxonomy, search portals, ranking heuristics, and terminology into configuration files located in `configs/personas/*.json` (`tech_builder.json`, `policy_law.json`, `business_finance.json`, `design_biotech.json`).

### Schema Example:
```json
{
  "persona_id": "policy_law",
  "label": "Law, Governance & Policy",
  "trusted_portals": ["regulations.gov", "law.cornell.edu", "ssrn.com"],
  "evaluation_rubric": ["Statutory Precedent", "Regulatory Viability", "Public Impact"],
  "radar_query_templates": ["policy fellowship 2026", "legal tech hackathon", "governance grant"]
}
```

### Consequences
- **Positive**: Zero backend Python code changes required to launch new academic domains or professional tracks.
- **Negative**: Prompts must dynamically inject persona definitions, slightly increasing prompt token footprints.

---

## ADR 003: Zero ML Training Strategy via Google Gemini API & pgvector

### Context
Training, fine-tuning, and maintaining bespoke ML models for dossier synthesis and classification requires large proprietary datasets, GPU clusters, and prolonged development cycles.

### Decision
Standardize 100% of the AI layer on:
1. **Google Gemini API (`google-genai`)**:
   - Multimodal PDF & repository parsing.
   - Pydantic-enforced **Structured JSON Outputs**.
   - `text-embedding-004` (768 dimensions) for vector representations.
2. **PostgreSQL 16 + pgvector**:
   - In-database HNSW indexing (`m=16, ef_construction=64`) for cosine semantic matching.
3. **Live Search APIs (Tavily/Exa + Gemini Grounding)**:
   - Real-time market whitespace and top ecosystem voices discovery.

### Consequences
- **Positive**: Zero dataset collection required; sub-second cold-start launch; state-of-the-art multimodal reasoning.
- **Negative**: Dependency on external LLM API availability and rate limits (mitigated by asynchronous task queues).

---

## ADR 004: Client-Side SHA-256 Web Crypto Contact Discovery (Zero-PII Backend)

### Context
Matching student contact lists across campus networks traditionally requires storing raw phone numbers or email addresses, introducing immense GDPR/FERPA compliance liabilities and privacy leaks.

### Decision
Execute email address normalization and cryptographic SHA-256 hashing strictly on the client browser using the native Web Crypto API (`window.crypto.subtle.digest`):
$$\text{Hash} = \text{SHA-256}(\text{normalize}(\text{email}))$$
Only 64-character hexadecimal hashes are sent over HTTPS to the backend. The backend matches these hashes against the indexed SHA-256 hashes of registered users.

### Consequences
- **Positive**: Zero non-user personal identifiable information (PII) is ever received, processed, or persisted by the backend.
- **Negative**: Client machines must execute hashing loops, though modern browsers hash 500 contacts in $< 15\text{ms}$.

---

## ADR 005: Visual Aesthetic — "Obsidian Atelier" (#06070B Void + #F8F9FA Editorial Paper)

### Context
Standard AI product demos suffer from visual monotony (generic dark mode with saturated neon gradients), making serious academic or technical work look like toy projects.

### Decision
Adopt **Obsidian Atelier**:
- An immersive `#06070B` void canvas with a luminous violet-indigo horizon top gradient.
- Crisp `#F8F9FA` editorial paper card backgrounds for the core Proof-of-Work Dossier.
- Typography balancing modern high-contrast editorial serifs with clean mono elements for technical specs.

### Consequences
- **Positive**: Projects look like publication-grade engineering artifacts, compelling recruiters and peers to take them seriously.
- **Negative**: Requires meticulous styling of both dark (void canvas) and light (editorial paper) elements.

---

## ADR 006: Guest Session Persistence & Google OAuth Claim State Machine

### Context
Forcing students to authenticate before generating a dossier causes drop-offs. Conversely, allowing unauthenticated creation without state persistence risks losing their generated dossier after signup.

### Decision
Implement a 2-stage Guest State Machine:
1. Issue an unauthenticated `guest_session_id` stored in `localStorage` and sent via `X-Guest-Session-ID` headers.
2. Persist guest dossiers in PostgreSQL with `user_id = NULL` and a 24-hour TTL.
3. When the user connects via Google OAuth, automatically execute an atomic claim transaction:
   ```sql
   UPDATE project_dossiers 
   SET user_id = :user_id, guest_session_id = NULL 
   WHERE guest_session_id = :guest_session_id;
   ```

### Consequences
- **Positive**: Frictionless top-of-funnel conversion with zero data loss on signup.
- **Negative**: Requires periodic cleanup of abandoned guest sessions older than 24 hours.

---

## ADR 007: Tool Separation: Grounding vs. Structured JSON Extraction

### Context
Combining live Google Search Grounding with highly complex nested JSON output schemas in a single LLM request frequently leads to schema truncation or dropped reference URLs.

### Decision
Decouple grounding and synthesis into a 2-stage pipeline:
1. **Stage 1 (Grounding Fetch)**: Fetch raw search results and canonical URLs using flat schemas (`OpportunityCard(canonical_source_url, title, deadline)`).
2. **Stage 2 (Structured Synthesis)**: Pass verified text and citations into Gemini with strict Pydantic structured output models. All candidate URLs undergo an HTTP HEAD validation check before insertion.

### Consequences
- **Positive**: 100% deterministic JSON schemas and verified canonical links.
- **Negative**: Two distinct API calls for complex multi-domain crawls.

---

## ADR 008: Latency Decoupling via Progressive Ingestion States

### Context
Running multi-modal PDF parsing, structured dossier extraction, live trend scouting, and 1200×630 OpenGraph card generation synchronously takes 6–10 seconds, causing browser timeouts and UI freezes.

### Decision
Return the structured core dossier within $\sim 2.5\text{s}$ so Screen 1 renders immediately. The Trend Scout (market whitespace/top voices) and OpenGraph card generation execute as asynchronous background tasks, streaming updates to the client via polling or Server-Sent Events (SSE).

### Consequences
- **Positive**: Perceived user latency drops from $>8\text{s}$ to $<2.5\text{s}$.
- **Negative**: Client UI must handle loading skeleton states for secondary widgets.

---

## ADR 009: Anti-Spam Peer Review Rubrics & External Link Verification

### Context
Incentivizing reviews with `+10⚡` credits creates an exploit vector where malicious actors submit one-word spam reviews or link to broken repositories to farm credits.

### Decision
1. **Rubric Validation**: Reviews must submit 3 required fields (`strength`, `bottleneck`, `suggestion`) with a combined minimum character count of 80 characters.
2. **Automated Link Probing**: Dossiers claiming GitHub, Figma, or deployed URLs are checked by an asynchronous HEAD prober. Only URLs returning `200 OK` receive the emerald **Verified Artifact** badge.

### Consequences
- **Positive**: High-signal community feedback; spam accounts cannot manipulate credit reserves.
- **Negative**: Occasional false negatives if external links block automated HEAD requests (mitigated by user agent headers).

