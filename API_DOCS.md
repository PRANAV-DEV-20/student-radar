# 📡 REST API Reference & Contracts

**Base URL**: `http://localhost:8000/api/v1`  
**Interactive docs**: `http://localhost:8000/docs`

All JSON errors use FastAPI's standard shape:

```json
{ "detail": "Human-readable reason." }
```

---

## 0. Conventions & Endpoint Map

### Authentication headers

| Header | Use |
| --- | --- |
| `Authorization: Bearer <JWT>` | Authenticated user actions. |
| `X-Guest-Session-ID: <id>` | Unauthenticated dossier creation. Guest IDs are opaque strings such as `guest_ab12cd34ef`; they are **not required to be UUIDs**. |

A request may send both headers. When a valid JWT is present, the user identity wins and the guest header is ignored for ownership.

`GET /dossiers/public/{slug}` never returns `guest_session_id`; a guest session id is a claim secret and must not be exposed publicly.

### Product-spec endpoint map

| Capability | Endpoint |
| --- | --- |
| Dossier ingestion | `POST /dossiers/ingest` |
| PDF dossier upload | `POST /dossiers/ingest-file` |
| Public dossier | `GET /dossiers/{slug}` (also `GET /dossiers/public/{slug}`) |
| Public dossier view beacon | `POST /dossiers/{slug}/view` |
| Two-tier ecosystem benchmark refresh | `POST /dossiers/{slug}/benchmark/refresh` |
| Save selected V2 roadmap upgrades | `POST /dossiers/{slug}/roadmap` |
| PR playbook generation | `POST /pr/generate` |
| PR asset engagement event | `POST /pr/assets/{asset_id}/events` |
| PR reach analytics | `GET /pr/reach` |
| Daily/weekly briefing | `GET /radar/briefing` |
| On-demand live Radar scan | `POST /radar/scan-live` |
| Signal source/provider status | `GET /signals/sources` |
| External market signals | `GET /signals/market` |
| Persona switch | `POST /radar/reprofile` |
| Co-builder matchmaking | `GET /matchmaking/cobuilders/{dossier_id}` |
| Peer review credits | `POST /credits/review` |
| Visibility boost | `POST /credits/boost/{dossier_id}` (also `POST /pr/{dossier_id}/boost`) |

### Visibility Credits economy

| Action | Amount |
| --- | --- |
| New account | `+30⚡` |
| Referral signup (paid to the inviter) | `+15⚡` |
| Accepted peer review | `+10⚡` once per reviewer per dossier |
| 48-hour feed boost | `−20⚡` |

A boost expires after **48 hours**. Deadlines closing in **less than 72 hours** are returned in `urgent_deadlines`.

---

## 1. Authentication & Session Management (`/auth`)

### 1.1 Register
Creates an account, awards `30⚡`, optionally claims guest dossiers, and optionally attributes a referral invite.

- **Endpoint**: `POST /auth/register`
- **Request Body**:
  ```json
  {
    "email": "student@example.com",
    "password": "a-strong-password",
    "full_name": "Aarav Sharma",
    "campus_or_org": "IIT Bombay",
    "city": "Mumbai",
    "active_persona_id": "tech_builder",
    "verified_skills": ["Rust", "PyTorch", "ROS 2"],
    "guest_session_id": "guest_ab12cd34ef",
    "referral_token": "ref_98ab7102e3b"
  }
  ```
- **Personas accepted**: `tech_builder`, `policy_law`, `business_finance`, `design_biotech`
- **Response** `201 Created`:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user_id": "8b9e6120-d38a-4d39-a868-cb0a463e2645",
    "full_name": "Aarav Sharma",
    "email": "student@example.com",
    "credits_balance": 30
  }
  ```

> **Referral attribution:** the `+15⚡` is credited to the invite's sender, not the newly registered user. The invite row is locked during attribution so the same token can only be claimed once.

### 1.2 Login
- **Endpoint**: `POST /auth/login`
- **Request Body**:
  ```json
  {
    "email": "student@example.com",
    "password": "a-strong-password",
    "guest_session_id": "guest_ab12cd34ef"
  }
  ```
- **Response** `200 OK`: same shape as register. If `guest_session_id` is supplied, that guest's unclaimed dossiers are attached to the account.

### 1.3 Google OAuth (simulated in development)
- **Endpoint**: `POST /auth/google`
- **Request Body**:
  ```json
  {
    "id_token": "dev_simulated_google_token",
    "guest_session_id": "guest_ab12cd34ef",
    "referral_token": "ref_98ab7102e3b"
  }
  ```
- **Response** `200 OK`: same shape as register.

> The development flow maps the token to `SIMULATED_OAUTH_EMAIL`. Replace this handler with real Google ID-token verification before production.

### 1.4 Claim Guest Session
Binds unclaimed dossiers created under a guest session to the current account.

- **Endpoint**: `POST /auth/claim-guest`
- **Headers**: `Authorization: Bearer <JWT>`
- **Request Body**:
  ```json
  {
    "guest_session_id": "guest_ab12cd34ef"
  }
  ```
- **Response** `200 OK`:
  ```json
  {
    "status": "success",
    "claimed_dossiers_count": 1,
    "user_id": "8b9e6120-d38a-4d39-a868-cb0a463e2645",
    "credits_balance": 30
  }
  ```

### 1.5 Profile
- **Get profile**: `GET /auth/me`
- **Update profile**: `PATCH /auth/me`
  ```json
  {
    "full_name": "Aarav Sharma",
    "campus_or_org": "IIT Bombay",
    "city": "Mumbai",
    "active_persona_id": "business_finance",
    "verified_skills": ["Financial Modeling", "Python", "Solidity"]
  }
  ```
- **Response** `200 OK`:
  ```json
  {
    "id": "8b9e6120-d38a-4d39-a868-cb0a463e2645",
    "email": "student@example.com",
    "full_name": "Aarav Sharma",
    "avatar_url": null,
    "oauth_provider": "google",
    "campus_or_org": "IIT Bombay",
    "city": "Mumbai",
    "active_persona_id": "business_finance",
    "verified_skills": ["Financial Modeling", "Python", "Solidity"],
    "credits_balance": 30
  }
  ```
- Updating `active_persona_id` re-targets future radar briefings. Only the four known personas are accepted.

---

## 2. Dossier Management (`/dossiers`)

### 2.1 Ingest Artifact (Idea / GitHub / Figma / URL / PDF text)
Processes raw content into a structured Proof-of-Work Dossier. When Gemini is not configured, deterministic extraction is used so the endpoint still works.

- **Endpoint**: `POST /dossiers/ingest`
- **Headers**: Optional `X-Guest-Session-ID: <id>`
- **Request Body**:
  ```json
  {
    "input_type": "github",
    "raw_content": "https://github.com/pranav/autonomous-drone-swarm",
    "domain_persona": "tech_builder"
  }
  ```
- **`input_type` values**: `github` | `idea` | `pdf_text` | `pdf` | `figma` | `url`
- **Response** `201 Created`:
  ```json
  {
    "id": "18d39f40-3490-48b7-84bc-2f9ec6727271",
    "owner_id": "8b9e6120-d38a-4d39-a868-cb0a463e2645",
    "slug": "autonomous-drone-swarm-18d39f",
    "title": "Autonomous Decentralized Drone Swarm Orchestrator",
    "tagline": "Mesh-based multi-agent coordination protocol operating in zero-GPS environments",
    "domain_persona": "tech_builder",
    "domain": "tech_builder",
    "stage": "Prototype",
    "problem_statement": "Search and rescue operations fail when satellite navigation is degraded.",
    "solution_breakdown": {
      "architecture": "Decentralized consensus via Raft over LoRa mesh",
      "core_algorithms": ["Distributed Kalman Filter", "Dynamic Voronoi Partitioning"],
      "hardware_integration": "PX4 Autopilot with Raspberry Pi CM4 companion"
    },
    "tech_stack": ["Rust", "ROS 2", "Python", "LoRaWAN", "FastAPI"],
    "key_metrics": [
      { "label": "Convergence Latency", "value": "12ms" },
      { "label": "Obstacle Avoidance F1", "value": "0.984" },
      { "label": "Max Swarm Nodes", "value": "32" }
    ],
    "whitespace_analysis": {
      "market_gap": "Commercial swarms rely on centralized LTE basestations which collapse during disasters.",
      "top_voices": ["@DrDroneAI", "ETH Robotics Lab", "Open Source Autopilot Foundation"]
    },
    "trend_radar_cache": {
      "market_gap": "Commercial swarms rely on centralized LTE basestations which collapse during disasters."
    },
    "missing_roles": [
      {
        "role": "Embedded Systems Engineer",
        "reason": "Optimize LoRa packet serialization in C/Rust"
      }
    ],
    "external_links": {
      "github": "https://github.com/pranav/autonomous-drone-swarm"
    },
    "verified_links": {},
    "verified_status": false,
    "boosted": false,
    "is_boost_active": false,
    "boosted_until": null,
    "boost_expires_at": null,
    "created_at": "2026-11-15T21:30:00Z",
    "updated_at": "2026-11-15T21:30:00Z"
  }
  ```

### 2.2 Ingest PDF File
- **Endpoint**: `POST /dossiers/ingest-file`
- **Content-Type**: `multipart/form-data`
- **Fields**:
  | Field | Type | Notes |
  | --- | --- | --- |
  | `file` | file | PDF, maximum 15 MB. |
  | `domain_persona` | string | Defaults to `tech_builder`; must be a known persona. |
- **Headers**: Optional `X-Guest-Session-ID: <id>`
- **Response** `201 Created`: same dossier shape as §2.1.

### 2.3 List Dossiers
- **Endpoint**: `GET /dossiers`
- **Query parameters**:
  | Parameter | Default | Notes |
  | --- | --- | --- |
  | `domain` / `persona` | none | Filter by persona key. |
  | `limit` | `20` | 1–100. |
  | `offset` | `0` | Pagination offset. |
- Active 48-hour boosts sort first, then newest dossiers.

### 2.4 Get Dossier by Slug
- **Endpoint**: `GET /dossiers/{slug}`
- **Frontend-compatible alias**: `GET /dossiers/public/{slug}`
- **Response** `200 OK`: full dossier object. No authentication is required.

### 2.5 Refresh Ecosystem Benchmark
Re-runs the two-tier Exa + Gemini mentor scan for an existing dossier. Tier 1 searches peer/indie projects (`category="github"`); Tier 2 searches production architectures and research breakthroughs. Gemini may only organize links returned by the provider; non-allowlisted URLs are dropped. If no provider key is available, the endpoint returns an empty grounded benchmark rather than fabricating results.

- **Endpoint**: `POST /dossiers/{slug}/benchmark/refresh`
- **Response** `200 OK`: full dossier object with `benchmark_analysis`. Any previously selected roadmap upgrades are preserved.
- **404**: Dossier not found.

### 2.6 Save Roadmap Upgrades
Persists the student's selected next-stage upgrades in `benchmark_analysis.selected_upgrades` (maximum 3). No new table is used.

- **Endpoint**: `POST /dossiers/{slug}/roadmap`
- **Request Body**:
  ```json
  {
    "selected_upgrades": [
      {
        "upgrade_title": "Add ROS2 Digital Twin Simulation",
        "inspired_by": "arxiv.org",
        "reference_url": "https://arxiv.org/abs/2401.01234",
        "architectural_impact": "Lets reviewers test kinematics without hardware.",
        "difficulty": "2-Week Milestone"
      }
    ]
  }
  ```
- **Response** `200 OK`: full dossier object with the persisted selection. The PR Studio reads these items and adds a **Building in Public — Version 2.0 Roadmap** hook without inventing metrics or links.

### 2.7 Verify External Artifacts
Performs safe HTTP HEAD/GET checks on external URLs (GitHub, live demo, Figma, paper PDF). Private/loopback targets are rejected.

- **Endpoint**: `POST /dossiers/{id}/verify`
- **Response** `200 OK`:
  ```json
  {
    "dossier_id": "18d39f40-3490-48b7-84bc-2f9ec6727271",
    "verified_status": true,
    "checked_urls": {
      "github": 200,
      "demo": 200
    }
  }
  ```

---

## 3. PR Studio (`/pr`)

### 3.1 Generate PR Asset Copy
Generates copy from a Markdown playbook and tone. `platform`, `platform_type`, and `playbook_type` are accepted as aliases for compatibility.

- **Endpoint**: `POST /pr/generate`
- **Request Body**:
  ```json
  {
    "dossier_id": "18d39f40-3490-48b7-84bc-2f9ec6727271",
    "playbook_type": "linkedin",
    "tone": "high_octane",
    "target_audience": "Peer builders and early-stage tech investors",
    "target_opportunity_id": null,
    "target_opportunity_context": null
  }
  ```
- **`playbook_type`** (domain-aware format packs): `linkedin` | `instagram_reel` | `instagram_carousel` | `x_thread` | `show_hn` | `reel_script` | `cold_pitch` | `policy_brief` | `plain_explainer`
- **`tone`**: `academic` | `high_octane` | `executive` | `founder` | `storyteller` | `humble_beginner`
- **`angle`** (optional free text): problem story, build journey, result/insight or collaborator call. Passed into the generation context.
- **Response** `200 OK`:
  ```json
  {
    "asset_id": "a1f4ae4d-7ca6-4969-8ea0-737c7723bca8",
    "asset_type": "linkedin",
    "platform": "linkedin",
    "headline": "We built a decentralized 32-drone swarm that coordinates without GPS in 12ms flat.",
    "body_markdown": "Most search-and-rescue drone swarms are fragile...",
    "hooks": [
      "GPS jammed? Your drone swarm shouldn't care.",
      "Here is how 32 autonomous drones navigate burning forests with zero central server:"
    ],
    "suggested_tags": ["#Robotics", "#RustLang", "#MeshNetworks"],
    "structured_payload": {
      "headline": "We built a decentralized 32-drone swarm...",
      "body_markdown": "Most search-and-rescue drone swarms are fragile..."
    },
    "og_image_url": "https://assets.studentradar.dev/og/autonomous-drone-swarm-18d39f.png",
    "launch_card_url": "data:image/png;base64,..."
  }
  ```

### 3.2 Record a PR Asset Engagement Event
Anonymous, non-blocking beacon used by PR Studio and public dossier pages. No authentication is required.

- **Endpoint**: `POST /pr/assets/{asset_id}/events`
- **Headers**: optional `X-Guest-Session-ID: <id>`
- **Request Body**:
  ```json
  { "event_type": "view", "guest_session_id": "guest_ab12cd34ef", "metadata": {} }
  ```
- **`event_type`**: `view` | `copy` | `share` | `dossier_view`
- **Response**: `204 No Content`

### 3.3 PR Reach Analytics
Returns aggregate counts of real, recorded events. No impressions are inferred and no credits are involved.

- **Endpoint**: `GET /pr/reach`
- **Query params**: optional `dossier_id` to scope the result to one dossier.
- **Response** `200 OK`:
  ```json
  {
    "total": 2,
    "by_event_type": { "view": 1, "dossier_view": 1 },
    "dossier_views": 1,
    "asset_views": 1,
    "latest_event_at": "2026-11-19T02:39:00Z"
  }
  ```

### 3.4 Public Dossier View Beacon
- **Endpoint**: `POST /dossiers/{slug}/view`
- **Response**: `204 No Content`
- Records one `dossier_view` event for the matching dossier. The public page fires this once per mount using `navigator.sendBeacon` with a `fetch(..., { keepalive: true })` fallback.

### 3.5 Boost Dossier on Campus Feed
Charges `20⚡` and activates a **48-hour** boost. Requires authentication and dossier ownership. The dossier row is locked, so concurrent requests cannot double-charge.

- **Endpoint**: `POST /pr/{dossier_id}/boost`
- **Alias**: `POST /credits/boost/{dossier_id}`
- **Response** `200 OK`:
  ```json
  {
    "status": "boosted",
    "dossier_id": "18d39f40-3490-48b7-84bc-2f9ec6727271",
    "credits_deducted": 20,
    "remaining_balance": 10,
    "boost_expires_at": "2026-11-17T21:30:00Z"
  }
  ```
- **Errors**:
  | Status | Meaning |
  | --- | --- |
  | `400` | Insufficient credits. |
  | `403` | Caller does not own the dossier. |
  | `404` | Dossier not found. |
  | `409` | The dossier already has an active boost. |

---

## 4. Opportunity Radar & Briefings (`/radar`)

### 4.1 Get Daily or Weekly Briefing
Returns a persona-filtered briefing. If a dossier is supplied, the strongest pick is scored against its technologies, missing roles, and stage.

- **Endpoint**: `GET /radar/briefing`
- **Query parameters**:
  | Parameter | Default | Notes |
  | --- | --- | --- |
  | `persona` | user's active persona, then `tech_builder` | One of the four personas. |
  | `briefing_type` | `daily` | `daily` or `weekly`. |
  | `dossier_id` | none | UUID context for personalised scoring. |
  | `dossier_slug` | none | Slug alternative to `dossier_id`. |
- **Headers**: Optional `Authorization` and `X-Guest-Session-ID`.
- **Response** `200 OK`:
  ```json
  {
    "briefing_date": "2026-11-15",
    "briefing_type": "daily",
    "persona": "tech_builder",
    "urgent_deadlines": [
      {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "title": "Global Autonomous Robotics Hackathon 2026",
        "category": "hackathon",
        "deadline": "2026-11-18T18:00:00Z",
        "hours_remaining": 68,
        "reward_pool": "$50,000"
      }
    ],
    "strongest_pick": {
      "id": "e5f67890-abcd-1234-5678-90abcdef1234",
      "title": "DARPA Subterranean Resiliency Grant",
      "category": "grant",
      "canonical_source_url": "https://www.darpa.mil/...",
      "host_organization": "DARPA Innovation Office",
      "organizer": "DARPA",
      "deadline": "2026-12-01T23:59:59Z",
      "deadline_at": "2026-12-01T23:59:59Z",
      "city": null,
      "event_date": null,
      "description": "Funding for resilient communication systems.",
      "tags": ["robotics", "resilience"],
      "domain_personas": ["tech_builder"],
      "persona_tags": ["tech_builder"],
      "location_type": "virtual",
      "mode": "virtual",
      "reward_pool": "$2,000,000",
      "decision_metadata": {},
      "match_score": 0.94,
      "why_you_match": "Your mesh consensus protocol aligns with subterranean comms requirements.",
      "networking_plan": {
        "target_stakeholders": ["Program Manager: Dr. Jane Doe", "Lead Evaluator: Col. Smith"],
        "pitch_angle": "Emphasize 12ms latency and zero dependency on GPS relays.",
        "icebreaker_message": "Hi Dr. Doe, noticed DARPA's focus on GPS-denied coordination...",
        "conversation_starters": [
          "What latency budget matters most in your evaluation?",
          "Are you prioritising mesh resilience or power efficiency?"
        ],
        "followup_draft": "Thanks for the conversation. Here is our 32-node mesh benchmark..."
      }
    },
    "hackathons": [],
    "general_events": [],
    "all_opportunities": []
  }
  ```
- Persona filtering is strict: another persona's events are not leaked as fallback. Only opportunities tagged `global` (empty `domain_personas`) can fill a persona feed.

### 4.2 Switch Persona (Reprofile)
Updates the authenticated user's active persona and immediately builds a fresh daily briefing.

- **Endpoint**: `POST /radar/reprofile`
- **Headers**: `Authorization: Bearer <JWT>`
- **Request Body**:
  ```json
  {
    "persona_id": "policy_law"
  }
  ```
  `persona`, `persona_id`, and `active_persona_id` are accepted aliases.
- **Response** `200 OK`:
  ```json
  {
    "status": "updated",
    "persona": "policy_law",
    "active_persona_id": "policy_law",
    "briefing": { "...": "same shape as §4.1" }
  }
  ```

### 4.3 List Opportunities
- **Endpoint**: `GET /radar/opportunities`
- **Query parameters**: `persona`, `category`, `city`
  - `category=hackathon` groups `hackathon`, `hackathons`, `build_sprint`, and `build_sprints`.
  - `category=general_event` groups `general_event`, `general_events`, `event`, and `events`.
  - City filtering keeps virtual/online/remote opportunities and matching in-person cities.

### 4.4 Download Calendar Event (.ics)
Generates an RFC 5545 iCalendar file for Google Calendar / Apple Calendar.

- **Endpoint**: `GET /radar/{opportunity_id}/ics`
- **Response** `200 OK`: `text/calendar; charset=utf-8` as an attachment named `radar-event-{id}.ics`.

### 4.5 On-demand Idea → Source-backed Scan
Runs immediately when a student types an idea on `/radar`. It retrieves real
records from platform endpoints first, then ranks them; it does not invent
events, deadlines, prizes, or links. A typed `raw_idea` is authoritative and
takes precedence over a persisted dossier. The endpoint bypasses the signal
snapshot cache (`max_age_hours=0` by default) and keeps Celery Beat for daily
digests. Only records with an explicit, future registration, application, or
submission deadline are promoted to cards; event start/end dates are never used
as registration deadlines.

- **Endpoint**: `POST /radar/scan-live`
- **Headers**: Optional `Authorization`.
- **Request Body**:
  ```json
  {
    "raw_idea": "A low-cost water filter for rural households",
    "persona": "tech_builder",
    "dossier_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "intents": ["hackathons", "news", "builders"],
    "language": "en",
    "max_age_hours": 0
  }
  ```
  `dossier_slug` may replace `dossier_id`. At least one of a resolvable dossier
  or `raw_idea` is required.

- **Pipeline**:
  1. Direct, source-linked adapters query Devpost, MLH, Unstop, Luma,
     Grants.gov, Commudle discovery, and Hackalendar in parallel. Each record
     is normalised into an opportunity candidate with `source`, `source_label`,
     `source_kind`, `verification`, and `match_score` metadata. Commudle and
     Hackalendar entries are explicitly marked as non-official discovery and
     must be verified on the linked page. MLH and Luma expose event windows but no registration deadline, so their records are reported as `empty` rather than shown as actionable cards. Hackalendar rows need a real `registrationDeadline`; Commudle news rows need registration language next to the stated date.
  2. Gemini fills the slots for three fixed query templates:
     - Hackathons & Grants: `"{domain} hackathon OR buildathon registration open 2026"`
     - News & Launches: `"{core_problem_or_tech} launch OR release OR funding"`
     - Builders & Discussions: `"building {problem_statement} OR looking for {solution_type}"`
  3. Tavily (primary) / Exa (fallback) search uses `search_depth="advanced"`,
     `filter_by_published_date=true`, `include_published_date=true`, and
     `max_results=10`. Hackathons are locked to event domains, builders to
     Reddit/X/Hacker News/Indie Hackers, and news uses `topic="news"` with a
     week/month `time_range`.
  4. Root profiles, generic listing pages, search URLs, and verification
     placeholders are rejected before any database write. A single batch
     Gemini rerank scores hits 0–100 against the project summary; scores below
     65 and results in a different language are dropped. Only explicitly
     stated deadlines/publish dates are returned for freshness badges.

- **Response** `200 OK`:
  ```json
  {
    "status": "ok",
    "persona": "tech_builder",
    "language": "en",
    "max_age_hours": 0,
    "queries": [
      {
        "intent": "hackathons",
        "query": "rural water hackathon OR buildathon registration open 2026",
        "raw_results": 10,
        "actionable_after_gatekeeper": 4,
        "accepted": 2,
        "note": null
      }
    ],
    "sources": [
      {
        "source": "devpost",
        "label": "Devpost",
        "status": "ok",
        "raw_count": 12,
        "accepted_count": 2,
        "is_official": true,
        "note": null
      },
      {
        "source": "commudle",
        "label": "Commudle (news discovery)",
        "status": "empty",
        "raw_count": 5,
        "accepted_count": 0,
        "is_official": false,
        "note": "Commudle has no public event API; results are news-discovery links."
      }
    ],
    "stats": {
      "raw_results": 30,
      "actionable_after_gatekeeper": 12,
      "accepted": 5,
      "rejected": 25,
      "opportunities_inserted": 1,
      "opportunities_merged": 0,
      "duration_ms": 3120
    },
    "briefing": { "...": "same shape as §4.1, filtered to live sources" },
    "signals": [
      {
        "id": "radar-1a2b3c4d5e6f78",
        "source": "news",
        "signal_type": "news",
        "title": "Low-cost filter startup raises seed round",
        "summary": "Grounded snippet from the search provider.",
        "url": "https://news.example.com/real-article",
        "published_at": "2026-11-18T09:30:00Z",
        "relevance_score": 0.91,
        "keywords": ["water filtration"],
        "is_live": true,
        "radar_intent": "news"
      }
    ]
  }
  ```
  The refreshed `briefing` excludes legacy `is_live: false`, seed/demo/fallback,
  and mock opportunities. Verification links remain available from
  `/signals/market`, but the Radar feed itself only renders real, source-backed
  results with a next action.

---

## 5. Co-Builder Matchmaking (`/matchmaking`)

### 5.1 Rank Complementary Co-Builders
Ranks active users against a dossier's `missing_roles`. Scoring blends pgvector cosine similarity (`missing_roles_embedding` vs `skills_embedding`) with deterministic token overlap from `verified_skills` and public tech stacks. Cross-persona candidates receive a small complementarity bonus.

- **Endpoint**: `GET /matchmaking/cobuilders/{dossier_id}`
- **Query parameters**:
  | Parameter | Default | Notes |
  | --- | --- | --- |
  | `limit` | `5` | 1–20. |
- **Response** `200 OK`:
  ```json
  {
    "dossier_id": "18d39f40-3490-48b7-84bc-2f9ec6727271",
    "dossier_slug": "autonomous-drone-swarm-18d39f",
    "missing_roles": ["Embedded Systems Engineer", "Field Test Coordinator"],
    "matches": [
      {
        "user_id": "71a6e92b-31cc-408d-8a5f-1411e89cf291",
        "full_name": "Meera Iyer",
        "avatar_url": null,
        "campus_or_org": "IIT Bombay",
        "city": "Mumbai",
        "active_persona_id": "tech_builder",
        "verified_skills": ["Rust", "Embedded C", "LoRaWAN"],
        "matched_roles": ["Embedded Systems Engineer"],
        "match_score": 0.87,
        "match_reason": "Verified portfolio covers Embedded Systems Engineer using Rust, Embedded C, LoRaWAN.",
        "active_dossiers_count": 2,
        "is_connected": false
      }
    ]
  }
  ```
- The dossier owner is excluded from results.

---

## 6. Privacy-Safe Contact Network (`/network`)

### 6.1 Intersect SHA-256 Hashes
Finds active builders matching client-computed SHA-256 email hashes. Raw emails never reach the backend.

- **Endpoint**: `POST /network/contacts/match`
- **Request Body**:
  ```json
  {
    "hashes": [
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
    ]
  }
  ```
- Hashes must be lowercase 64-character SHA-256 hex digests. Opted-out addresses are excluded.
- **Response** `200 OK`:
  ```json
  {
    "matched_contacts": [
      {
        "user_id": "71a6e92b-31cc-408d-8a5f-1411e89cf291",
        "full_name": "Aarav Sharma",
        "avatar_url": "https://avatars.githubusercontent.com/u/1029384",
        "active_dossiers_count": 2,
        "is_connected": false
      }
    ]
  }
  ```

### 6.2 Dispatch Project-Anchored Invite
Creates a referral invite for a specific dossier and returns a one-click WhatsApp share URL.

- **Endpoint**: `POST /network/invites/send`
- **Headers**: `Authorization: Bearer <JWT>`
- **Request Body**:
  ```json
  {
    "dossier_id": "18d39f40-3490-48b7-84bc-2f9ec6727271",
    "recipient_email_hash": "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae",
    "role_context": "Embedded Systems Engineer"
  }
  ```
- **Rules**:
  - Maximum `10` invites per sender per UTC day.
  - A pending invite to the same recipient for the same dossier is rejected for 24 hours.
  - Self-invites and opted-out recipients are rejected.
  - Only the dossier owner may invite collaborators.
  - When the invite is later claimed at signup, the **sender** receives `+15⚡`.
- **Response** `201 Created`:
  ```json
  {
    "status": "sent",
    "invite_token": "ref_98ab7102e3b",
    "whatsapp_url": "https://wa.me/?text=Hey!%20We%20just%20published...",
    "daily_invites_remaining": 8
  }
  ```

---

## 7. Credits & Peer Reviews (`/credits`)

### 7.1 Balance
- **Endpoint**: `GET /credits/balance`
- **Headers**: `Authorization: Bearer <JWT>`
- **Response** `200 OK`:
  ```json
  {
    "user_id": "8b9e6120-d38a-4d39-a868-cb0a463e2645",
    "credits_balance": 30
  }
  ```

### 7.2 Ledger History
- **Endpoint**: `GET /credits/transactions`
- **Query parameters**: `limit` (default `50`, 1–200)
- **Response** `200 OK`:
  ```json
  {
    "user_id": "8b9e6120-d38a-4d39-a868-cb0a463e2645",
    "credits_balance": 40,
    "transactions": [
      {
        "id": "f2b1c9a0-...",
        "dossier_id": "18d39f40-3490-48b7-84bc-2f9ec6727271",
        "delta": 10,
        "reason": "review_peer",
        "metadata": {
          "rubric": {
            "strength": "...",
            "bottleneck": "...",
            "suggestion": "..."
          }
        },
        "created_at": "2026-11-15T21:45:00Z"
      }
    ]
  }
  ```

### 7.3 Submit Moderated Peer Review
Submits a structured review adhering to the anti-spam, three-field rubric.

- **Endpoint**: `POST /credits/review`
- **Headers**: `Authorization: Bearer <JWT>`
- **Request Body**:
  ```json
  {
    "dossier_id": "18d39f40-3490-48b7-84bc-2f9ec6727271",
    "rubric": {
      "strength": "The Raft consensus over LoRa demonstrates impressive low-bandwidth efficiency.",
      "bottleneck": "Packets may suffer collision when swarm scale exceeds 40 active transceivers.",
      "suggestion": "Benchmark TDMA slot scheduling rather than CSMA/CA to eliminate channel contention."
    }
  }
  ```
- **Validation**: the three fields combined must contain at least 80 characters. Each field is capped at 2,000 characters.
- **Rules**:
  - A reviewer may earn the `+10⚡` reward only once per dossier.
  - Reviewers cannot review their own dossier.
  - The duplicate rule is backed by a partial unique database index.
- **Response** `201 Created`:
  ```json
  {
    "status": "review_accepted",
    "dossier_id": "18d39f40-3490-48b7-84bc-2f9ec6727271",
    "credits_awarded": 10,
    "new_balance": 40
  }
  ```
- **Errors**:
  | Status | Meaning |
  | --- | --- |
  | `400` | Rubric or credit failure. |
  | `403` | Attempted to review your own dossier. |
  | `404` | Dossier not found. |
  | `409` | You already reviewed this dossier. |

### 7.4 Boost a Dossier
Same behaviour and response as `POST /pr/{dossier_id}/boost` (§3.2).

- **Endpoint**: `POST /credits/boost/{dossier_id}`
- **Headers**: `Authorization: Bearer <JWT>`
- **Effect**: `−20⚡`, active for 48 hours, owner-only, one active boost at a time.

---

## 8. Health & Metadata

### 8.1 Health
- **Endpoint**: `GET /health`
- **Response** `200 OK`:
  ```json
  {
    "status": "healthy",
    "app": "AI-Powered Student Radar",
    "environment": "development",
    "vector_dimensions": 768,
    "personas": ["tech_builder", "policy_law", "business_finance", "design_biotech"]
  }
  ```

### 8.2 Root
- **Endpoint**: `GET /`
- **Response** `200 OK`: API name, documentation link, and version.

### 8.3 OpenAI-compatible surface
Some local AI tooling (OpenCode providers, Ollama-compatible clients, IDE
extensions) discovers models by calling `GET /v1/models` on its configured base
URL. When that base URL points at this API, these endpoints answer the probe
and its follow-up calls instead of returning `404` on every poll. Chat requests
are mapped to the configured Gemini text model; embeddings reuse the existing
embedding service. Both use deterministic fallbacks when no API key is set.

- **Model discovery**: `GET /v1/models`
  - Response `200 OK`: `{"object": "list", "data": [{"id": ..., "object": "model", "created": 0, "owned_by": "student-radar"}, ...]}`
- **Model detail**: `GET /v1/models/{model_id}`
- **Chat completions**: `POST /v1/chat/completions`
  - Body: `{"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "Hello"}], "stream": false}`
  - Response `200 OK`: standard `chat.completion` JSON, or SSE chunks ending in `data: [DONE]` when `stream: true`.
- **Embeddings**: `POST /v1/embeddings`
  - Body: `{"input": "text"}` (or a list of strings). Returns OpenAI-shaped embedding records.

> **Note**: these routes exist for compatibility/health-check traffic. If an
> AI client is intended to talk to a different LLM provider, correct that
> client's base URL (e.g. `https://api.openai.com/v1` or the local Ollama port)
> rather than relying on this surface.

### 8.4 Cross-platform market intelligence

External signals power the **Market & Competitor Pulse** filter in the unified
Radar feed and the dashboard command center. The collector queries FounderDB,
IdeaBrowser, Tumrr, Google Trends, X, Reddit, and Threads. Grounding uses
**Tavily first**; Exa is queried only when Tavily is unconfigured, fails, or
returns no results. Results are persisted in `signal_cache` with a TTL and
refreshed by Celery Beat before the morning dashboard load.

> **No fabricated data**: without a grounding key (or when a provider fails),
> the API returns real, openable search URLs marked `is_live: false` and a
> `coverage` note. These are verification links, not scraped posts, and no
> engagement numbers are invented. `google_trends` always returns an
> exploration link because interest values require an interactive session.

Event scouting uses **Gemini Search Grounding** when `GEMINI_API_KEY` is set. A
grounded event is accepted only when its `source_url` appears in the response's
citation metadata and it has an explicitly stated future deadline. Missing
deadlines, rewards, and organisers are omitted, never inferred.

The unified Radar feed is stricter: it never renders verification-only cards.
Scheduled crawling and `POST /radar/scan-live` share the same intent/recency
pipeline, pre-DB URL gatekeeper, and batch Gemini reranker described in §4.5.
Legacy rows marked `decision_metadata.is_live: false` are hidden from
`/radar/briefing` even if an older crawl already persisted them. The
`/signals/market` endpoint still returns real exploration links with
`is_live: false` for manual verification, but the frontend Radar feed filters
them out.

- **Sources & provider status**: `GET /signals/sources`
  - Includes `grounding_providers` and `grounding_provider_order: ["tavily", "exa"]`.
- **Collect signals**: `GET /signals/market`
  - Query params: `keywords` (comma-separated), `persona`, optional `title`, `max_per_source` (1–8, default 3).
  - Serves a fresh `signal_cache` snapshot when available; otherwise collects and persists one.
  - Response `200 OK`: `keywords`, `trend_direction` (`rising` / `steady` / `emerging` / `unknown`), `trend_basis`, `summary`, `signals[]`, `similar_builders[]`, and `coverage[]`.
  - Each signal includes `source`, `signal_type`, `title`, `summary`, `url`, `published_at`, `relevance_score`, `is_live`, and optional `radar_intent`.
  - `trend_direction` is a heuristic based on the number of grounded signals, not an official Google Trends metric.

Environment flags: `ENABLE_EXTERNAL_INTELLIGENCE`,
`EXTERNAL_SIGNAL_TIMEOUT_SECONDS`, `EXTERNAL_SIGNAL_MAX_PER_SOURCE`,
`SIGNAL_CACHE_TTL_MINUTES`, `TAVILY_API_KEY`, `EXA_API_KEY`,
`GEMINI_API_KEY`, `SIGNAL_REFRESH_HOUR_IST`, `SIGNAL_REFRESH_MINUTE_IST`,
plus the Radar pipeline settings listed in `.env.example`
(`RADAR_HACKATHON_DOMAINS`, `RADAR_BUILDER_DOMAINS`,
`RADAR_TAVILY_SEARCH_DEPTH`, `RADAR_TAVILY_NEWS_TIME_RANGE`,
`RADAR_TAVILY_TIME_RANGE`, `RADAR_TAVILY_MAX_RESULTS`,
`RADAR_TAVILY_FILTER_BY_PUBLISHED_DATE`,
`RADAR_TAVILY_INCLUDE_PUBLISHED_DATE`, `RADAR_RERANK_THRESHOLD`,
`RADAR_SCAN_LANGUAGE`, `RADAR_ON_DEMAND_MAX_INTENTS`).

---

## 9. Scheduled Workflows (Celery Beat, IST)

| Job | Schedule | Behaviour |
| --- | --- | --- |
| Opportunity crawl | **05:30 IST daily** | Intent/recency pipeline for hackathons & grants only: Gemini query planning + Tavily-first / Exa-fallback grounded search, pre-DB junk gatekeeper, batch Gemini rerank. Explicit future registration/application deadlines only; event end dates are never promoted; two-pass dedup then upsert. Verification links are no longer stored in the Radar feed. |
| Signal cache refresh | **06:00 IST daily** | Refreshes persona and active-dossier market snapshots into `signal_cache`. |
| Daily user briefings | **07:00 IST daily** | Persona-ranked opportunities, `<72h` urgent deadlines, strongest pick, networking plan; persisted per user. |
| Weekly user briefings | **Sunday 18:00 IST** | Weekly strongest-pick digest. |

When `ENABLE_CELERY_DISPATCH=true`, briefing and invite email tasks are queued. The current email workers are provider-agnostic logging stubs; plug in an ESP before production.
