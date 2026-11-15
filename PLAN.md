# 🗺️ Master Implementation Plan & Milestone Roadmap

This roadmap details the 4-phase execution plan for the **AI-Powered Student Radar**, structured so each layer is verified before moving to the next.

---

## Milestone Phase Tracker

```
┌────────────────────────────────────────────────────────┐
│ Phase 1: Infrastructure, Database & Auth Foundation   │ [X] COMPLETED
├────────────────────────────────────────────────────────┤
│ Phase 2: Solo Utility Core (Ingestion + Dossier + PR)  │ [X] COMPLETED
├────────────────────────────────────────────────────────┤
│ Phase 3: Scheduled Event Radar & Multi-Domain Engine   │ [X] COMPLETED
├────────────────────────────────────────────────────────┤
│ Phase 4: Viral Growth Loops, WhatsApp & Token Economy │ [X] COMPLETED
└────────────────────────────────────────────────────────┘
```

---

## Phase 1: Infrastructure, Database & Auth Foundation

### Objectives
- Establish full containerization via `docker-compose.yml` (PostgreSQL 16 with pgvector, Redis 7, FastAPI, Next.js 15).
- Define asynchronous SQLAlchemy models and initial Alembic migrations for all 8 normalized tables with 768-dim vector embeddings.
- Implement JWT authentication with Google OAuth integration and guest session claim state machine.
- Seed database with 25 cross-domain cold-start sample dossiers.

### Deliverables
1. `docker-compose.yml` & `.env.example`
2. `backend/app/models/` (8 tables: users, project_dossiers, pr_assets, opportunities, user_briefings, referral_invites, suppressed_emails, credit_transactions)
3. `backend/app/core/` (config, database, security)
4. `backend/alembic/versions/001_initial_schema.py`
5. `backend/scripts/seed_dossiers.py` (25 seed dossiers spanning Tech, Law, Finance, and Biotech)

### Verification Criteria
- [x] `docker compose up -d postgres redis` launches with healthy status.
- [x] `alembic upgrade head` executes and creates HNSW vector index on `project_dossiers.embedding`.
- [x] `python scripts/seed_dossiers.py` successfully inserts 25 dossiers and seed opportunities.

---

## Phase 2: Solo Utility Core (Ingestion + Dossier + PR Studio)

### Objectives
- Build multi-modal ingestion pipeline supporting raw text ideas, GitHub repository URLs, and research PDFs via PyMuPDF.
- Implement Gemini structured output extraction returning Pydantic-validated dossiers in $<2.5\text{s}$.
- Develop version-controlled PR Strategist utilizing `configs/playbooks/*.md` (LinkedIn, Instagram Reels, Cold Pitch).
- Create Next.js 15 Obsidian Atelier workspace (Landing Page with Omni-Command Dock, Screen 1 Dossier Workspace 65/35 split, Screen 2 3-Column PR Studio, and SSR `/p/[slug]`).

### Deliverables
1. `backend/app/services/ingestion_agent.py` & `gemini_client.py`
2. `backend/app/services/trend_scout.py` & `pr_strategist.py`
3. `backend/app/services/card_renderer.py` (1200x630 OpenGraph card generator)
4. `backend/configs/playbooks/{linkedin,instagram_reel,cold_pitch}_playbook.md`
5. Next.js pages:
   - `frontend/src/app/page.tsx` (Hero horizon + ⌘K dock + 3-card fanout)
   - `frontend/src/app/dossier/page.tsx` (65/35 Editorial Paper Dossier)
   - `frontend/src/app/pr-studio/page.tsx` (3-Column PR copy & OG card studio)
   - `frontend/src/app/p/[slug]/page.tsx` (Public SSR proof-of-work page)

### Verification Criteria
- [x] Ingesting a GitHub URL or text prompt returns a validated dossier within 3 seconds.
- [x] PR Studio renders tailored markdown for selected playbook and tone.
- [x] `/p/[slug]` renders semantic OpenGraph metadata tags.

---

## Phase 3: Scheduled Event Radar & Multi-Domain Engine

### Objectives
- Implement domain-agnostic persona configs (`configs/personas/*.json`).
- Build radar crawler service with 2-pass deduplication:
  - Pass 1: Cryptographic SHA-256 fingerprint matching.
  - Pass 2: Semantic pgvector cosine similarity $> 0.88$.
- Configure Celery Beat scheduled tasks (5:30 AM IST crawl, 6:30 AM IST briefing generation).
- Build Next.js Screen 3 (Event Radar) with live Persona Switcher, Urgent <72h deadline strip, Strongest Pick hero card, expandable Networking Plan drawer, and 1-click RFC 5545 `.ics` export.

### Deliverables
1. `backend/configs/personas/{tech_builder,policy_law,business_finance,design_biotech}.json`
2. `backend/app/services/dedup_service.py` & `radar_engine.py`
3. `backend/app/services/calendar_service.py` (.ics generator)
4. `backend/app/workers/tasks.py` (Celery Beat scheduled routines)
5. `frontend/src/app/radar/page.tsx` (Complete Event Radar screen)

### Verification Criteria
- [x] Crawled opportunities with cosine similarity $>0.88$ are deduplicated and merged.
- [x] Clicking `.ics` export downloads a valid RFC 5545 calendar file.
- [x] "Tailor Application Pitch" successfully passes opportunity requirements into PR Studio.

---

## Phase 4: Viral Growth Loops, WhatsApp & Token Economy

### Objectives
- Implement client-side Web Crypto SHA-256 email hashing for zero-PII contact discovery.
- Build Redis rate-limited invite sender (capped at 10/day per user) with `wa.me` deep-link generation.
- Implement 3-Step Post-Dossier Contact Modal in the frontend.
- Build Visibility Credits ledger:
  - `+15⚡` for attributed signup via referral token.
  - `+10⚡` for peer reviews passing the 3-field rubric ($\ge 80$ characters).
  - `-20⚡` for launching a campus feed boost.

### Deliverables
1. `frontend/src/lib/crypto.ts` (Client Web Crypto SHA-256 hasher)
2. `backend/app/api/v1/network.py` (Contact match & invite sender)
3. `backend/app/api/v1/credits.py` (Credit ledger & peer review validator)
4. `frontend/src/components/network/ContactDiscoveryModal.tsx`
5. `frontend/src/components/network/WhatsAppShareButton.tsx`

### Verification Criteria
- [x] Contact matching inspects only 64-character SHA-256 hex strings.
- [x] Outbound invite dispatch enforces 10/day rate limit per user.
- [x] Peer reviews under 80 characters or missing rubric fields are rejected with descriptive 422 errors.
- [x] Launch boost deducts 20⚡ credits and updates the public feed priority.

