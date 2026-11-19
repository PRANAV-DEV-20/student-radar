# ⚡ AI-Powered Student Radar & Proof-of-Work Dossier

> **Single-Player Proof-of-Work Dossier Engine + AI PR Kit + Daily Event Radar**  
> *Transform raw student projects, GitHub repos, and research PDFs into verified, publication-grade dossiers with automated PR playbooks and high-signal opportunity matchmaking.*

---

## 🌟 Executive Summary & Product Vision

Most student platforms fail because of the **empty-feed cold-start problem**: networks require millions of users before any individual gets value. 

**Student Radar inverts this dynamic through a single-player utility wedge**:
1. **Day One Utility**: A student pastes an idea, GitHub repository URL, or project PDF into the **Omni-Command Dock**. Within seconds, the platform synthesizes an **Editorial Proof-of-Work Dossier** and a complete **PR Kit** (viral LinkedIn hook, Instagram Reel storyboard, cold investor/recruiter pitch, and a 1200×630 OpenGraph launch card).
2. **Organic Discovery Engine**: Every dossier generated automatically populates the public discovery feed (`/p/[slug]`), giving peers and recruiters a verifiable record of artifacts and technical whitespace.
3. **Daily Opportunity Radar**: Celery-scheduled agents crawl hackathons, grants, fellowships, and conferences tailored to 4 domain personas (`Engineering/AI`, `Law/Policy`, `Finance/Business`, `Biotech/Design`), generating curated daily briefings, urgent deadline tickers, and automated networking playbooks.
4. **Privacy-Preserving Viral Growth**: Using client-side **SHA-256 Web Crypto hashing**, students discover campus peers with zero raw personal email addresses stored on the backend, earning **Visibility Credits (⚡)** for peer reviews and feed boosts.

---

## 🎯 One Promise, One Flow, Three Domain Packs

> **Turn any project into visibility and opportunities in 10 minutes.**

The whole product now follows a single guided loop, visible and clickable from the
[Builder Command Center](frontend/src/app/dashboard/page.tsx):

```
Understand → Position → Publish → Connect → Track → Repeat
```

| Stage | What the student sees | Where |
| :--- | :--- | :--- |
| **Understand** | Project DNA card, readiness score, source-linked reality check, claim flags, stage-aware next step | `/dossier` |
| **Position** | 9 format packs, 4 angles, 6 tones, domain-specific pre-publish safety gate | `/pr-studio` |
| **Publish** | Shareable project passport, copy-ready share text, OG card | `/p/[slug]` |
| **Connect** | One personalized email per recipient, intent templates, consent + daily cap, day 4 / day 10 nudges | `/pr-studio?tab=outreach` |
| **Track** | Reach totals, urgent deadlines, matched opportunities, source-linked signals | `/dashboard`, `/radar` |
| **Repeat** | Refine the project, re-analyze, next best action | `/dashboard` |

**Three domain packs** (`frontend/src/lib/domainPacks.ts`) replace generic personas.
Each pack owns its proof definition, channels, formats, key risk, safety rules,
opportunity types, outreach targets and preferred retrieval sources:

- **AI & Tech** — demo / repo / benchmark proof; GitHub, arXiv, HN, Product Hunt.
- **Biotech & Life Sciences** — controls, preprint, methods proof; patent-timing and health-claim guardrails; PubMed, bioRxiv, OpenAlex.
- **Law & Policy** — citation and applicability proof; "analysis, not legal advice" framing; SSRN, legislation portals, journal CFPs.

**RAG-first grounding:** similar work and opportunities come from real fetched records with links.
The model summarizes and ranks; it never invents competitors, deadlines or metrics. Claims without
evidence are flagged, and the UI says "no external records retrieved" when that is the truth.

Every card in the dashboard is a button that opens a detail drawer with the underlying work,
sources and next action — so the dashboard is a task surface, not a static chart.

---

## 🏛️ System Architecture Overview

```
                      [ USER / BROWSER (Next.js 15) ]
                                    │
    ┌───────────────────────────────┼──────────────────────────────┐
    │ Omni-Command Dock (⌘K)        │ Client Web Crypto SHA-256    │ 1-Click WhatsApp
    │ Obsidian Atelier UI           │ Privacy-Safe Peer Match      │ Deep Link (wa.me)
    └───────────────────────────────┼──────────────────────────────┘
                                    │ REST API & Server Actions
                                    ▼
                     [ FASTAPI BACKEND (Python 3.11+) ]
    ┌──────────────────────────────────────────────────────────────┐
    │ ├── /api/v1/dossiers/ingest  (Gemini Multimodal + PyMuPDF)   │
    │ ├── /api/v1/pr/generate      (Playbook Engine + Markdown)    │
    │ ├── /api/v1/radar/briefing   (Domain Personas + .ics Export) │
    │ ├── /api/v1/network/contacts (Zero-PII SHA-256 Intersect)    │
    │ └── /api/v1/credits/*        (⚡ Economy & Peer Review)     │
    └───────────────────────┬──────────────────────────────┬───────┘
                            │                              │
         Vector Search & SQL│                              │ Celery Worker / Redis
                            ▼                              ▼
             [ POSTGRESQL 16 + pgvector ]          [ BACKGROUND WORKERS ]
             • 8 Core Normalized Tables            • 5:30 AM IST Crawl
             • VECTOR(768) HNSW Indexes            • 7:00 AM IST Briefing
             • 2-Pass Deduplication (Cosine > 0.88)• Sunday 6:00 PM IST Weekly Digest
```

---

## ✨ Key Capabilities

| Capability | Technical Mechanism | User Value |
| :--- | :--- | :--- |
| **Omni-Command Ingestion** | PyMuPDF + Gemini Structured Outputs + Tavily Trend Scout | Turn a raw thought, repo, or PDF into a comprehensive dossier in <3 seconds. |
| **Obsidian Atelier Aesthetic** | `#06070B` void backdrop, luminous indigo horizon, `#F8F9FA` editorial paper card | Publication-quality visual presentation, eliminating the "noisy AI demo" look. |
| **Domain-Agnostic Personas** | Config-driven `configs/personas/*.json` | One engine powers AI/Tech, Policy/Law, Finance, and Biotech without backend modifications. |
| **3-Column PR Studio** | Markdown playbooks (`configs/playbooks/*.md`) + Gemini LLM | 1-click tailored copy for LinkedIn, Instagram Reels, and Cold Emails. |
| **Event Radar with .ics Export** | Intent/recency pipeline + Celery Beat + 2-pass deduplication (SHA-256 + pgvector >0.88) | Daily briefing of high-signal hackathons and grants with 1-click calendar sync. |
| **Unified Radar & External Intelligence** | Gemini query planning + batch rerank; Tavily-first / Exa-fallback grounded search with recency and domain locks | One feed with `Live Hackathons & Grants` / `Current News & Launches` / `Similar Builders & Discussions` tabs, freshness badges (`Posted 2d ago`, `Closes Nov 28`), and a Draft Response / PR Hook action. Root profiles, generic pages, and verification-only cards are dropped before persistence; no posts, deadlines, or metrics are invented. `POST /radar/scan-live` refreshes on demand while Celery Beat keeps daily digests. |
| **Builder Command Center** | `/dashboard` with dossier, radar, signal, and PR-reach snapshots | At-a-glance dossiers, urgent deadlines, cross-platform pulse, and anonymous engagement totals without credits UI. |
| **Privacy-Safe Peer Discovery** | Client-side `crypto.subtle.digest("SHA-256")` | Match campus contacts with zero raw PII stored in databases. |
| **Visibility Credits (⚡)** | PostgreSQL ledger balance (`+30⚡` signup, `+10⚡` review, `−20⚡` 48h boost) | Incentivizes substantive peer feedback and active discovery. |

---

## 📁 Repository Directory Structure

```plaintext
AI-powered-student-radar/
├── README.md                     # Master project overview and user guide
├── ARCHITECTURE.md              # Detailed low-level system design & data pipeline
├── DESIGN.md                    # Obsidian Atelier UI/UX design specification
├── API_DOCS.md                  # Comprehensive REST API reference & schema contracts
├── DECISIONS.md                 # Architectural Decision Records (ADRs)
├── PLAN.md                      # Phased delivery roadmap and milestone tracker
├── docker-compose.yml           # Local multi-service orchestration (Postgres, Redis, API, Web)
├── .env.example                 # Environment configuration template
│
├── backend/                     # FastAPI backend application
│   ├── Dockerfile               # Backend container definition
│   ├── requirements.txt         # Python dependencies
│   ├── app/
│   │   ├── main.py              # Application entrypoint & middleware configuration
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic v2 application settings
│   │   │   ├── database.py      # Async SQLAlchemy engine & session factory
│   │   │   └── security.py      # JWT authentication & guest session handlers
│   │   ├── models/              # SQLAlchemy 2.0 ORM models with pgvector
│   │   │   ├── user.py          # User accounts & credits balance
│   │   │   ├── dossier.py       # Project dossiers & 768-dim embeddings
│   │   │   ├── pr_asset.py      # Multi-platform PR copy & card references
│   │   │   ├── opportunity.py   # Hackathons, grants, and radar events
│   │   │   ├── briefing.py      # Curated user briefings & networking plans
│   │   │   ├── network.py       # Referral invites & contact hashes
│   │   │   └── credit.py        # Credit transaction ledger (⚡)
│   │   ├── schemas/             # Pydantic v2 validation contracts
│   │   │   ├── dossier.py       # Ingest, update, and response schemas
│   │   │   ├── pr.py            # PR generation request and response models
│   │   │   ├── radar.py         # Briefings, opportunities, and .ics export
│   │   │   └── signals.py       # External signal & builder-match contracts
│   │   │   ├── network.py       # Privacy-safe SHA-256 matching schemas
│   │   │   └── auth.py          # OAuth and guest claim schemas
│   │   ├── api/v1/              # Versioned API routes
│   │   │   ├── auth.py          # Google OAuth & guest claim conversion
│   │   │   ├── dossiers.py      # Ingest, view, and verify dossiers
│   │   │   ├── pr.py            # PR copy synthesis & launch boost
│   │   │   ├── radar.py         # Daily briefing & calendar sync
│   │   │   └── signals.py       # Cross-platform market intelligence
│   │   │   ├── network.py       # Contact matching & referral invites
│   │   │   └── credits.py       # Credit balances and peer review rewards
│   │   ├── services/            # Core business logic & AI orchestration
│   │   │   ├── gemini_client.py # Gemini multimodal, query planning & batch rerank
│   │   │   ├── radar_live_service.py # Intent/recency pipeline, gatekeeper, live scan
│   │   │   ├── ingestion_agent.py # PyMuPDF & repo parsing agent
│   │   │   ├── trend_scout.py   # Market whitespace & top voices scout
│   │   │   └── external_intelligence.py # FounderDB/IdeaBrowser/Trends/X/Reddit/Threads signals
│   │   │   ├── pr_strategist.py # Playbook loader & PR generator
│   │   │   ├── card_renderer.py # 1200x630 OpenGraph card renderer
│   │   │   ├── dedup_service.py # SHA-256 + pgvector cosine deduplicator
│   │   │   └── calendar_service.py # RFC 5545 .ics generator
│   │   └── workers/             # Celery background tasks & schedule
│   │       ├── celery_app.py    # Celery worker initialization
│   │       └── tasks.py         # Crawl, briefing, and email dispatch tasks
│   ├── configs/                 # Declarative configuration files
│   │   ├── personas/            # Domain definitions (Tech, Law, Finance, Bio)
│   │   │   ├── tech_builder.json
│   │   │   ├── policy_law.json
│   │   │   ├── business_finance.json
│   │   │   └── design_biotech.json
│   │   └── playbooks/           # PR strategies in versioned Markdown
│   │       ├── linkedin_playbook.md
│   │       ├── instagram_reel_playbook.md
│   │       └── cold_pitch_playbook.md
│   └── scripts/
│       ├── seed_dossiers.py     # 25 Cross-domain cold-start seed dossiers
│       └── init_db.py           # Database migration helper
│
└── frontend/                    # Next.js 15 App Router frontend
    ├── Dockerfile               # Production Next.js container
    ├── package.json             # NPM dependencies
    ├── tsconfig.json            # Strict TypeScript configuration
    ├── tailwind.config.ts       # Obsidian Atelier color palette & typography
    ├── next.config.ts           # Next.js configuration & image domains
    └── src/
        ├── app/                 # Next.js 15 App Router pages
        │   ├── layout.tsx       # Root layout, fonts, and global providers
        │   ├── page.tsx         # Luminous Horizon Landing Page (⌘K dock)
        │   ├── dossier/         # Screen 1: 65/35 Dossier Workspace
        │   │   └── page.tsx
        │   ├── pr-studio/       # Screen 2: 3-Column PR Studio
        │   │   └── page.tsx
        │   ├── radar/           # Screen 3: Unified Opportunity & Market Radar
        │   │   └── page.tsx
        │   ├── dashboard/       # Student Builder Command Center (no credits UI)
        │   │   └── page.tsx
        │   ├── p/[slug]/        # Screen 4: Public SSR Proof-of-Work Dossier
        │   │   └── page.tsx
        │   └── auth/            # Auth callback & guest claim modal
        │       └── page.tsx
        ├── components/          # Reusable React components
        │   ├── ui/              # Buttons, inputs, modals, cards, tabs
        │   ├── landing/         # Hero horizon, Omni-dock, 3-card fanout
        │   ├── dossier/         # Editorial paper card, Idea radar widget
        │   ├── pr/              # PR copy tabs, social card previewer
        │   ├── radar/           # Opportunity cards, networking drawer
        │   └── network/         # 3-step contact discovery & WhatsApp modal
        └── lib/                 # Shared client utilities
            ├── api.ts           # Typed API client with guest session cookies
            ├── crypto.ts        # Client-side Web Crypto SHA-256 hasher
            ├── ics.ts           # Client-side .ics calendar export helper
            └── constants.ts     # Sample presets, navigation, and badges
```

---

## 🚀 Quickstart & Installation

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/ai-powered-student-radar.git
   cd ai-powered-student-radar
   ```

2. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   # Add your GEMINI_API_KEY and other optional provider keys in .env
   ```

3. **Start all services**:
   ```bash
   docker compose up --build
   ```

4. **Access the application**:
   - **Frontend UI**: [http://localhost:3000](http://localhost:3000)
   - **Backend REST Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Database (pgvector)**: `localhost:5432`

---

### Option 2: Local Development Setup

#### Backend Setup (Python 3.11+)

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Seed sample dossiers and opportunities
python scripts/seed_dossiers.py

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup (Next.js 15 & Node 20+)

```bash
cd frontend

# Install packages
npm install

# Run development server
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) to start exploring.

---

## ⚡ Product Loops & Token Economy

```
             ┌─────────────────────────────┐
             │   1. Ingest Project / Idea  │
             └──────────────┬──────────────┘
                            │
                            ▼
             ┌─────────────────────────────┐
             │  Proof-of-Work Dossier +    │
             │   1200x630 OG Launch Card   │
             └──────────────┬──────────────┘
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
   ┌───────────────────────┐ ┌───────────────────────┐
   │  WhatsApp Deep Link   │ │   Peer Review Loop    │
   │  wa.me/?ref={token}   │ │  Review dossier (+10⚡)│
   │  New Signup = +15⚡   │ │  Boost launch   (-20⚡)│
   └───────────────────────┘ └───────────────────────┘
```

1. **Proof-of-Work Creation**: Generates an authoritative dossier and OpenGraph image, giving students an instant bragging artifact for Twitter, LinkedIn, and personal portfolios.
2. **Contact Discovery Loop**: Matches local student contacts via privacy-safe SHA-256 hashes, allowing 1-click WhatsApp invites that grant **+15⚡ credits** on signup.
3. **Peer Review Economy**: Students earn **+10⚡** for completing structured peer reviews (Strength, Bottleneck, Suggestion) and spend **-20⚡** to feature their project in the public campus spotlight.

---

## 🛡️ Privacy & Security Guarantees

- **Zero Non-User PII Stored**: Contact discovery utilizes SHA-256 hashing computed client-side using `window.crypto.subtle.digest`. The server only intersects cryptographic hashes.
- **Unauthenticated Guest Claim State**: Guests can create a complete dossier before registering. A `guest_session_id` in localStorage and HTTP-only cookies securely binds their work to their account upon Google OAuth login.
- **Dossier Link Verification**: External URLs (GitHub repositories, live deployments, Figma files) undergo automated status code checks to earn the **Verified Artifact** badge.
- **Rate-Limited Outreach**: Outbound email invitations are capped at 10/day per user via Redis token buckets to eliminate spam.

---

## 📜 Documentation Index

- [Architecture Specification (ARCHITECTURE.md)](ARCHITECTURE.md)
- [UI/UX Design Specification (DESIGN.md)](DESIGN.md)
- [REST API Reference (API_DOCS.md)](API_DOCS.md)
- [Architectural Decision Records (DECISIONS.md)](DECISIONS.md)
- [Phased Implementation Plan (PLAN.md)](PLAN.md)

---

## 📄 License
This project is licensed under the Apache 2.0 License. Built for students, builders, and innovators globally.

#   s t u d e n t - r a d a r  
 