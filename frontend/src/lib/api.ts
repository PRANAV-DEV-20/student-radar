import { synthesizeFallbackDossier, slugToFallbackContent } from "./heuristicDossier";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function getGuestSessionId(): string {
  if (typeof window === "undefined") return "server-guest-id";
  let guestId = localStorage.getItem("student_radar_guest_id");
  if (!guestId) {
    guestId = "guest_" + Math.random().toString(36).substring(2, 12) + Date.now().toString(36);
    localStorage.setItem("student_radar_guest_id", guestId);
  }
  return guestId;
}

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("student_radar_jwt");
}

export function setAuthToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("student_radar_jwt", token);
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  behavior: { noFallback?: boolean } = {},
): Promise<T> {
  const token = getAuthToken();
  const guestId = getGuestSessionId();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Guest-Session-ID": guestId,
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${API_BASE}${endpoint}`;

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      const rawDetail = errorData.detail ?? errorData;
      const detail =
        typeof rawDetail === "string" ? rawDetail : JSON.stringify(rawDetail);
      console.error(`[api] ${res.status} ${endpoint}: ${detail}`);
      throw new Error(detail || `Request failed with status ${res.status}`);
    }
    if (res.status === 204) return undefined as T;
    return await res.json();
  } catch (err: any) {
    // A bare `TypeError: Failed to fetch` is a browser network failure (backend
    // offline, CORS rejection, wrong URL, or HTTPS page calling an HTTP API).
    // Surface an actionable message instead of an opaque stack trace.
    const isNetworkFailure =
      err instanceof TypeError ||
      err?.name === "TypeError" ||
      err?.name === "AbortError";
    if (isNetworkFailure) {
      err = new Error(
        `Cannot reach the API at ${API_BASE}. Confirm the backend is running and NEXT_PUBLIC_API_URL points to it (network / CORS / mixed content). Original error: ${err.message}`,
      );
    }
    if (behavior.noFallback) {
      console.warn(`API call to ${endpoint} failed (${err.message}). No local fallback used.`);
      throw err;
    }
    console.warn(`API call to ${endpoint} failed (${err.message}). Using local fallback mock if available.`);
    return getLocalFallback<T>(endpoint, options);
  }
}

export const api = {
  ingestArtifact: (data: { input_type: string; raw_content: string; domain_persona: string }) =>
    request<any>("/dossiers/ingest", { method: "POST", body: JSON.stringify(data) }),

  getDossier: (slug: string) =>
    request<any>(`/dossiers/${slug}`),

  listDossiers: (domain?: string) =>
    request<any[]>(`/dossiers${domain ? `?domain=${domain}` : ""}`),

  verifyDossier: (id: string) =>
    request<any>(`/dossiers/${id}/verify`, { method: "POST" }),

  trackDossierView: (slug: string) =>
    request<any>(`/dossiers/${slug}/view`, { method: "POST" }),

  refreshDossierBenchmark: (slug: string) =>
    request<any>(`/dossiers/${encodeURIComponent(slug)}/benchmark/refresh`, { method: "POST" }),

  saveDossierRoadmap: (slug: string, selectedUpgrades: any[]) =>
    request<any>(`/dossiers/${encodeURIComponent(slug)}/roadmap`, {
      method: "POST",
      body: JSON.stringify({ selected_upgrades: selectedUpgrades }),
    }),

  trackAssetEvent: (assetId: string, eventType: "view" | "copy" | "share" | "dossier_view") =>
    request<any>(`/pr/assets/${assetId}/events`, {
      method: "POST",
      body: JSON.stringify({ event_type: eventType }),
    }),

  getPRReach: (dossierId?: string) =>
    request<any>(`/pr/reach${dossierId ? `?dossier_id=${dossierId}` : ""}`),

  generatePR: (data: {
    dossier_id: string;
    playbook_type: string;
    tone: string;
    target_audience?: string;
    target_opportunity_context?: string;
    angle?: string;
  }) => request<any>("/pr/generate", { method: "POST", body: JSON.stringify(data) }),

  boostDossier: (dossierId: string) =>
    request<any>(`/pr/${dossierId}/boost`, { method: "POST" }),

  getRadarBriefing: (persona: string = "tech_builder") =>
    request<any>(`/radar/briefing?persona=${persona}`, {}, { noFallback: true }),

  scanLiveRadar: (data: {
    raw_idea?: string;
    persona: string;
    dossier_id?: string;
    dossier_slug?: string;
    intents?: Array<"hackathons" | "news" | "builders" | "events" | "grants" | "trends" | "opportunities">;
    language?: string;
    max_age_hours?: number;
  }) => request<any>(
    "/radar/scan-live",
    { method: "POST", body: JSON.stringify(data) },
    { noFallback: true },
  ),

  getMarketIntelligence: (
    keywords: string[],
    persona: string = "tech_builder",
    title?: string,
  ) => {
    const params = new URLSearchParams({
      keywords: keywords.join(","),
      persona,
    });
    if (title) params.set("title", title);
    return request<any>(`/signals/market?${params.toString()}`);
  },

  matchContacts: (hashes: string[]) =>
    request<any>("/network/contacts/match", { method: "POST", body: JSON.stringify({ hashes }) }),

  sendInvite: (data: { dossier_id: string; recipient_email_hash: string; role_context?: string }) =>
    request<any>("/network/invites/send", { method: "POST", body: JSON.stringify(data) }),

  submitPeerReview: (data: { dossier_id: string; rubric: { strength: string; bottleneck: string; suggestion: string } }) =>
    request<any>("/credits/review", { method: "POST", body: JSON.stringify(data) }),

  claimGuestSession: (guest_session_id: string) =>
    request<any>("/auth/claim-guest", { method: "POST", body: JSON.stringify({ guest_session_id }) }),

  googleAuth: (guest_session_id?: string) =>
    request<any>("/auth/google", { method: "POST", body: JSON.stringify({ id_token: "simulated_token", guest_session_id }) })
};

/**
 * Build PR copy from locally cached dossier content without calling the API.
 * Used when there is no persisted dossier UUID yet (e.g. ingest fell back to
 * a client-side mock), which would otherwise produce a 422 on /pr/generate.
 */
export function generatePRLocalFallback(data: Record<string, any>): any {
  return getLocalFallback<any>("/pr/generate", { body: JSON.stringify(data) });
}

// ==========================================
// High-Fidelity Client-Side Fallback Engine
// ==========================================
function readStoredDossier(slug?: string): any | null {
  if (typeof window === "undefined") return null;
  const keys = ["current_dossier", "student_radar_last_dossier"];
  for (const storage of [sessionStorage, localStorage]) {
    for (const key of keys) {
      try {
        const raw = storage.getItem(key);
        if (!raw) continue;
        const dossier = JSON.parse(raw);
        if (!dossier?.title || !dossier?.slug) continue;
        if (!slug || dossier.slug === slug) return dossier;
      } catch {
        // Ignore malformed cached records and keep looking.
      }
    }
  }
  return null;
}

function getLocalFallback<T>(endpoint: string, options: RequestInit): T {
  let reqBody: any = {};
  try {
    reqBody = options.body ? JSON.parse(options.body as string) : {};
  } catch {
    reqBody = {};
  }

  if (endpoint.includes("/dossiers/ingest")) {
    // Never return a fixed demo project here: the preview must contain the
    // student's own concept so the offline flow still feels like a generator.
    return synthesizeFallbackDossier(
      reqBody.raw_content || "",
      reqBody.input_type || "idea",
      reqBody.domain_persona || "tech_builder",
    ) as T;
  }

  if (endpoint.includes("/auth/google")) {
    return {
      access_token: "demo_local_token",
      token_type: "bearer",
      user_id: "demo-user",
      full_name: "Student Builder",
      email: "student@example.com",
      credits_balance: 30,
      is_new_user: false,
    } as unknown as T;
  }

  if (endpoint.includes("/auth/claim-guest")) {
    return {
      status: "claimed",
      guest_session_id: reqBody.guest_session_id || "guest_local",
    } as unknown as T;
  }

  if (endpoint.includes("/dossiers/") && endpoint.includes("/verify")) {
    const id = endpoint.split("/").filter(Boolean)[1] || "unknown";
    return {
      dossier_id: id,
      verified_status: false,
      checked_urls: {},
      message: "Verification queued locally.",
    } as unknown as T;
  }

  const publicMatch = endpoint.match(/^\/dossiers\/public\/([^/?]+)/);
  const detailMatch = endpoint.match(/^\/dossiers\/([^/?]+)$/);
  if (publicMatch || detailMatch) {
    const slug = decodeURIComponent((publicMatch?.[1] || detailMatch?.[1]) as string);
    const cached = readStoredDossier(slug);
    if (cached) return cached as T;
    return synthesizeFallbackDossier(
      slugToFallbackContent(slug),
      "idea",
      "tech_builder",
      slug,
    ) as T;
  }

  if (endpoint.includes("/benchmark/refresh")) {
    const cached = readStoredDossier();
    return {
      ...(cached || {}),
      benchmark_analysis: cached?.benchmark_analysis || null,
    } as unknown as T;
  }

  if (endpoint.includes("/roadmap")) {
    const cached = readStoredDossier();
    return {
      ...(cached || {}),
      benchmark_analysis: {
        ...(cached?.benchmark_analysis || {}),
        selected_upgrades: reqBody.selected_upgrades || [],
      },
    } as unknown as T;
  }

  if (endpoint.startsWith("/dossiers")) {
    const cached = readStoredDossier();
    return (cached ? [cached] : []) as unknown as T;
  }

  if (endpoint.startsWith("/pr/reach")) {
    return {
      total: 0,
      by_event_type: {},
      dossier_views: 0,
      asset_views: 0,
      latest_event_at: null,
    } as unknown as T;
  }

  if (endpoint.includes("/pr/generate")) {
    const cached = readStoredDossier();
    const title = cached?.title || "Your project";
    const tagline = cached?.tagline || "A student-built proof-of-work project";
    const stack = (cached?.tech_stack || []).slice(0, 4).join(", ") || "the submitted stack";
    const metrics = (cached?.key_metrics || [])
      .slice(0, 2)
      .map((metric: any) => `${metric.label}: ${metric.value}`)
      .join(" | ");
    const problem = cached?.problem_statement || "a concrete workflow gap";
    const context = reqBody.target_opportunity_context
      ? `Context to answer: ${reqBody.target_opportunity_context}`
      : "";
    const selectedUpgrades = cached?.benchmark_analysis?.selected_upgrades || [];
    const roadmap = selectedUpgrades.length
      ? [
          "Building in Public — Version 2.0 Roadmap:",
          ...selectedUpgrades
            .slice(0, 3)
            .map((upgrade: any, index: number) => `${index + 1}. ${upgrade.upgrade_title || "Next-stage upgrade"}`),
        ].join("\n")
      : "";

    const format = String(reqBody.playbook_type || "linkedin");
    const slug = cached?.slug || "project";
    const detail = metrics ? `Evidence: ${metrics}.` : "Evidence: not yet attached — describe a run or add a demo link before posting.";
    const limitation = "What is not shown yet: state the current limitation before publishing.";
    const angle = reqBody.angle ? `Angle: ${reqBody.angle}.` : "";
    const shared = [angle, context, roadmap].filter(Boolean).join(" ");

    const formatBody: Record<string, string> = {
      linkedin: [
        `Most teams still struggle with ${problem}`,
        "",
        `We built ${title}. ${tagline}.`,
        "",
        `Core stack: ${stack}.`,
        detail,
        limitation,
        shared,
        "",
        `Full dossier: /p/${slug}`,
      ].filter(Boolean).join("\n"),
      instagram_carousel: [
        "CAPTION",
        `Most people overlook ${problem}.`,
        `We built ${title} — ${tagline}.`,
        detail,
        "What would you change first?",
        "#studentbuilders #buildinpublic",
        "",
        "SLIDE-BY-SLIDE",
        `Slide 1: ${problem.slice(0, 90)}`,
        `Slide 2: Built for students working on ${tagline.slice(0, 70)}`,
        `Slide 3: ${title} — what it does`,
        `Slide 4: How it works: ${stack}`,
        `Slide 5: ${detail}`,
        `Slide 6: ${limitation}`,
        `Slide 7: Feedback wanted — /p/${slug}`,
        shared,
      ].filter(Boolean).join("\n"),
      x_thread: [
        `1/ ${problem.slice(0, 200)}`,
        `2/ We built ${title} to address it.`,
        `3/ Who it helps: ${tagline.slice(0, 160)}`,
        `4/ How it works: ${stack}.`,
        `5/ ${detail}`,
        `6/ ${limitation}`,
        `7/ Building in public: /p/${slug}. One specific question: does this match a problem you have?`,
        shared,
      ].filter(Boolean).join("\n"),
      show_hn: [
        `Show HN: ${title} – ${tagline.slice(0, 90)}`,
        "",
        "What it does",
        tagline,
        "",
        "Why I built it",
        problem,
        "",
        "How it works",
        stack,
        "",
        "What I'd love feedback on",
        `${detail} ${limitation}`,
        "",
        `[add a demo or repo link before posting] · /p/${slug}`,
        shared,
      ].filter(Boolean).join("\n"),
      reel_script: [
        `[0-3s] VISUAL: problem setup | VOICEOVER: ${problem.slice(0, 90)} | ON-SCREEN TEXT: THE PROBLEM`,
        `[3-8s] VISUAL: team at work | VOICEOVER: So we built ${title} | ON-SCREEN TEXT: WHAT WE BUILT`,
        `[8-16s] VISUAL: product in use | VOICEOVER: ${tagline.slice(0, 90)} | ON-SCREEN TEXT: HOW IT WORKS`,
        `[16-25s] VISUAL: stack / diagram | VOICEOVER: Built with ${stack} | ON-SCREEN TEXT: THE METHOD`,
        `[25-34s] VISUAL: chart or demo | VOICEOVER: ${detail} | ON-SCREEN TEXT: THE EVIDENCE`,
        `[34-42s] VISUAL: ask | VOICEOVER: Feedback welcome at /p/${slug} | ON-SCREEN TEXT: ONE ASK`,
        shared,
      ].filter(Boolean).join("\n"),
      policy_brief: [
        "Analysis, not legal advice.",
        "",
        "Question",
        problem,
        "",
        "Why it matters",
        tagline,
        "",
        "Evidence & sources",
        "[add primary-source citation from the dossier]",
        "",
        "Recommendation",
        "One bounded action based only on the cited material.",
        "",
        "Limitations",
        limitation,
        "",
        `/p/${slug}`,
        shared,
      ].filter(Boolean).join("\n"),
      plain_explainer: [
        "Research note — not medical advice.",
        "",
        "What we asked",
        problem,
        "",
        "What we did (methods + controls)",
        `[add the control or comparison used] · ${stack}`,
        "",
        "What we found",
        detail,
        "",
        "What we did NOT show",
        limitation,
        "",
        "Why it matters",
        tagline,
        "",
        `/p/${slug}`,
        shared,
      ].filter(Boolean).join("\n"),
    };

    return {
      asset_type: format,
      headline: `${title}: ${tagline}`.slice(0, 180),
      body_markdown: formatBody[format] || formatBody.linkedin,
      hooks: [
        problem.slice(0, 120),
        `What would you build to make ${tagline.toLowerCase()} work?`,
      ],
      suggested_tags: (cached?.tech_stack || [])
        .slice(0, 4)
        .map((item: string) => `#${item.replace(/[^A-Za-z0-9]/g, "")}`),
      og_image_url: "",
    } as unknown as T;
  }

  if (endpoint.includes("/boost")) {
    const segments = endpoint.split("/").filter(Boolean);
    const id = segments[segments.length - 1] || "unknown";
    return {
      status: "boosted",
      dossier_id: id,
      credits_deducted: 20,
      new_balance: 10,
      remaining_balance: 10,
      boost_expires_at: new Date(Date.now() + 48 * 3600 * 1000).toISOString(),
    } as unknown as T;
  }

  if (endpoint.includes("/signals/market")) {
    const params = new URLSearchParams(endpoint.split("?")[1] || "");
    const keywords = (params.get("keywords") || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const primary = keywords[0] || "your project";
    const encoded = encodeURIComponent(primary);
    const topic = keywords.slice(0, 3).join(", ") || primary;
    const links: Array<{
      source: string;
      signal_type: string;
      title: string;
      url: string;
      summary: string;
    }> = [
      {
        source: "founderdb",
        signal_type: "competitor",
        title: "FounderDB · browse similar products",
        url: "https://www.founderdb.com/",
        summary: `Open FounderDB to compare live and early-stage products adjacent to ${topic}.`,
      },
      {
        source: "ideabrowser",
        signal_type: "competitor",
        title: "IdeaBrowser · browse similar products",
        url: "https://www.ideabrowser.com/",
        summary: `Open IdeaBrowser to compare live products adjacent to ${topic}.`,
      },
      {
        source: "tumrr",
        signal_type: "competitor",
        title: "Tumrr · browse similar products",
        url: "https://tumrr.com/",
        summary: `Open Tumrr to compare indie products adjacent to ${topic}.`,
      },
      {
        source: "google_trends",
        signal_type: "trend",
        title: `Google Trends · ${primary}`,
        url: `https://trends.google.com/trends/explore?q=${encoded}`,
        summary: `Explore search interest for ${topic} over time and by region.`,
      },
      {
        source: "x",
        signal_type: "discussion",
        title: `X · live posts on ${primary}`,
        url: `https://x.com/search?q=${encoded}&f=live`,
        summary: `Open live X posts about ${topic} to see launches and builder discourse.`,
      },
      {
        source: "reddit",
        signal_type: "discussion",
        title: `Reddit · recent threads on ${primary}`,
        url: `https://www.reddit.com/search/?q=${encoded}&sort=new`,
        summary: `Open live Reddit discussions about ${topic} to spot unmet needs.`,
      },
      {
        source: "threads",
        signal_type: "discussion",
        title: `Threads · builders discussing ${primary}`,
        url: `https://www.threads.net/search?q=${encoded}`,
        summary: `Open Threads search for ${topic} to find adjacent builders.`,
      },
    ];
    const signals = links.map((link) => ({
      id: `offline-${link.source}`,
      source: link.source,
      signal_type: link.signal_type,
      title: link.title,
      summary: link.summary,
      url: link.url,
      relevance_score: 0.3,
      keywords,
      is_live: false,
    }));

    return {
      generated_at: new Date().toISOString(),
      domain_persona: params.get("persona") || "tech_builder",
      keywords,
      trend_direction: "unknown",
      trend_basis: "Offline fallback: no live provider was contacted.",
      summary: `Offline fallback for ${topic}. Open these real search links to verify each platform directly — no posts or metrics were invented.`,
      signals,
      similar_builders: [],
      coverage: signals.map((signal) => ({
        source: signal.source,
        live: false,
        signal_count: 1,
        note: "Offline fallback",
      })),
    } as unknown as T;
  }

  // Radar intentionally has no local fallback. A failed scan must never wipe
  // the visible briefing or invent a hackathon, grant, deadline, or link.

  if (endpoint.includes("/network/contacts/match")) {
    return {
      matched_contacts: [
        {
          user_id: "u-1",
          full_name: "Aarav Sharma",
          avatar_url: "https://avatars.githubusercontent.com/u/1029384",
          active_dossiers_count: 2,
          is_connected: false,
        },
        {
          user_id: "u-2",
          full_name: "Maya Chen",
          avatar_url: "https://avatars.githubusercontent.com/u/2048592",
          active_dossiers_count: 1,
          is_connected: false,
        },
      ],
    } as unknown as T;
  }

  if (endpoint.includes("/network/invites/send")) {
    const cached = readStoredDossier();
    const slug = cached?.slug || "project";
    return {
      status: "sent",
      invite_token: "ref_simulated_token",
      whatsapp_url: `https://wa.me/?text=${encodeURIComponent(
        `Hey! Check out our new build: https://studentradar.dev/p/${slug}`,
      )}`,
      daily_invites_remaining: 8,
    } as unknown as T;
  }

  if (endpoint.includes("/credits/review")) {
    return {
      status: "review_accepted",
      credits_awarded: 10,
      new_balance: 40,
    } as unknown as T;
  }

  return {} as T;
}
