/**
 * Typed client for LaunchPad Dossier v2.
 *
 * This module deliberately does NOT import the legacy `api.ts` fallback engine:
 * a v2 run must only display content that actually came from the API.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const SECTION_KEYS = [
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
] as const;

export type SectionKey = (typeof SECTION_KEYS)[number];

export const SECTION_TITLES: Record<SectionKey, string> = {
  executive_brief: "Executive brief",
  idea_restated: "Idea, restated",
  problem_users: "Problem & users",
  market_landscape: "Market landscape",
  related_work: "Related work",
  novelty_assessment: "Novelty assessment",
  gaps: "Gaps",
  challenges_risks: "Challenges & risks",
  feasibility: "Feasibility",
  solution_design: "Solution design",
  tech_stack: "Tech stack",
  data_evaluation: "Data & evaluation",
  validation_plan: "Validation plan",
  roadmap: "Roadmap",
  people_community: "People & community",
  funding_opportunities: "Funding opportunities",
  visibility_angle: "Visibility angle",
  open_questions_evidence: "Open questions & missing evidence",
};

export function isSectionKey(value: string): value is SectionKey {
  return (SECTION_KEYS as readonly string[]).includes(value);
}

export type InputType = "idea" | "github" | "pdf_text";
export type RunMode = "quick" | "deep";
export type ClaimLabel = "grounded" | "input" | "inference" | "recommendation";
export type Confidence = "high" | "medium" | "low";
export type Coverage = "strong" | "thin" | "none";
export type Effort = "low" | "medium" | "high";
export type Severity = "low" | "medium" | "high" | "critical";

export interface StudentProfile {
  skills: string[];
  weekly_hours: number;
  budget_usd: number;
  country: string;
  education_level: string;
  goals: string[];
  purpose: "coursework" | "research" | "product";
}

export interface StartRunPayload {
  input_type: InputType;
  raw_content: string;
  domain_persona: string;
  mode: RunMode;
  profile: StudentProfile;
}

export interface SectionItem {
  id: string;
  label: ClaimLabel | string;
  text: string;
  evidence: string[];
  reasoning?: string;
  effort?: Effort | string;
  severity?: Severity | string;
  /** Tolerant extras used by specialised renderers when the API supplies them. */
  alternatives?: string[];
  cost?: string;
  layer?: string;
  done?: boolean;
  [key: string]: unknown;
}

export interface SectionTable {
  title: string;
  columns: unknown[];
  rows: unknown[];
}

export interface GeneratedBy {
  prompt: string;
  model: string;
}

export interface Section {
  section: string;
  summary: string;
  confidence: Confidence | string;
  coverage: Coverage | string;
  items: SectionItem[];
  tables: SectionTable[];
  limitations: string[];
  generated_by: GeneratedBy;
  locked?: boolean;
}

export interface Evidence {
  ref: string;
  url: string;
  title: string;
  source: string;
  source_quality: string;
  passage: string;
  retrieved_at: string;
  relevance: number | string;
  question_id: string;
}

export interface RunProgress {
  stage: string;
  message: string;
  completed_sections: number;
  total_sections: number;
}

export interface DossierRun {
  id: string;
  status: string;
  mode: RunMode | string;
  progress: RunProgress;
  plan?: unknown;
  coverage?: unknown;
  cost_usd?: number;
  duration_ms?: number;
  created_at?: string;
  finished_at?: string;
  sections: Record<string, Section>;
  evidence: Evidence[];
  reviews?: unknown;
  error?: unknown;
  [key: string]: unknown;
}

export interface RunCreated {
  run_id: string;
  status: string;
  stream_url?: string;
  [key: string]: unknown;
}

export interface ChatResponse {
  answer: string;
  evidence: string[];
  abstained: boolean;
}

export interface RoadmapItem {
  text: string;
  section: string;
  effort: Effort | string;
  done?: boolean;
}

export interface RoadmapResponse {
  run_id: string;
  tasks: unknown[];
  [key: string]: unknown;
}

export interface SectionPatchBody {
  content: Record<string, unknown>;
  locked: boolean;
}

export type StreamEventType = "progress" | "section" | "complete" | "error";

export interface StreamEventData {
  type: StreamEventType;
  data: unknown;
}

export interface StreamHandlers {
  onEvent?: (event: StreamEventData) => void;
  onError?: () => void;
}

export class DossierV2Error extends Error {
  readonly status: number;
  readonly code?: string;
  readonly detail: unknown;

  constructor(message: string, status: number, detail?: unknown, code?: string) {
    super(message);
    this.name = "DossierV2Error";
    this.status = status;
    this.detail = detail;
    this.code = code;
  }

  static from(status: number, payload: unknown): DossierV2Error {
    const root = isRecord(payload) ? payload : {};
    const detail = root.detail !== undefined ? root.detail : payload;
    const code = isRecord(detail) && typeof detail.code === "string" ? detail.code : undefined;
    let message = `Request failed (${status})`;
    if (code === "AI_PROVIDER_NOT_CONFIGURED") {
      message = "AI provider not configured";
    } else if (typeof detail === "string" && detail.trim()) {
      message = detail;
    } else if (isRecord(detail) && typeof detail.message === "string") {
      message = detail.message;
    } else if (detail !== undefined && detail !== null) {
      try {
        message = JSON.stringify(detail);
      } catch {
        message = `Request failed (${status})`;
      }
    }
    return new DossierV2Error(message, status, detail, code);
  }

  get isNotConfigured(): boolean {
    return this.code === "AI_PROVIDER_NOT_CONFIGURED" || this.status === 503 && this.code === "AI_PROVIDER_NOT_CONFIGURED";
  }
}

export function asDossierV2Error(error: unknown): DossierV2Error {
  if (error instanceof DossierV2Error) return error;
  const message = error instanceof Error ? error.message : String(error || "Unknown error");
  return new DossierV2Error(message, 0);
}

function getGuestSessionId(): string {
  if (typeof window === "undefined") return "server-guest-id";
  try {
    let guestId = window.localStorage.getItem("student_radar_guest_id");
    if (!guestId) {
      guestId = `guest_${Math.random().toString(36).substring(2, 12)}${Date.now().toString(36)}`;
      window.localStorage.setItem("student_radar_guest_id", guestId);
    }
    return guestId;
  } catch {
    return "guest_unavailable";
  }
}

function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem("student_radar_jwt");
  } catch {
    return null;
  }
}

function requestHeaders(extra?: HeadersInit): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Guest-Session-ID": getGuestSessionId(),
  };
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (extra) {
    if (extra instanceof Headers) {
      extra.forEach((value, key) => {
        headers[key] = value;
      });
    } else if (Array.isArray(extra)) {
      extra.forEach(([key, value]) => {
        headers[key] = value;
      });
    } else {
      Object.assign(headers, extra as Record<string, string>);
    }
  }
  return headers;
}

async function request<T>(endpoint: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...init,
    headers: requestHeaders(init.headers),
  });

  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = await response.text().catch(() => null);
    }
    throw DossierV2Error.from(response.status, payload);
  }

  if (response.status === 204) return undefined as T;
  const raw = await response.text();
  if (!raw) return undefined as T;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return raw as unknown as T;
  }
}

export function startRun(payload: StartRunPayload): Promise<RunCreated> {
  return request<RunCreated>("/dossiers/v2/runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getRun(runId: string): Promise<DossierRun> {
  return request<DossierRun>(`/dossiers/v2/runs/${encodeURIComponent(runId)}`);
}

/**
 * EventSource cannot set arbitrary headers, so a guest id is passed as a query
 * parameter as well. JWT auth is intentionally not placed in a URL.
 */
export function streamRunEvents(runId: string, handlers: StreamHandlers): EventSource {
  const guest = encodeURIComponent(getGuestSessionId());
  const source = new EventSource(
    `${API_BASE}/dossiers/v2/runs/${encodeURIComponent(runId)}/events?guest_session_id=${guest}`,
  );

  const dispatch = (raw: string): void => {
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      return;
    }
    if (!isRecord(parsed)) return;
    const type = parsed.type;
    if (type !== "progress" && type !== "section" && type !== "complete" && type !== "error") return;
    handlers.onEvent?.({ type, data: parsed.data });
  };

  source.onmessage = (event: MessageEvent<string>) => dispatch(event.data);
  (["progress", "section", "complete", "error"] as const).forEach((type) => {
    source.addEventListener(
      type,
      ((event: MessageEvent<string>) => dispatch(event.data)) as unknown as EventListener,
    );
  });
  source.onerror = () => handlers.onError?.();
  return source;
}

export function deepenSection(runId: string, section: SectionKey): Promise<unknown> {
  return request<unknown>(`/dossiers/v2/runs/${encodeURIComponent(runId)}/deepen`, {
    method: "POST",
    body: JSON.stringify({ section }),
  });
}

export function askDossier(runId: string, question: string): Promise<ChatResponse> {
  return request<ChatResponse>(`/dossiers/v2/runs/${encodeURIComponent(runId)}/chat`, {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export function patchSection(runId: string, section: SectionKey, body: SectionPatchBody): Promise<unknown> {
  return request<unknown>(`/dossiers/v2/runs/${encodeURIComponent(runId)}/sections/${section}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function rerunResearch(runId: string): Promise<RunCreated> {
  return request<RunCreated>(`/dossiers/v2/runs/${encodeURIComponent(runId)}/rerun`, {
    method: "POST",
  });
}

export function saveRoadmap(runId: string, items: RoadmapItem[]): Promise<RoadmapResponse | DossierRun> {
  return request<RoadmapResponse | DossierRun>(`/dossiers/v2/runs/${encodeURIComponent(runId)}/roadmap`, {
    method: "POST",
    body: JSON.stringify({ items }),
  });
}

export async function exportRunText(runId: string, format: "markdown" | "json"): Promise<string> {
  const response = await fetch(
    `${API_BASE}/dossiers/v2/runs/${encodeURIComponent(runId)}/export?format=${format}`,
    { headers: requestHeaders() },
  );
  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = await response.text().catch(() => null);
    }
    throw DossierV2Error.from(response.status, payload);
  }
  return response.text();
}

export function downloadTextFile(filename: string, content: string, mimeType: string): void {
  if (typeof document === "undefined") return;
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function cellToString(value: unknown): string {
  if (value === undefined || value === null) return "";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) return value.map(cellToString).join(", ");
  if (isRecord(value)) {
    const preferred = value.title ?? value.label ?? value.name ?? value.text ?? value.value ?? value.id;
    if (preferred !== undefined) return cellToString(preferred);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function normalizeColumns(columns: unknown[]): string[] {
  return columns.map((column, index) => {
    if (Array.isArray(column)) return column.map(cellToString).join(" / ");
    if (isRecord(column)) {
      const named = column.label ?? column.title ?? column.name ?? column.key ?? column.id;
      if (named !== undefined) return cellToString(named);
    }
    const asText = cellToString(column);
    return asText || `Column ${index + 1}`;
  });
}

export function normalizeRows(rows: unknown[], columns: string[]): string[][] {
  return rows.map((row) => {
    if (Array.isArray(row)) return row.map(cellToString);
    if (isRecord(row)) return columns.map((column) => cellToString(row[column]));
    return columns.map(() => cellToString(row));
  });
}

export function evidenceRefsInText(text: string): string[] {
  const refs = text.match(/\[E\d+\]/g) || [];
  return Array.from(new Set(refs));
}

/** API refs are `E12`; prose citations are written `[E12]`. */
export function normalizeEvidenceRef(ref: string): string {
  return ref.trim().replace(/^\[/, "").replace(/\]$/, "");
}

/** Build the full section object required by PATCH /sections/{section}. */
export function sectionContentPayload(
  section: Section,
  overrides: Partial<Section> = {},
): Record<string, unknown> {
  const merged: Section = { ...section, ...overrides };
  return {
    section: merged.section,
    summary: merged.summary || "",
    confidence: merged.confidence || "low",
    coverage: merged.coverage || "none",
    items: merged.items || [],
    tables: merged.tables || [],
    limitations: merged.limitations || [],
    generated_by: merged.generated_by || { prompt: "", model: "" },
  };
}

export function terminalStatus(status: string | undefined): boolean {
  if (!status) return false;
  return ["completed", "complete", "done", "succeeded", "success", "partial", "failed", "error", "cancelled", "canceled"]
    .includes(status.toLowerCase());
}

export function sectionCount(run: DossierRun | null): { done: number; total: number } {
  if (!run) return { done: 0, total: SECTION_KEYS.length };
  const done = Object.keys(run.sections || {}).filter((key) => Boolean(run.sections[key])).length;
  const total = run.progress?.total_sections || SECTION_KEYS.length;
  return { done, total };
}
