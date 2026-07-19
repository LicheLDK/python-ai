import { apiFetch } from "@/services/http";
import type {
  AdminDashboard,
  AiUsageRead,
  AuditLogRead,
  OcrJobAdminDetail,
  OcrJobAdminRead,
  Page,
  UserRead,
} from "@/types";

function qs(params: Record<string, string | number | undefined | null>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

export async function listUsers(params?: {
  q?: string;
  role?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<Page<UserRead>> {
  return apiFetch(`/api/v1/admin/users${qs(params || {})}`);
}

export async function getUser(userId: string): Promise<UserRead> {
  return apiFetch(`/api/v1/admin/users/${userId}`);
}

export async function patchUser(
  userId: string,
  body: { name?: string; role?: string; status?: string },
): Promise<UserRead> {
  return apiFetch(`/api/v1/admin/users/${userId}`, {
    method: "PATCH",
    body,
  });
}

export async function listUsage(params?: {
  from?: string;
  to?: string;
  provider?: string;
  user_id?: string;
  page?: number;
  page_size?: number;
}): Promise<Page<AiUsageRead>> {
  return apiFetch(`/api/v1/admin/usage${qs(params || {})}`);
}

export async function listOcrHistory(params?: {
  from?: string;
  to?: string;
  status?: string;
  user_id?: string;
  page?: number;
  page_size?: number;
}): Promise<Page<OcrJobAdminRead>> {
  return apiFetch(`/api/v1/admin/ocr-history${qs(params || {})}`);
}

export async function getOcrHistoryDetail(
  jobId: string,
): Promise<OcrJobAdminDetail> {
  return apiFetch(`/api/v1/admin/ocr-history/${jobId}`);
}

export async function listAuditLogs(params?: {
  actor_id?: string;
  action?: string;
  from?: string;
  to?: string;
  page?: number;
  page_size?: number;
}): Promise<Page<AuditLogRead>> {
  return apiFetch(`/api/v1/admin/audit-logs${qs(params || {})}`);
}

export async function getDashboard(): Promise<AdminDashboard> {
  return apiFetch("/api/v1/admin/dashboard");
}
