# 📡 REST API Reference & Contracts

**Base URL**: `http://localhost:8000/api/v1`  
**OpenAPI Specification**: Interactive Swagger docs available at `http://localhost:8000/docs`

---

## 1. Authentication & Session Management

All endpoints accept either an `Authorization: Bearer <JWT>` header for logged-in users or an `X-Guest-Session-ID: <UUID>` header for unauthenticated guest interactions.

### 1.1 Claim Guest Session
Binds an unauthenticated guest session's created dossiers to a newly authenticated user account upon Google OAuth login.

- **Endpoint**: `POST /auth/claim-guest`
- **Headers**: `Authorization: Bearer <JWT>`
- **Request Body**:
  ```json
  {
    "guest_session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  }
  ```
- **Response** `200 OK`:
  ```json
  {
    "status": "success",
    "claimed_dossiers_count": 1,
    "user_id": "8b9e6120-d38a-4d39-a868-cb0a463e2645",
    "credits_balance": 65
  }
  ```

---

## 2. Dossier Management (`/dossiers`)

### 2.1 Ingest Artifact (Idea / GitHub Repo / PDF)
Processes a raw artifact into a structured Proof-of-Work Dossier.

- **Endpoint**: `POST /dossiers/ingest`
- **Headers**: Optional `X-Guest-Session-ID: <UUID>`
- **Request Body**:
  ```json
  {
    "input_type": "github", // "github" | "idea" | "pdf_text"
    "raw_content": "https://github.com/pranav/autonomous-drone-swarm",
    "domain_persona": "tech_builder" // "tech_builder" | "policy_law" | "business_finance" | "design_biotech"
  }
  ```
- **Response** `201 Created`:
  ```json
  {
    "id": "18d39f40-3490-48b7-84bc-2f9ec6727271",
    "slug": "autonomous-drone-swarm-18d39f",
    "title": "Autonomous Decentralized Drone Swarm Orchestrator",
    "tagline": "Mesh-based multi-agent coordination protocol operating in zero-GPS environments",
    "domain_persona": "tech_builder",
    "problem_statement": "Search and rescue operations fail when satellite navigation is degraded.",
    "solution_breakdown": {
      "architecture": "Decentralized consensus via Raft over LoRa mesh",
      "core_algorithms": ["Distributed Kalman Filter", "Dynamic Voronoi Partitioning"],
      "hardware_integration": "PX4 Autopilot with Raspberry Pi CM4 companion"
    },
    "tech_stack": ["Rust", "ROS 2", "Python", "LoRaWAN", "FastAPI"],
    "key_metrics": [
      {"label": "Convergence Latency", "value": "12ms"},
      {"label": "Obstacle Avoidance F1", "value": "0.984"},
      {"label": "Max Swarm Nodes", "value": "32"}
    ],
    "whitespace_analysis": {
      "market_gap": "Commercial swarms rely on centralized LTE basestations which collapse during disasters.",
      "top_voices": ["@DrDroneAI", "ETH Robotics Lab", "Open Source Autopilot Foundation"]
    },
    "missing_roles": [
      {"role": "Embedded Systems Engineer", "reason": "Optimize LoRa packet serialization in C/Rust"},
      {"role": "Field Test Coordinator", "reason": "Lead outdoor FAA Part 107 test flights"}
    ],
    "verified_status": true,
    "created_at": "2026-11-15T21:30:00Z"
  }
  ```

### 2.2 Get Dossier by Slug
- **Endpoint**: `GET /dossiers/{slug}`
- **Response** `200 OK`: Full dossier object including PR assets and verification status.

### 2.3 Verify External Artifacts
Triggers an automated HTTP HEAD check on external URLs (GitHub, live demo, Figma, paper PDF) to award the **Verified Artifact** badge.
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
Generates tailored promotional copy using the specified Markdown playbook and configured tone.

- **Endpoint**: `POST /pr/generate`
- **Request Body**:
  ```json
  {
    "dossier_id": "18d39f40-3490-48b7-84bc-2f9ec6727271",
    "playbook_type": "linkedin", // "linkedin" | "instagram_reel" | "cold_pitch"
    "tone": "high_octane", // "academic" | "high_octane" | "executive"
    "target_audience": "Peer builders and early stage tech investors"
  }
  ```
- **Response** `200 OK`:
  ```json
  {
    "asset_type": "linkedin",
    "headline": "We built a decentralized 32-drone swarm that coordinates without GPS in 12ms flat.",
    "body_markdown": "Most search-and-rescue drone swarms are fragile. If cellular networks drop, they become expensive paperweights.\n\nOver the past 4 months, our team developed a decentralized consensus layer running over sub-GHz LoRa mesh...",
    "hooks": [
      "GPS jammed? Your drone swarm shouldn't care.",
      "Here is how 32 autonomous drones navigate burning forests with zero central server:"
    ],
    "suggested_tags": ["#Robotics", "#RustLang", "#MeshNetworks", "#AutonomousSystems"],
    "og_image_url": "https://assets.studentradar.dev/og/autonomous-drone-swarm-18d39f.png"
  }
  ```

### 3.2 Boost Dossier on Campus Feed
Deducts 20⚡ credits to spotlight a dossier in the campus discovery feed.
- **Endpoint**: `POST /pr/{dossier_id}/boost`
- **Response** `200 OK`:
  ```json
  {
    "status": "boosted",
    "credits_deducted": 20,
    "remaining_balance": 45,
    "boost_expires_at": "2026-11-18T21:30:00Z"
  }
  ```

---

## 4. Opportunity Radar & Briefings (`/radar`)

### 4.1 Get Daily Curated Briefing
Returns the personalized daily briefing for the specified domain persona or active dossier.

- **Endpoint**: `GET /radar/briefing?persona=tech_builder`
- **Response** `200 OK`:
  ```json
  {
    "briefing_date": "2026-11-15",
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
      "host_organization": "DARPA Innovation Office",
      "deadline": "2026-12-01T23:59:59Z",
      "match_score": 0.94,
      "why_you_match": "Your mesh consensus protocol aligns with subterranean comms requirements.",
      "networking_plan": {
        "target_stakeholders": ["Program Manager: Dr. Jane Doe", "Lead Evaluator: Col. Smith"],
        "pitch_angle": "Emphasize 12ms latency and zero-dependency on GPS relays.",
        "icebreaker_message": "Hi Dr. Doe, noticed DARPA's focus on GPS-denied coordination. We demonstrated a 32-node LoRa mesh with 12ms convergence..."
      }
    },
    "all_opportunities": [...]
  }
  ```

### 4.2 Download Calendar Event (.ics)
Generates an RFC 5545 iCalendar file for direct 1-click import into Google Calendar or Apple Calendar.
- **Endpoint**: `GET /radar/{opportunity_id}/ics`
- **Response** `200 OK`: `text/calendar; charset=utf-8`

---

## 5. Privacy-Safe Contact Network (`/network`)

### 5.1 Intersect SHA-256 Hashes
Finds active student builders matching a client-provided list of SHA-256 hashed emails.

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

### 5.2 Dispatch Project-Anchored Invite
Sends an invite to a peer linked to a specific project role or peer review request (capped at 10/day per user via Redis rate-limiting).

- **Endpoint**: `POST /network/invites/send`
- **Request Body**:
  ```json
  {
    "dossier_id": "18d39f40-3490-48b7-84bc-2f9ec6727271",
    "recipient_email_hash": "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae",
    "role_context": "Embedded Systems Engineer"
  }
  ```
- **Response** `201 Created`:
  ```json
  {
    "status": "sent",
    "invite_token": "inv_98ab7102e3b",
    "whatsapp_url": "https://wa.me/?text=Hey!%20Check%20out%20our%20new%20build%20and%20join%20the%20team:%20https://studentradar.dev/p/autonomous-drone-swarm-18d39f?ref=inv_98ab7102e3b",
    "daily_invites_remaining": 8
  }
  ```

---

## 6. Credits & Peer Reviews (`/credits`)

### 6.1 Submit Moderated Peer Review
Submits a structured review adhering to the anti-spam 3-field rubric.

- **Endpoint**: `POST /credits/review`
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
- **Validation**: Total characters across all 3 fields must exceed 80 characters.
- **Response** `201 Created`:
  ```json
  {
    "status": "review_accepted",
    "credits_awarded": 10,
    "new_balance": 55
  }
  ```

