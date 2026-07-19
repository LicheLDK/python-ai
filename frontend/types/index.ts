/** Shared API types aligned with backend OpenAPI / SDS §9. */

export type UserRole = "user" | "admin";
export type UserStatus = "active" | "inactive" | "suspended";

export interface UserRead {
  id: string;
  email: string;
  name: string;
  org_id: string;
  role: UserRole;
  status: UserStatus;
  created_at: string;
  updated_at: string;
}

export interface ErrorEnvelope {
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
  request_id?: string | null;
}

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserRead;
}

export interface DocumentRead {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  checksum_sha256: string;
  status: string;
  created_at: string;
  page_count?: number | null;
}

export type OcrJobStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export interface OcrJobRead {
  id: string;
  document_id: string;
  status: OcrJobStatus;
  error?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface OcrPageResult {
  page: number;
  text: string;
  boxes?: unknown;
  confidence?: number | null;
}

export interface OcrResultsResponse {
  job_id: string;
  pages: OcrPageResult[];
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface UsageBlock {
  tokens_in: number;
  tokens_out: number;
  latency_ms: number;
  cost_estimate?: number | null;
}

export interface ChatResponse {
  request_id: string;
  provider: string;
  model: string;
  message: ChatMessage;
  usage: UsageBlock;
}

export interface VisionResponse {
  request_id: string;
  provider: string;
  model: string;
  result: unknown;
  usage: UsageBlock;
}

export interface PromptRead {
  id: string;
  name: string;
  version: number;
  template: string;
  variables_schema?: Record<string, unknown> | null;
  active: boolean;
  created_at: string;
}

export type PipelineRunStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export interface PipelineStage {
  name: string;
  status: string;
  error?: string | null;
  output_ref?: Record<string, unknown> | null;
}

export interface PipelineRunRead {
  id: string;
  document_id: string;
  status: PipelineRunStatus;
  stages: PipelineStage[];
  error?: string | null;
  created_at: string;
  finished_at?: string | null;
}

export interface StatPoint {
  date: string;
  metric: string;
  value: number;
  dimensions?: Record<string, unknown>;
}

export interface StatsSummary {
  ocr_jobs_today: number;
  ai_requests_today: number;
  tokens_today: number;
  error_rate_today: number;
}

export interface AiUsageRead {
  id: string;
  request_id: string;
  user_id: string;
  provider: string;
  model: string;
  request_type: string;
  status: string;
  tokens_in: number;
  tokens_out: number;
  latency_ms: number;
  cost_estimate: number;
  created_at: string;
}

export interface OcrJobAdminRead {
  id: string;
  document_id: string;
  user_id: string;
  status: string;
  error?: string | null;
  options?: Record<string, unknown>;
  attempt_count?: number;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
}

export interface OcrJobAdminDetail {
  job: OcrJobAdminRead;
  pages: OcrPageResult[];
}

export interface AuditLogRead {
  id: string;
  actor_id?: string | null;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  payload?: Record<string, unknown>;
  ip?: string | null;
  request_id?: string | null;
  created_at: string;
}

export interface AdminDashboard {
  users_total: number;
  ocr_jobs_24h: number;
  ai_requests_24h: number;
  error_rate_24h: number;
  top_users: {
    user_id: string;
    email?: string | null;
    ocr_jobs: number;
    ai_requests: number;
  }[];
  provider_breakdown: {
    provider: string;
    requests: number;
    tokens_in: number;
    tokens_out: number;
    cost_estimate: number;
  }[];
}

