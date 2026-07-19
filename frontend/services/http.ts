/**
 * Typed HTTP client (T-8.02 / SDS §5.22).
 * - Bearer access token from memory
 * - credentials:include for refresh cookie
 * - Single-flight refresh on 401
 * - CSRF header on /auth/refresh and /auth/logout
 */

import {
  clearAccessToken,
  getAccessToken,
  readCsrfCookie,
  setAccessToken,
  setCurrentUser,
} from "@/lib/auth";
import type { ErrorEnvelope, TokenResponse } from "@/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: Record<string, unknown> | null;
  readonly requestId?: string | null;

  constructor(status: number, envelope: ErrorEnvelope) {
    super(envelope.message || `HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.code = envelope.code || "unknown";
    this.details = envelope.details;
    this.requestId = envelope.request_id;
  }
}

export function apiBaseUrl(): string {
  return API_BASE;
}

type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

export interface RequestOptions {
  method?: HttpMethod;
  body?: unknown;
  formData?: FormData;
  headers?: Record<string, string>;
  /** Skip Authorization header (login/register). */
  skipAuth?: boolean;
  /** Skip 401→refresh retry (auth endpoints). */
  skipRefresh?: boolean;
  /** Attach X-CSRF-Token from cookie. */
  csrf?: boolean;
}

let refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const csrf = readCsrfCookie();
      const headers: Record<string, string> = {
        Accept: "application/json",
      };
      if (csrf) headers["X-CSRF-Token"] = csrf;
      const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers,
      });
      if (!res.ok) {
        clearAccessToken();
        return false;
      }
      const data = (await res.json()) as TokenResponse;
      setAccessToken(data.access_token);
      setCurrentUser(data.user);
      return true;
    } catch {
      clearAccessToken();
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

async function parseError(res: Response): Promise<ApiError> {
  let envelope: ErrorEnvelope = {
    code: "http_error",
    message: res.statusText || `HTTP ${res.status}`,
  };
  try {
    const data = (await res.json()) as ErrorEnvelope;
    if (data && typeof data === "object" && "message" in data) {
      envelope = data;
    }
  } catch {
    /* ignore */
  }
  return new ApiError(res.status, envelope);
}

export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    method = "GET",
    body,
    formData,
    headers: extra = {},
    skipAuth = false,
    skipRefresh = false,
    csrf = false,
  } = options;

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...extra,
  };

  if (!skipAuth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  if (csrf) {
    const csrfToken = readCsrfCookie();
    if (csrfToken) headers["X-CSRF-Token"] = csrfToken;
  }

  let payload: BodyInit | undefined;
  if (formData) {
    payload = formData;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  let res = await fetch(url, {
    method,
    credentials: "include",
    headers,
    body: payload,
  });

  if (res.status === 401 && !skipRefresh && !skipAuth) {
    const ok = await tryRefresh();
    if (ok) {
      const retryHeaders = { ...headers };
      const token = getAccessToken();
      if (token) retryHeaders.Authorization = `Bearer ${token}`;
      if (csrf) {
        const csrfToken = readCsrfCookie();
        if (csrfToken) retryHeaders["X-CSRF-Token"] = csrfToken;
      }
      res = await fetch(url, {
        method,
        credentials: "include",
        headers: retryHeaders,
        body: payload,
      });
    }
  }

  if (res.status === 204) {
    return undefined as T;
  }

  if (!res.ok) {
    throw await parseError(res);
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    return (await res.json()) as T;
  }
  return (await res.text()) as T;
}
